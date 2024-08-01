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

from abc import abstractmethod

from pisek.env.env import Env
from pisek.jobs.jobs import PipelineItemFailure
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import ProgramsJob

from .input_info import InputInfo


class GeneratorListInputs(ProgramsJob):
    """Lists all inputs generator can generate."""

    def __init__(
        self, env: Env, generator: TaskPath, *, name: str = "", **kwargs
    ) -> None:
        self.generator = generator
        super().__init__(env=env, name=name or "List generator inputs", **kwargs)

    @abstractmethod
    def _run(self) -> list[InputInfo]:
        pass


class GenerateInput(ProgramsJob):
    """Generates input with given name."""

    def __init__(
        self,
        env: Env,
        generator: TaskPath,
        input_info: InputInfo,
        seed: int,
        *,
        name: str = "",
        **kwargs,
    ) -> None:
        self.generator = generator
        self.seed = seed
        self.input_info = input_info
        self.input_path = input_info.task_path(env, seed)
        super().__init__(
            env=env, name=name or f"Generate {self.input_path.name}", **kwargs
        )

    def _run(self) -> None:
        self._gen()

    @abstractmethod
    def _gen(self) -> None:
        pass


class GeneratorTestDeterminism(ProgramsJob):
    """Tests determinism of generating a given input."""

    def __init__(
        self,
        env: Env,
        generator: TaskPath,
        input_info: InputInfo,
        seed: int,
        *,
        name: str = "",
        **kwargs,
    ) -> None:
        self.generator = generator
        self.seed = seed
        self.input_info = input_info
        self.input = input_info.task_path(env, seed)
        super().__init__(env=env, name=name or f"Generate {self.input.name}", **kwargs)

    def _run(self) -> None:
        original = self.input.replace_suffix(".in2")
        self._rename_file(self.input, original)
        self._gen()
        if not self._files_equal(self.input, original):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {self.input:p} and {original:p} differ"
                + (f" (seed {self.seed:x})" if self.input_info.seeded else "")
                + "."
            )

    @abstractmethod
    def _gen(self) -> None:
        pass
