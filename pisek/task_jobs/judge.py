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
from decimal import Decimal
from functools import cache
import os
import random
import subprocess
from typing import Any, Optional, Union, Callable

from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.config.config_types import TaskType, ProgramType, OutCheck, JudgeType
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.utils.text import tab
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.compile import Compile
from pisek.task_jobs.chaos_monkey import Incomplete, ChaosMonkey
from pisek.task_jobs.tools import PrepareTokenJudge, Sanitize
from pisek.task_jobs.solution.solution_result import (
    Verdict,
    SolutionResult,
    RelativeSolutionResult,
    AbsoluteSolutionResult,
)


class JudgeManager(TaskJobManager):
    """Manager that prepares and test judge."""

    def __init__(self) -> None:
        super().__init__("Preparing judge")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        comp: Optional[Job] = None

        if self._env.config.out_check == OutCheck.judge:
            if self._env.config.out_judge is None:
                raise RuntimeError(
                    f"Unset judge for out_check={self._env.config.out_check.name}"
                )
            jobs.append(comp := Compile(self._env, self._env.config.out_judge))
        elif self._env.config.out_check == OutCheck.tokens:
            jobs.append(comp := PrepareTokenJudge(self._env))

        samples = self._get_static_samples()
        if self._env.config.task_type == TaskType.communication:
            return jobs

        for inp, out in samples:
            jobs.append(
                judge_j := judge_job(
                    inp,
                    out,
                    out,
                    0,
                    lambda: "0",
                    Verdict.ok,
                    self._env,
                )
            )
            if comp is not None:
                judge_j.add_prerequisite(comp)

            if os.stat(out.path).st_size > 0:
                JOBS = [(Incomplete, 10), (ChaosMonkey, 50)]

                total = sum(map(lambda x: x[1], JOBS))
                random.seed(4)  # Reproducibility!
                seeds = random.sample(range(0, 16**4), total)

                for job, times in JOBS:
                    for _ in range(times):
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
                        if comp is not None:
                            run_judge.add_prerequisite(comp)
                        run_judge.add_prerequisite(invalidate)
        return jobs

    def _compute_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        result["judge_outs"] = set()
        for job in self.jobs:
            if isinstance(job, RunJudge):
                if isinstance(job, RunCMSJudge):
                    result["judge_outs"].add(job.points_file)
                result["judge_outs"].add(job.judge_log_file)

        return result


class RunJudge(ProgramsJob):
    """Runs judge on single input. (Abstract class)"""

    def __init__(
        self,
        env: Env,
        name: str,
        subtask: int,
        judge_name: str,
        input_: TaskPath,
        judge_log_file: TaskPath,
        expected_verdict: Optional[Verdict],
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.subtask = subtask
        self.input = input_
        self.judge_name = judge_name
        self.judge_log_file = judge_log_file
        self.expected_verdict = expected_verdict

        self.result: Optional[SolutionResult]

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
            result = RelativeSolutionResult(
                Verdict.error, None, self._solution_run_res, None, Decimal(0)
            )
        elif self._solution_run_res.kind == RunResultKind.TIMEOUT:
            result = RelativeSolutionResult(
                Verdict.timeout, None, self._solution_run_res, None, Decimal(0)
            )

        if (
            self.expected_verdict is not None
            and result.verdict != self.expected_verdict
        ):
            raise PipelineItemFailure(
                f"{self._judging_message_capitalized()} should have got verdict '{self.expected_verdict}' but got '{result.verdict}'."
            )

        return result

    def message(self) -> str:
        """Message about how judging ended."""
        if self.result is None:
            raise RuntimeError(f"Job {self.name} has not finished yet.")

        sol_rr = self.result.solution_rr
        judge_rr = self.result.judge_rr

        text = f"input: {self._quote_file_with_name(self.input)}"
        if isinstance(self, RunBatchJudge):
            text += f"correct output: {self._quote_file_with_name(self.correct_output)}"
        text += f"result: {self.result.verdict.name}\n"

        text += "solution:\n"
        text += tab(
            self._format_run_result(
                sol_rr,
                status=sol_rr.kind != RunResultKind.OK,
                stderr_force_content=sol_rr.kind == RunResultKind.RUNTIME_ERROR,
                time=True,
            )
        )
        text += "\n"
        if judge_rr is not None:
            text += (
                f"{self.judge_name}:\n"
                + tab(
                    self._format_run_result(
                        judge_rr,
                        status=isinstance(self, RunDiffJudge | RunTokenJudge),
                        stderr_force_content=True,
                    )
                )
                + "\n"
            )

        return text

    def verdict_text(self) -> str:
        if self.result is not None:
            if self.result.message is not None:
                return self.result.message
            return self.result.verdict.name
        else:
            return self.state.name

    def verdict_mark(self) -> str:
        if self.state == State.cancelled:
            return "-"
        elif self.result is None:
            return " "
        elif self.result.verdict == Verdict.partial_ok:
            if isinstance(self.result, RelativeSolutionResult):
                return f"[{self.result.relative_points:.2f}]"
            elif isinstance(self.result, AbsoluteSolutionResult):
                return f"[={self.result.absolute_points:.{self._env.config.score_precision}f}]"
            else:
                raise ValueError(
                    f"Unexpected SolutionResult type: '{type(self.result)}'"
                )
        else:
            return self.result.verdict.mark()

    @property
    def full_points(self) -> float:
        return self.rel_to_abs_points(1.0)

    def rel_to_abs_points(self, rel_points: float) -> float:
        return self._env.config.subtasks[self.subtask].points * rel_points


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

    def _load_points(self, result: RunResult) -> Decimal:
        with self._open_file(result.stdout_file) as f:
            points_str = f.read().split("\n")[0]
        try:
            points = Decimal(points_str)
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
                verdict = Verdict.partial_ok

            with self._open_file(judge_run_result.stderr_file) as f:
                message = f.readline().removesuffix("\n")

            return RelativeSolutionResult(
                verdict, message, self._solution_run_res, judge_run_result, points
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
        subtask: int,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_verdict: Optional[Verdict],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=f"Judge {output:n}",
            judge_name=judge_name,
            subtask=subtask,
            input_=input_,
            judge_log_file=TaskPath.log_file(self._env, output.name, judge_name),
            expected_verdict=expected_verdict,
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


class RunDiffJudge(RunBatchJudge):
    """Judges solution output and correct output using diff."""

    def __init__(
        self,
        env: Env,
        subtask: int,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_verdict: Optional[Verdict],
    ) -> None:
        super().__init__(
            env=env,
            judge_name="diff",
            subtask=subtask,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_verdict=expected_verdict,
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
            status=("Files are the same" if diff.returncode == 0 else "Files differ")
            + f": {self.output.col(self._env)} {self.correct_output.col(self._env)}",
        )
        if diff.returncode == 0:
            return RelativeSolutionResult(
                Verdict.ok, None, self._solution_run_res, rr, Decimal(1)
            )
        elif diff.returncode == 1:
            return RelativeSolutionResult(
                Verdict.wrong_answer, None, self._solution_run_res, rr, Decimal(0)
            )
        else:
            raise PipelineItemFailure(
                f"Diff failed:\n{tab(diff.stderr.decode('utf-8'))}"
            )


class RunTokenJudge(RunBatchJudge):
    """Judges solution output and correct output using judge-token."""

    def __init__(
        self,
        env: Env,
        subtask: int,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_verdict: Optional[Verdict],
    ) -> None:
        super().__init__(
            env=env,
            judge_name="judge-token",
            subtask=subtask,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_verdict=expected_verdict,
        )

    def _judge(self) -> SolutionResult:
        self._access_file(self.output)
        self._access_file(self.correct_output)

        executable = TaskPath.executable_path(self._env, "judge-token")
        flags = ["-t"]

        if self._env.config.tokens_ignore_newlines:
            flags.append("-n")
        if self._env.config.tokens_ignore_case:
            flags.append("-i")
        if self._env.config.tokens_float_rel_error != None:
            flags.extend(
                [
                    "-r",
                    "-e",
                    str(self._env.config.tokens_float_rel_error),
                    "-E",
                    str(self._env.config.tokens_float_abs_error),
                ]
            )

        judge = subprocess.run(
            [executable.path, *flags, self.output.path, self.correct_output.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stderr = judge.stderr.decode("utf-8")

        # XXX: Okay, it didn't finish in no time, but this is not meant to be used
        rr = RunResult(
            RunResultKind.OK,
            judge.returncode,
            0,
            0,
            status=(stderr.strip() or "Files are equivalent")
            + f": {self.output.col(self._env)} {self.correct_output.col(self._env)}",
        )

        if judge.returncode == 42:
            return RelativeSolutionResult(
                Verdict.ok, None, self._solution_run_res, rr, Decimal(1)
            )
        elif judge.returncode == 43:
            return RelativeSolutionResult(
                Verdict.wrong_answer, None, self._solution_run_res, rr, Decimal(0)
            )
        else:
            raise PipelineItemFailure(f"Token judge failed:\n{tab(stderr)}")


class RunOpendataJudge(RunBatchJudge):
    """Judges solution output using judge with the opendata interface. (Abstract class)"""

    @property
    @abstractmethod
    def return_code_ok(self) -> int:
        pass

    @property
    @abstractmethod
    def return_code_wa(self) -> int:
        pass

    def __init__(
        self,
        env: Env,
        judge: TaskPath,
        subtask: int,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        seed: str,
        expected_verdict: Optional[Verdict],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge_name=judge.name,
            subtask=subtask,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_verdict=expected_verdict,
            **kwargs,
        )
        self.judge = judge
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
        if result.returncode == self.return_code_ok:
            return RelativeSolutionResult(
                Verdict.ok, None, self._solution_run_res, result, Decimal(1)
            )
        elif result.returncode == self.return_code_wa:
            return RelativeSolutionResult(
                Verdict.wrong_answer, None, self._solution_run_res, result, Decimal(0)
            )
        else:
            raise self._create_program_failure(
                f"Judge failed on output {self.output:n}:", result
            )


class RunOpendataV1Judge(RunOpendataJudge):
    """Judges solution output using judge with the opendataV1 interface."""

    @property
    def return_code_ok(self) -> int:
        return 0

    @property
    def return_code_wa(self) -> int:
        return 1


class RunCMSBatchJudge(RunCMSJudge, RunBatchJudge):
    """Judges solution output using judge with CMS interface."""

    def __init__(
        self,
        env: Env,
        judge: TaskPath,
        subtask: int,
        input_: TaskPath,
        output: TaskPath,
        correct_output: TaskPath,
        expected_verdict: Optional[Verdict],
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            judge=judge,
            subtask=subtask,
            input_=input_,
            output=output,
            correct_output=correct_output,
            expected_verdict=expected_verdict,
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
        return sol_result


def judge_job(
    input_: TaskPath,
    output: TaskPath,
    correct_output: TaskPath,
    subtask: int,
    get_seed: Callable[[], str],
    expected_verdict: Optional[Verdict],
    env: Env,
) -> Union[RunDiffJudge, RunTokenJudge, RunOpendataV1Judge, RunCMSBatchJudge]:
    """Returns JudgeJob according to contest type."""
    if env.config.out_check == OutCheck.diff:
        return RunDiffJudge(
            env, subtask, input_, output, correct_output, expected_verdict
        )

    if env.config.out_check == OutCheck.tokens:
        return RunTokenJudge(
            env, subtask, input_, output, correct_output, expected_verdict
        )

    if env.config.out_judge is None:
        raise RuntimeError(f"Unset judge for out_check={env.config.out_check.name}")

    if env.config.judge_type == JudgeType.cms_batch:
        return RunCMSBatchJudge(
            env,
            env.config.out_judge,
            subtask,
            input_,
            output,
            correct_output,
            expected_verdict,
        )
    else:
        return RunOpendataV1Judge(
            env,
            env.config.out_judge,
            subtask,
            input_,
            output,
            correct_output,
            get_seed(),
            expected_verdict,
        )
