# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import abstractmethod
from functools import cache, partial
import os
import random
from typing import Optional, Union, Callable
import subprocess

from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.env.task_config import ProgramType, JudgeType
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.utils.text import tab
from pisek.utils.terminal import colored_env
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramsJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.chaos_monkey import Incomplete, ChaosMonkey
from pisek.jobs.parts.tools import Sanitize
from pisek.jobs.parts.solution_result import Verdict, SolutionResult

DIFF_NAME = "diff.sh"


class JudgeManager(TaskJobManager):
    """Manager that prepares and test judge."""

    def __init__(self) -> None:
        super().__init__("Preparing judge")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        if self._env.config.out_check == JudgeType.judge:
            if self._env.config.out_judge is None:
                raise RuntimeError(
                    f"Unset judge for out_check={self._env.config.out_check.name}"
                )
            jobs.append(
                comp := Compile(self._env, TaskPath(self._env.config.out_judge))
            )

        samples = self._get_samples()
        if self._env.config.task_type == "communication":
            return jobs

        for inp, out in samples:
            jobs.append(
                judge_j := judge_job(
                    inp,
                    out,
                    out,
                    0,
                    lambda: "0",
                    1.0,
                    self._env,
                )
            )
            if self._env.config.out_check == JudgeType.judge:
                judge_j.add_prerequisite(comp)

            JOBS = [(Incomplete, 10), (ChaosMonkey, 50)]

            total = sum(map(lambda x: x[1], JOBS))
            random.seed(4)  # Reproducibility!
            seeds = random.sample(range(0, 16**4), total)

            for job, times in JOBS:
                for i in range(times):
                    seed = seeds.pop()
                    inv_out = TaskPath.invalid_file(self._env, out.name, seed)
                    jobs += [
                        invalidate := job(self._env, out, inv_out, seed),
                        run_judge := judge_job(
                            inp,
                            inv_out,
                            out,
                            0,
                            lambda: "0",
                            None,
                            self._env,
                        ),
                    ]
                    if self._env.config.out_check == JudgeType.judge:
                        run_judge.add_prerequisite(comp)
                    run_judge.add_prerequisite(invalidate)
        return jobs


class RunKasiopeaJudgeMan(TaskJobManager):
    def __init__(
        self,
        subtask: int,
        seed: int,
        input_: str,
        output: str,
        correct_output: str,
    ) -> None:
        self._subtask = subtask
        self._seed = seed
        self._input = input_
        self._output = output
        self._correct_output = correct_output
        super().__init__("Running judge")

    def _get_jobs(self) -> list[Job]:
        input_, output, correct_output = map(
            TaskPath,
            (self._input, self._output, self._correct_output),
        )
        clean_output = TaskPath.sanitized_file(self._env, output.name)

        jobs: list[Job] = [
            sanitize := Sanitize(self._env, output, clean_output),
            judge := judge_job(
                input_,
                clean_output,
                correct_output,
                self._subtask,
                lambda: f"{self._seed:x}",
                None,
                self._env,
            ),
        ]
        judge.add_prerequisite(sanitize)
        if self._env.config.out_check == JudgeType.judge:
            if self._env.config.out_judge is None:
                raise RuntimeError(
                    f"Unset judge for out_check={self._env.config.out_check.name}"
                )
            jobs.insert(
                0,
                compile := Compile(self._env, TaskPath(self._env.config.out_judge)),
            )
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
        judge_name: str,
        input_: TaskPath,
        judge_log_file: TaskPath,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.input = input_
        self.judge_name = judge_name
        self.judge_log_file = judge_log_file
        self.expected_points = expected_points

    @cache
    def _load_solution_run_res(self) -> None:
        """
        Loads solution's RunResult into self.solution_res
        """
        self._solution_run_res = self._get_solution_run_res()

    @abstractmethod
    def _get_solution_run_res(self) -> RunResult:
        """
        Gets solution's RunResult.
        Call this only through _load_solution_run_res as this can run the solution.
        """
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
        self._load_solution_run_res()
        if self._solution_run_res.kind == RunResultKind.OK:
            result = self._judge()
        elif self._solution_run_res.kind == RunResultKind.RUNTIME_ERROR:
            result = SolutionResult(
                Verdict.error,
                0.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                "",
                self._quote_program(self._solution_run_res),
                self._solution_run_res.status,
            )
        elif self._solution_run_res.kind == RunResultKind.TIMEOUT:
            result = SolutionResult(
                Verdict.timeout,
                0.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                "",
                self._quote_program(self._solution_run_res),
            )

        if (
            self.expected_points is not None
            and result is not None
            and result.points != self.expected_points
        ):
            raise PipelineItemFailure(
                f"{self._judging_message_capitalized()} should have got {self.expected_points} points but got {result.points} points."
            )

        return result

    def message(self) -> str:
        """Message about how judging ended."""
        if self.result is None:
            raise RuntimeError(f"Job {self.name} has not finished yet.")

        judging = self._judging_message()
        if self.result.verdict == Verdict.ok:
            head = f"{self.judge_name} accepted {judging}"
        elif self.result.verdict == Verdict.wrong_answer:
            head = f"{self.judge_name} rejected {judging}"
        elif self.result.verdict == Verdict.partial:
            head = f"{self.judge_name} partially accepted {judging}"
        elif self.result.verdict == Verdict.error:
            head = f"Solution failed on input {self.input}"
        elif self.result.verdict == Verdict.timeout:
            head = f"Solution did timeout on input {self.input}"

        text = f"{head}:\n{tab(self.result.output)}"
        if self.result.diff != "":
            text += "\n" + tab(f"diff:\n{tab(self.result.diff)}")

        return text


class RunCMSJudge(RunJudge):
    """Judge class with CMS helper functions"""

    def __init__(
        self,
        env: Env,
        judge: TaskPath,
        **kwargs,
    ) -> None:
        super().__init__(env=env, judge_name=judge.name, **kwargs)
        self.judge = judge
        self.points_file = TaskPath.points_file(self._env, self.judge_log_file.name)

    def _load_points(self, result: RunResult) -> float:
        points_str = result.raw_stdout(self._access_file).split("\n")[0]
        try:
            points = float(points_str)
        except ValueError:
            raise self._create_program_failure(
                "Judge didn't write points on stdout:", result
            )

        if not 0 <= points <= 1:
            raise self._create_program_failure(
                "Judge must give between 0 and 1 points:", result
            )

        return points

    def _load_solution_result(self, judge_run_result: RunResult) -> SolutionResult:
        if judge_run_result.returncode == 0:
            points = self._load_points(judge_run_result)
            if points == 1.0:
                verdict = Verdict.ok
            elif points == 0.0:
                verdict = Verdict.wrong_answer
            else:
                verdict = Verdict.partial

            return SolutionResult(
                verdict,
                points,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                judge_run_result.raw_stderr(self._access_file),
                self._quote_program(judge_run_result),
            )
        else:
            raise self._create_program_failure(
                f"Judge failed on {self._judging_message()}:", judge_run_result
            )


class RunBatchJudge(RunJudge):
    """Runs batch judge on single input. (Abstract class)"""

    def __init__(
        self,
        env: Env,
        judge_name: str,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=JUDGE_JOB_NAME.replace(r"(\w+)", output.name, 1),
            judge_name=judge_name,
            input_=input_,
            judge_log_file=TaskPath.log_file(self._env, output.name, judge_name),
            expected_points=expected_points,
            **kwargs,
        )
        self.output = output
        self.correct_output_name = correct_output
        self.correct_output = correct_output

    def _get_solution_run_res(self) -> RunResult:
        if "run_solution" in self.prerequisites_results:
            return self.prerequisites_results["run_solution"]
        else:
            # There is no solution (judging samples)
            # XXX: It didn't technically finish in 0 time.
            return RunResult(RunResultKind.OK, 0, 0.0, 0.0)

    def _judging_message(self) -> str:
        return f"output {self.output:p} for input {self.input:p}"

    def _nice_diff(self) -> str:
        """Create a nice diff between output and correct output."""
        diff = self._short_text(self._diff_files(self.correct_output, self.output))
        return colored_env(diff, "yellow", self._env)


class RunDiffJudge(RunBatchJudge):
    """Judges solution output and correct output using diff."""

    def __init__(
        self,
        env: Env,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_points: Optional[float],
    ) -> None:
        super().__init__(
            env=env,
            judge_name="diff",
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_points=expected_points,
        )

    def _judge(self) -> SolutionResult:
        self._access_file(self.output)
        self._access_file(self.correct_output)
        diff = subprocess.run(
            ["diff", "-Bbq", self.output.path, self.correct_output.path],
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
            return SolutionResult(
                Verdict.ok,
                1.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                "",
                self._quote_program(rr),
            )
        elif diff.returncode == 1:
            return SolutionResult(
                Verdict.wrong_answer,
                0.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
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
        judge: TaskPath,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        subtask: int,
        seed: str,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge_name=judge.name,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_points=expected_points,
            **kwargs,
        )
        self.judge = judge
        self.subtask = subtask
        self.seed = seed

    def _judge(self) -> SolutionResult:
        envs = {}
        if self._env.config.judge_needs_in:
            envs["TEST_INPUT"] = self.input.path
            self._access_file(self.input)
        if self._env.config.judge_needs_out:
            envs["TEST_OUTPUT"] = self.correct_output.path
            self._access_file(self.correct_output)

        result = self._run_program(
            ProgramType.judge,
            self.judge,
            args=[str(self.subtask), self.seed],
            stdin=self.output,
            stderr=self.judge_log_file,
            env=envs,
        )
        if result.returncode == 0:
            return SolutionResult(
                Verdict.ok,
                1.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                result.raw_stderr(self._access_file),
                self._quote_program(result),
            )
        elif result.returncode == 1:
            return SolutionResult(
                Verdict.wrong_answer,
                0.0,
                self._solution_run_res.time,
                self._solution_run_res.wall_time,
                result.raw_stderr(self._access_file),
                self._quote_program(result),
                self._nice_diff(),
            )
        else:
            raise self._create_program_failure(
                f"Judge failed on output {self.output:n}:", result
            )


class RunCMSBatchJudge(RunCMSJudge, RunBatchJudge):
    """Judges solution output using judge with CMS interface."""

    def __init__(
        self,
        env: Env,
        judge: TaskPath,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_points: Optional[float],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge=judge,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_points=expected_points,
            **kwargs,
        )

    def _judge(self) -> SolutionResult:
        self._access_file(self.input)
        self._access_file(self.output)
        self._access_file(self.correct_output)
        result = self._run_program(
            ProgramType.judge,
            self.judge,
            args=[
                self.input.path,
                self.correct_output.path,
                self.output.path,
            ],
            stdout=self.points_file,
            stderr=self.judge_log_file,
        )

        sol_result = self._load_solution_result(result)
        if sol_result.verdict != Verdict.ok:
            sol_result.diff = self._nice_diff()
        return sol_result


def judge_job(
    input_: TaskPath,
    output: TaskPath,
    correct_output: TaskPath,
    subtask: int,
    get_seed: Callable[[], str],
    expected_points: Optional[float],
    env: Env,
) -> Union[RunDiffJudge, RunKasiopeaJudge, RunCMSBatchJudge]:
    """Returns JudgeJob according to contest type."""
    if env.config.out_check == JudgeType.diff:
        return RunDiffJudge(env, input_, output, correct_output, expected_points)

    if env.config.out_judge is None:
        raise RuntimeError(f"Unset judge for out_check={env.config.out_check.name}")
    judge = TaskPath(env.config.out_judge)

    if env.config.contest_type == "cms":
        return RunCMSBatchJudge(
            env, judge, input_, output, correct_output, expected_points
        )
    else:
        return RunKasiopeaJudge(
            env,
            judge,
            input_,
            output,
            correct_output,
            subtask,
            get_seed(),
            expected_points,
        )
