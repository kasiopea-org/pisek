# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import abstractmethod
import os
import random
from typing import Optional, Union, Callable
import subprocess

from pisek.env import Env
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.terminal import tab, colored
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramsJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.chaos_monkey import Incomplete, ChaosMonkey
from pisek.jobs.parts.tools import Sanitize
from pisek.jobs.parts.solution_result import RESULT_MARK, Verdict, SolutionResult

DIFF_NAME = "diff.sh"


class JudgeManager(TaskJobManager):
    """Manager that prepares and test judge."""

    def __init__(self):
        super().__init__("Preparing judge")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        if self._env.config.judge_type != "diff":
            jobs.append(
                comp := Compile(self._env, self._resolve_path(self._env.config.judge))
            )

        samples = self._get_samples()
        if self._env.config.task_type == "communication":
            return jobs

        for inp, out in samples:
            jobs.append(
                judge := judge_job(
                    self._env.config.judge,
                    inp,
                    out,
                    out,
                    0,
                    lambda: "0",
                    1.0,
                    self._env,
                )
            )
            if self._env.config.judge_type != "diff":
                judge.add_prerequisite(comp)

            JOBS = [(Incomplete, 10), (ChaosMonkey, 50)]

            total = sum(map(lambda x: x[1], JOBS))
            random.seed(4)  # Reproducibility!
            seeds = random.sample(range(0, 16**4), total)

            for job, times in JOBS:
                for i in range(times):
                    seed = seeds.pop()
                    inv_out = out.replace(".out", f".{seed:x}.invalid")
                    jobs += [
                        invalidate := job(self._env, out, inv_out, seed),
                        run_judge := judge_job(
                            self._env.config.judge,
                            inp,
                            inv_out,
                            out,
                            0,
                            lambda: "0",
                            None,
                            self._env,
                        ),
                    ]
                    if self._env.config.judge_type != "diff":
                        run_judge.add_prerequisite(comp)
                    run_judge.add_prerequisite(invalidate)
        return jobs


class RunKasiopeaJudgeMan(TaskJobManager):
    def __init__(
        self, subtask: int, seed: int, input_: str, output: str, correct_output: str
    ):
        self._subtask = subtask
        self._seed = seed
        self._input_file = input_
        self._output_file = output
        self._correct_output = correct_output
        super().__init__("Running judge")

    def _get_jobs(self) -> list[Job]:
        judge_program = self._resolve_path(self._env.config.judge)
        clean_output = self._output_file + ".clean"

        jobs: list[Job] = [
            sanitize := Sanitize(self._env, self._output_file, clean_output),
            judge := judge_job(
                judge_program,
                self._input_file,
                clean_output,
                self._correct_output,
                self._subtask,
                lambda: f"{self._seed:x}",
                None,
                self._env,
            ),
        ]
        judge.add_prerequisite(sanitize)
        if self._env.config.judge_type != "diff":
            jobs.insert(0, compile := Compile(self._env, judge_program))
            judge.add_prerequisite(compile)

        self._judge_job = judge

        return jobs

    def judge_result(self) -> SolutionResult:
        if self.state != State.succeeded:
            raise RuntimeError(f"Judging hasn't successfully finished.")
        elif not isinstance(self._judge_job.result, SolutionResult):
            raise RuntimeError(f"Judging result invalid.")
        return self._judge_job.result


JUDGE_JOB_NAME = r"Judge (\w+)"


class RunJudge(ProgramsJob):
    """Runs judge on single input. (Abstract class)"""

    def __init__(
        self,
        env: Env,
        name: str,
        judge: str,
        input_name: str,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.judge = judge
        self.input_name = input_name
        self.input = self._input(input_name)
        self.expected_points = expected_points

    @abstractmethod
    def _get_solution_run_res(self) -> RunResult:
        pass

    @abstractmethod
    def _judge(self) -> SolutionResult:
        """Here actually do the judging."""
        pass

    @abstractmethod
    def _judging_message(self) -> str:
        pass

    def _judging_message_capitalized(self) -> str:
        msg = self._judging_message()
        return msg[0].upper() + msg[1:]

    def _run(self) -> SolutionResult:
        solution_res = self._get_solution_run_res()
        if solution_res.kind == RunResultKind.OK:
            result = self._judge()
        elif solution_res.kind == RunResultKind.RUNTIME_ERROR:
            result = SolutionResult(
                Verdict.error,
                0.0,
                "",
                self._quote_program(solution_res),
                solution_res.status,
            )
        elif solution_res.kind == RunResultKind.TIMEOUT:
            result = SolutionResult(
                Verdict.timeout, 0.0, "", self._quote_program(solution_res)
            )

        if (
            self.expected_points is not None
            and result is not None
            and result.points != self.expected_points
        ):
            raise PipelineItemFailure(
                self._judging_message_capitalized()
                + f"should have got {self.expected_points} points but got {result.points} points."
            )

        return result

    def message(self) -> str:
        """Message about how judging ended."""
        if self.result is None:
            raise RuntimeError(f"Job {self.name} has not finished yet.")

        judge = os.path.basename(self.judge)
        judging = self._judging_message()
        if self.result.verdict == Verdict.ok:
            head = f"{judge} accepted {judging}"
        elif self.result.verdict == Verdict.wrong_answer:
            head = f"{judge} rejected {judging}"
        elif self.result.verdict == Verdict.partial:
            head = f"{judge} partially accepted {judging}"
        elif self.result.verdict == Verdict.error:
            head = f"Solution failed on input {self.input_name}"
        elif self.result.verdict == Verdict.timeout:
            head = f"Solution did timeout on input {self.input_name}"

        text = f"{head}:\n{tab(self.result.output)}"
        if self.result.diff != "":
            text += "\n" + tab(f"diff:\n{tab(self.result.diff)}")

        return text


class RunBatchJudge(RunJudge):
    """Runs batch judge on single input. (Abstract class)"""

    def __init__(
        self,
        env: Env,
        judge: str,
        input_name: str,
        output_name: str,
        correct_output: str,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=JUDGE_JOB_NAME.replace(r"(\w+)", os.path.basename(output_name), 1),
            judge=judge,
            input_name=input_name,
            expected_points=expected_points,
            **kwargs,
        )
        self.output_name = output_name
        self.output = (
            self._invalid_output if output_name.endswith(".invalid") else self._output
        )(output_name)
        self.correct_output_name = correct_output
        self.correct_output = self._output(correct_output)
        self.log_file = self._log_file(self.output_name, self.judge)

    def _get_solution_run_res(self) -> RunResult:
        if "run_solution" in self.prerequisites_results:
            return self.prerequisites_results["run_solution"]
        else:
            # There is no solution (judging samples)
            # XXX: We only care about the kind
            return RunResult(RunResultKind.OK, 0, 0.0, 0.0)

    def _judging_message(self) -> str:
        return f"output {self.output_name} for input {self.input_name}"

    def _nice_diff(self) -> str:
        """Create a nice diff between output and correct output."""
        diff = self._short_text(self._diff_files(self.correct_output, self.output))
        return colored(diff, self._env, "yellow")


class RunDiffJudge(RunBatchJudge):
    """Judges solution output and correct output using diff."""

    def __init__(
        self,
        env: Env,
        judge: str,
        input_name: str,
        output_name: str,
        correct_output: str,
        expected_points: Optional[float],
    ) -> None:
        super().__init__(
            env=env,
            judge=judge,
            input_name=input_name,
            output_name=output_name,
            correct_output=correct_output,
            expected_points=expected_points,
        )

    def _judge(self) -> SolutionResult:
        self._access_file(self.output)
        self._access_file(self.correct_output)
        diff = subprocess.run(
            ["diff", "-Bq", self.output, self.correct_output],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # XXX: Okay, it didn't finish in no time, but this is not meant to be used
        rr = RunResult(
            RunResultKind.OK,
            diff.returncode,
            0,
            0,
            stderr_text=diff.stderr.decode("utf-8"),
            status="Files are same" if diff.returncode == 0 else "Files differ",
        )
        if diff.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0, "", self._quote_program(rr))
        elif diff.returncode == 1:
            return SolutionResult(
                Verdict.wrong_answer,
                0.0,
                "",
                self._quote_program(rr),
                self._nice_diff(),
            )
        else:
            raise PipelineItemFailure(
                f"Diff failed:\n{tab(diff.stderr.decode('utf-8'))}"
            )


class RunKasiopeaJudge(RunBatchJudge):
    """Judges solution output using judge with Kasiopea interface."""

    def __init__(
        self,
        env: Env,
        judge: str,
        input_name: str,
        output_name: str,
        correct_output: str,
        subtask: int,
        seed: str,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge=judge,
            input_name=input_name,
            output_name=output_name,
            correct_output=correct_output,
            expected_points=expected_points,
            **kwargs,
        )
        self.subtask = subtask
        self.seed = seed

    def _judge(self) -> SolutionResult:
        envs = {}
        if self._env.config.judge_needs_in:
            envs["TEST_INPUT"] = self.input
            self._access_file(self.input)
        if self._env.config.judge_needs_out:
            envs["TEST_OUTPUT"] = self.correct_output
            self._access_file(self.correct_output)

        result = self._run_program(
            self.judge,
            args=[str(self.subtask), self.seed],
            stdin=self.output,
            stderr=self.log_file,
            env=envs,
        )
        if result.returncode == 0:
            return SolutionResult(
                Verdict.ok, 1.0, result.raw_stderr(), self._quote_program(result)
            )
        elif result.returncode == 1:
            return SolutionResult(
                Verdict.wrong_answer,
                0.0,
                result.raw_stderr(),
                self._quote_program(result),
                self._nice_diff(),
            )
        else:
            raise self._create_program_failure(
                f"Judge failed on output {self.output_name}:", result
            )


class RunCMSJudge(RunBatchJudge):
    """Judges solution output using judge with CMS interface."""

    def __init__(
        self,
        env: Env,
        judge: str,
        input_name: str,
        output_name: str,
        correct_output: str,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge=judge,
            input_name=input_name,
            output_name=output_name,
            correct_output=correct_output,
            expected_points=expected_points,
            **kwargs,
        )

    def _judge(self) -> SolutionResult:
        self._access_file(self.input)
        self._access_file(self.output)
        self._access_file(self.correct_output)
        points_file = self.output.replace(".out", ".judge")
        self._access_file(points_file)
        result = self._run_program(
            self.judge,
            args=[self.input, self.correct_output, self.output],
            stdout=points_file,
            stderr=self.log_file,
        )
        if result.returncode == 0:
            points_str = result.raw_stdout().split("\n")[0]
            try:
                points = float(points_str)
            except ValueError:
                raise self._create_program_failure(
                    "Judge wrote didn't write points on stdout:", result
                )

            if not 0 <= points <= 1:
                raise self._create_program_failure(
                    "Judge must give between 0 and 1 points:", result
                )

            if points == 0:
                return SolutionResult(
                    Verdict.wrong_answer,
                    0.0,
                    result.raw_stderr(),
                    self._quote_program(result),
                    self._nice_diff(),
                )
            elif points == 1:
                return SolutionResult(
                    Verdict.ok, 1.0, result.raw_stderr(), self._quote_program(result)
                )
            else:
                return SolutionResult(
                    Verdict.partial,
                    points,
                    result.raw_stderr(),
                    self._quote_program(result),
                    self._nice_diff(),
                )
        else:
            raise self._create_program_failure(
                f"Judge failed on output {self.output_name}:", result
            )


def judge_job(
    judge: str,
    input_name: str,
    output_name: str,
    correct_output: str,
    subtask: int,
    get_seed: Callable[[], str],
    expected_points: Optional[float],
    env: Env,
) -> Union[RunDiffJudge, RunKasiopeaJudge, RunCMSJudge]:
    """Returns JudgeJob according to contest type."""
    if env.config.judge_type == "diff":
        return RunDiffJudge(
            env, judge, input_name, output_name, correct_output, expected_points
        )
    elif env.config.contest_type == "cms":
        return RunCMSJudge(
            env, judge, input_name, output_name, correct_output, expected_points
        )
    else:
        return RunKasiopeaJudge(
            env,
            judge,
            input_name,
            output_name,
            correct_output,
            subtask,
            get_seed(),
            expected_points,
        )
