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
from typing import Optional

from pisek.env.env import Env
from pisek.jobs.jobs import PipelineItemFailure
from pisek.utils.paths import TaskPath
from pisek.task_jobs.task_job import TaskJob
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.data.testcase_info import TestcaseInfo, TestcaseGenerationMode


class GeneratorListInputs(ProgramsJob):
    """Lists all inputs generator can generate."""

    def __init__(self, env: Env, generator: str, *, name: str = "", **kwargs) -> None:
        self.generator = generator
        super().__init__(env=env, name=name or "List generator inputs", **kwargs)

    @abstractmethod
    def _run(self) -> list[TestcaseInfo]:
        pass


class GenerateInput(ProgramsJob):
    """Generates input with given name."""

    def __init__(
        self,
        env: Env,
        generator: str,
        testcase_info: TestcaseInfo,
        seed: Optional[int],
        *,
        name: str = "",
        **kwargs,
    ) -> None:
        assert testcase_info.generation_mode == TestcaseGenerationMode.generated

        self.generator = generator
        self.seed = seed
        self.testcase_info = testcase_info
        self.input_path = testcase_info.input_path(env, seed)
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
        generator: str,
        testcase_info: TestcaseInfo,
        seed: Optional[int],
        *,
        name: str = "",
        **kwargs,
    ) -> None:
        assert testcase_info.generation_mode == TestcaseGenerationMode.generated

        self.generator = generator
        self.seed = seed
        self.testcase_info = testcase_info
        self.input_path = testcase_info.input_path(env, seed)
        super().__init__(
            env=env,
            name=name or f"Generator is deterministic (on {self.input_path:p})",
            **kwargs,
        )

    def _run(self) -> None:
        input_path = self.input_path.to_raw(self._env.config.in_format)
        original = input_path.replace_suffix(".second")
        self._rename_file(input_path, original)
        self._gen()
        if not self._files_equal(input_path, original):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {input_path:p} and {original:p} differ"
                + (f" (seed {self.seed:016x})" if self.testcase_info.seeded else "")
                + "."
            )
        self._remove_file(original)

    @abstractmethod
    def _gen(self) -> None:
        pass


class GeneratorRespectsSeed(TaskJob):
    def __init__(
        self, env: Env, testcase_info: TestcaseInfo, seed1: int, seed2: int
    ) -> None:
        assert (
            testcase_info.generation_mode == TestcaseGenerationMode.generated
            and testcase_info.seeded
        )

        self.testcase_info = testcase_info
        self.seed1 = seed1
        self.seed2 = seed2
        self.input1 = testcase_info.input_path(self._env, seed1).to_raw(
            env.config.in_format
        )
        self.input2 = testcase_info.input_path(self._env, seed2).to_raw(
            env.config.in_format
        )
        super().__init__(
            env=env,
            name=f"Generator respects seed ({self.input1:n} and {self.input2:n})",
        )

    def _run(self) -> None:
        if self._files_equal(self.input1, self.input2):
            raise PipelineItemFailure(
                f"Inputs generated with different seed are same:\n"
                f"- {self.input1:p} (seed {self.seed1:016x})\n"
                f"- {self.input2:p} (seed {self.seed2:016x})"
            )
