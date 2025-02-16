# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional

from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath, InputPath, OutputPath
from pisek.task_jobs.program import ProgramsJob, RunResultKind
from pisek.task_jobs.data.testcase_info import TestcaseInfo

from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism


class OpendataV1ListInputs(GeneratorListInputs):
    """Lists all inputs for opendata-v1 generator - one for each test."""

    def __init__(self, env: Env, generator: str, **kwargs) -> None:
        super().__init__(env=env, generator=generator, **kwargs)

    def _run(self) -> list[TestcaseInfo]:
        return [
            TestcaseInfo.generated(f"{test:02}")
            for test in self._env.config.tests
            if test != 0
        ]


class OpendataV1GeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    generator: str
    seed: Optional[int]
    testcase_info: TestcaseInfo
    input_path: InputPath

    def __init__(self, env: Env, *, name: str = "", **kwargs) -> None:
        super().__init__(env=env, name=name, **kwargs)

    def _gen(self) -> None:
        assert self.seed is not None
        if self.seed < 0:
            raise ValueError(f"seed {self.seed} is negative")

        test = int(self.testcase_info.name)

        result = self._run_program(
            ProgramType.gen,
            self.generator,
            args=[str(test), f"{self.seed:016x}"],
            stdout=self.input_path,
            stderr=self.input_path.to_log(self.generator),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on test {test}, seed {self.seed:016x}:",
                result,
            )


class OpendataV1Generate(OpendataV1GeneratorJob, GenerateInput):
    """Generates input with given name."""

    pass


class OpendataV1TestDeterminism(OpendataV1GeneratorJob, GeneratorTestDeterminism):
    """Tests determinism of generating a given input."""

    pass
