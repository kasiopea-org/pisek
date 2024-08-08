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

from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import ProgramsJob, RunResult, RunResultKind

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism


class OpendataV1ListInputs(GeneratorListInputs):
    """Lists all inputs for opendata-v1 generator - one for each subtask."""

    def __init__(self, env: Env, generator: TaskPath, **kwargs) -> None:
        super().__init__(env=env, generator=generator, **kwargs)

    def _run(self) -> list[InputInfo]:
        return [
            InputInfo.generated(f"{subtask:02}")
            for subtask in self._env.config.subtasks
            if subtask != 0
        ]


class OpendataV1GeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    generator: TaskPath
    seed: int
    input_info: InputInfo
    input_path: TaskPath

    def __init__(self, env: Env, *, name: str = "", **kwargs) -> None:
        super().__init__(env=env, name=name, **kwargs)

    def _gen(self) -> None:
        if self.seed < 0:
            raise ValueError(f"seed {self.seed} is negative")

        subtask = int(self.input_info.name)

        result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=[str(subtask), f"{self.seed:x}"],
            stdout=self.input_path,
            stderr=TaskPath.log_file(
                self._env, self.input_path.name, self.generator.name
            ),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on subtask {subtask}, seed {self.seed:x}:",
                result,
            )


class OpendataV1Generate(OpendataV1GeneratorJob, GenerateInput):
    """Generates input with given name."""

    pass


class OpendataV1TestDeterminism(OpendataV1GeneratorJob, GeneratorTestDeterminism):
    """Tests determinism of generating a given input."""

    pass
