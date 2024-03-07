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

from typing import Any, Optional

from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.env.task_config import ProgramType
from pisek.utils.terminal import colored_env
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramsJob
from pisek.jobs.parts.compile import Compile


class CheckerManager(TaskJobManager):
    """Runs checker on inputs."""

    def __init__(self):
        self.skipped_checker = ""
        super().__init__("Running checker")

    def _get_jobs(self) -> list[Job]:
        if self._env.config.checker is None:
            if self._env.strict:
                raise PipelineItemFailure("No checker specified in config.")
            else:
                self.skipped_checker = colored_env(
                    "Warning: No checker specified in config.\n"
                    "It is recommended to set `checker` is section [tests]",
                    "yellow",
                    self._env,
                )
            return []

        checker = TaskPath(self._env.config.checker)

        jobs: list[Job] = [compile := Compile(self._env, checker)]

        self.loose_subtasks = []
        for sub_num, sub in self._env.config.subtasks.items():
            if sub_num == 0:
                continue  # Skip samples
            for inp in self._subtask_inputs(sub):
                jobs.append(
                    check := CheckerJob(
                        self._env, checker, inp, sub_num, RunResultKind.OK
                    )
                )
                check.add_prerequisite(compile)
            if sub.predecessors:
                self.loose_subtasks.append(LooseCheckJobGroup(sub_num))
                for pred in sub.predecessors:
                    self.loose_subtasks[-1].jobs[pred] = []
                    for inp in self._subtask_new_inputs(sub):
                        jobs.append(
                            check := CheckerJob(self._env, checker, inp, pred, None)
                        )
                        self.loose_subtasks[-1].jobs[pred].append(check)
                        check.add_prerequisite(compile)

        return jobs

    def _evaluate(self) -> None:
        if len(self.jobs) == 0:
            return

        for loose_subtask in self.loose_subtasks:
            err = loose_subtask.failed(self._env.config.fail_mode)
            if err is not None:
                raise PipelineItemFailure(err)

    def _get_status(self) -> str:
        if self.skipped_checker:
            if self.state == State.succeeded:
                return self.skipped_checker
            else:
                return ""
        else:
            return super()._get_status()


class LooseCheckJobGroup:
    """
    Groups jobs on subtask where checker is run on predecessors instead.
    Checking that checker is strict enough - checking fails when run on predecessor.
    """

    def __init__(self, num: int):
        self.num = num
        self.jobs: dict[int, list[CheckerJob]] = {}

    def failed(self, fail_mode: str) -> Optional[str]:
        """Returns whether jobs resulted as expected."""

        def result_kind(job: CheckerJob) -> RunResultKind:
            if job.result is None:
                raise RuntimeError(f"Job {job.name} has not finished yet.")
            return job.result.kind

        for pred in self.jobs:
            results = list(map(result_kind, self.jobs[pred]))
            if fail_mode == "all" and RunResultKind.OK in results:
                job = self._index_job(pred, results, RunResultKind.OK)
                return (
                    f"Checker is not strict enough:\n"
                    f"All inputs of subtask {self.num} should have not passed on predecessor subtask {pred}\n"
                    f"but on input {job.input} did not."
                )
            if fail_mode == "any" and RunResultKind.RUNTIME_ERROR not in results:
                return (
                    f"Checker is not strict enough:\n"
                    f"An input of subtask {self.num} should have not passed on predecessor subtask {pred}\n"
                    f"but all have passed."
                )
            if RunResultKind.TIMEOUT in results:
                to_job = self._index_job(pred, results, RunResultKind.TIMEOUT)
                return f"Checker timeouted on input {to_job.input}, subtask {self.num}."
        return None

    def _index_job(
        self, pred: int, results: list[RunResultKind], result: RunResultKind
    ) -> "CheckerJob":
        return self.jobs[pred][results.index(result)]


class CheckerJob(ProgramsJob):
    """Runs checker on single input."""

    def __init__(
        self,
        env: Env,
        checker: TaskPath,
        input_: TaskPath,
        subtask: int,
        expected: Optional[RunResultKind],
        **kwargs,
    ):
        super().__init__(
            env=env, name=f"Check {input_:n} on subtask {subtask}", **kwargs
        )
        self.checker = checker
        self.subtask = subtask
        self.input = input_
        self.log_file = TaskPath.log_file(
            self._env, input_.name, f"{self.checker.name}{subtask}"
        )
        self.expected = expected

    def _check(self) -> RunResult:
        return self._run_program(
            ProgramType.checker,
            self.checker,
            args=[str(self.subtask)],
            stdin=self.input,
            stderr=self.log_file,
        )

    def _run(self) -> RunResult:
        result = self._check()
        if self.expected == RunResultKind.OK != result.kind:
            raise self._create_program_failure(
                f"Checker failed on {self.input:p} (subtask {self.subtask}) but should have succeeded.",
                result,
            )
        elif self.expected == RunResultKind.RUNTIME_ERROR != result.kind:
            raise self._create_program_failure(
                f"Checker succeeded on {self.input:p} (subtask {self.subtask}) but should have failed.",
                result,
            )
        return result
