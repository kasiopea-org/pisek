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
from pisek.task_jobs.task_job import TaskJob
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
        assert input_info.is_generated

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
        assert input_info.is_generated

        self.generator = generator
        self.seed = seed
        self.input_info = input_info
        self.input_path = input_info.task_path(env, seed)
        super().__init__(
            env=env,
            name=name or f"Generator is deterministic ({self.input_info.name})",
            **kwargs,
        )

    def _run(self) -> None:
        original = self.input_path.replace_suffix(".in2")
        self._rename_file(self.input_path, original)
        self._gen()
        if not self._files_equal(self.input_path, original):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {self.input_path:p} and {original:p} differ"
                + (f" (seed {self.seed:x})" if self.input_info.seeded else "")
                + "."
            )
        self._remove_file(original)

    @abstractmethod
    def _gen(self) -> None:
        pass


class GeneratorRespectsSeed(TaskJob):
    def __init__(self, env: Env, input_info: InputInfo, seed1: int, seed2: int) -> None:
        assert input_info.is_generated and input_info.seeded

        self.input_info = input_info
        self.seed1 = seed1
        self.seed2 = seed2
        self.input1 = input_info.task_path(self._env, seed1)
        self.input2 = input_info.task_path(self._env, seed2)
        super().__init__(
            env=env,
            name=f"Generator respects seed ({self.input1:n} and {self.input2:n})",
        )

    def _run(self) -> None:
        if self._files_equal(self.input1, self.input2):
            raise PipelineItemFailure(
                f"Inputs generated with different seed are same:\n"
                f"- {self.input1:p} (seed {self.seed1:x})\n"
                f"- {self.input2:p} (seed {self.seed2:x})"
            )
