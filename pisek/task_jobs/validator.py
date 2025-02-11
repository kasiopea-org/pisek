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

from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.utils.paths import TaskPath, InputPath
from pisek.config.task_config import ProgramType
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.compile import Compile


class ValidatorManager(TaskJobManager):
    """Runs validator on inputs."""

    def __init__(self):
        self.skipped_validator = ""
        super().__init__("Prepare validator")

    def _get_jobs(self) -> list[Job]:
        if self._env.config.validator is None:
            if self._env.strict:
                raise PipelineItemFailure("No validator specified in config.")
            else:
                self.skipped_validator = self._colored(
                    "Warning: No validator specified in config.\n"
                    "It is recommended to set `validator` is section [tests]",
                    "yellow",
                )
            return []

        return [Compile(self._env, self._env.config.validator_path)]

    def _get_status(self) -> str:
        if self.skipped_validator:
            if self.state == State.succeeded:
                return self.skipped_validator
            else:
                return ""
        else:
            return super()._get_status()


class ValidatorJob(ProgramsJob):
    """Runs validator on single input."""

    def __init__(
        self,
        env: Env,
        validator: str,
        input_: InputPath,
        test: int,
        **kwargs,
    ):
        super().__init__(env=env, name=f"Check {input_:n} on test {test}", **kwargs)
        self.validator = validator
        self.test = test
        self.input = input_
        self.log_file = input_.to_log(f"{validator}{test}")

    def _check(self) -> RunResult:
        return self._run_program(
            ProgramType.validator,
            self.validator,
            args=[str(self.test)],
            stdin=self.input,
            stderr=self.log_file,
        )

    def _run(self) -> RunResult:
        result = self._check()
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"Validator failed on {self.input:p} (test {self.test}):",
                result,
            )
        return result
