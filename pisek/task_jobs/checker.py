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
from pisek.utils.paths import TaskPath
from pisek.config.task_config import ProgramType
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.compile import Compile


class CheckerManager(TaskJobManager):
    """Runs checker on inputs."""

    def __init__(self):
        self.skipped_checker = ""
        super().__init__("Prepare checker")

    def _get_jobs(self) -> list[Job]:
        if self._env.config.checker is None:
            if self._env.strict:
                raise PipelineItemFailure("No checker specified in config.")
            else:
                self.skipped_checker = self._colored(
                    "Warning: No checker specified in config.\n"
                    "It is recommended to set `checker` is section [tests]",
                    "yellow",
                )
            return []

        return [Compile(self._env, self._env.config.checker)]

    def _get_status(self) -> str:
        if self.skipped_checker:
            if self.state == State.succeeded:
                return self.skipped_checker
            else:
                return ""
        else:
            return super()._get_status()


class CheckerJob(ProgramsJob):
    """Runs checker on single input."""

    def __init__(
        self,
        env: Env,
        checker: TaskPath,
        input_: TaskPath,
        subtask: int,
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
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"Checker failed on {self.input:p} (subtask {self.subtask}):",
                result,
            )
        return result
