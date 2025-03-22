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

from pisek.env.env import Env
from pisek.utils.paths import InputPath
from pisek.config.task_config import ProgramType, RunConfig
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob


class ValidatorJob(ProgramsJob):
    """Runs validator on single input."""

    def __init__(
        self,
        env: Env,
        validator: RunConfig,
        input_: InputPath,
        test: int,
        **kwargs,
    ):
        super().__init__(env=env, name=f"Validate {input_:n} on test {test}", **kwargs)
        self.validator = validator
        self.test = test
        self.input = input_
        self.log_file = input_.to_log(f"{validator.name}{test}")

    def _validate(self) -> RunResult:
        return self._run_program(
            ProgramType.validator,
            self.validator,
            args=[str(self.test)],
            stdin=self.input,
            stderr=self.log_file,
        )

    def _run(self) -> RunResult:
        result = self._validate()
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"Validator failed on {self.input:p} (test {self.test}):",
                result,
            )
        return result
