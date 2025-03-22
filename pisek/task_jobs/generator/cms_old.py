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

import os
import shutil

from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.config.task_config import RunConfig
from pisek.utils.paths import TaskPath, LogPath
from pisek.task_jobs.program import RunResultKind
from pisek.task_jobs.data.testcase_info import TestcaseInfo

from .base_classes import GeneratorListInputs, GenerateInput


class CmsOldListInputs(GeneratorListInputs):
    """Lists all inputs for cms-old generator - by running it."""

    def __init__(self, env: Env, generator: RunConfig, **kwargs) -> None:
        super().__init__(env, generator, name="Run generator", **kwargs)

    def _run(self) -> list[TestcaseInfo]:
        """Generates all inputs."""
        gen_dir = TaskPath.generated_path(self._env, ".")
        try:
            shutil.rmtree(gen_dir.path)
        except FileNotFoundError:
            pass
        self.makedirs(gen_dir, exist_ok=False)

        run_result = self._run_program(
            ProgramType.gen,
            self.generator,
            args=[gen_dir.path],
            stderr=LogPath.generator_log(self.generator.name),
        )
        self._access_dir(gen_dir)

        if run_result.kind != RunResultKind.OK:
            raise self._create_program_failure("Generator failed:", run_result)

        testcases = []
        for inp in self._globs_to_files(["*"], TaskPath.generated_path(self._env, ".")):
            if inp.path.endswith(".in"):
                testcases.append(
                    TestcaseInfo.generated(inp.path.removesuffix(".in"), seeded=False)
                )
        return testcases


class CmsOldGenerate(GenerateInput):
    def __init__(
        self,
        env: Env,
        generator: RunConfig,
        testcase_info: TestcaseInfo,
        seed: int,
        **kwargs,
    ) -> None:
        super().__init__(
            env,
            generator,
            testcase_info,
            seed,
            name=f"Serve {testcase_info.input_path(env).name}",
            **kwargs,
        )

    def _gen(self):
        self._link_file(
            TaskPath.generated_path(self._env, self.input_path.name),
            self.input_path.to_raw(self._env.config.in_format),
            overwrite=True,
        )
