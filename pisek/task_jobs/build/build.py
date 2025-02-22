# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

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
from pisek.utils.text import tab
from pisek.utils.paths import TaskPath, BUILD_DIR
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.task_job import TaskJob
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.config.task_config import BuildConfig
from pisek.config.config_types import BuildStrategyName
from pisek.task_jobs.build.strategies import BuildStrategy, AUTO_STRATEGIES, ALL_STRATEGIES

WORKING_DIR = os.path.join(BUILD_DIR, "_pisek")


class BuildManager(TaskJobManager):
    """Builds task programs."""

    def __init__(self):
        self.skipped_validator = ""
        super().__init__("Build programs")

    def _get_jobs(self) -> list[Job]:
        return [Build(self._env, build) for build in self._env.config.builds.values()]

    # TODO: Print used build strategies

class Build(TaskJob):
    """Job that compiles a program."""

    def __init__(
        self,
        env: Env,
        build_section: BuildConfig,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=f"Build {build_section.name}", **kwargs)
        self.build_section = build_section
    
    def _run(self):
        # TODO: Cache glob corresponding to resolved files
        sources = self._globs_to_files(
            [s + ".*" for s in self.build_section.sources] + self.build_section.sources,
            TaskPath(".") # TODO: Fix
        )

        if self.build_section.strategy == BuildStrategyName.auto:
            strategy = self._resolve_strategy(sources)
        else:
            strategy = ALL_STRATEGIES[self.build_section.strategy]

        if os.path.exists(WORKING_DIR):
            shutil.rmtree(WORKING_DIR)
        os.makedirs(WORKING_DIR, exist_ok=True)

        for source in sources:
            shutil.copy(source.path, os.path.join(WORKING_DIR, source.name))
        target = TaskPath(BUILD_DIR, self.build_section.name)
        shutil.copy(
            os.path.join(WORKING_DIR, strategy(self.build_section, self._env, self._print).build(WORKING_DIR)),
            target.path
        )
        self._access_file(source)
        self._access_file(target)

    def _resolve_strategy(self, sources: list[TaskPath]) -> BuildStrategy:
        applicable = []
        for strategy in AUTO_STRATEGIES:
            if strategy.applicable(self.build_section, list(map(lambda p: p.path, sources))):
                applicable.append(strategy)
        if len(applicable) == 0:
            raise PipelineItemFailure(
                f"No applicable build strategy for [build_{self.build_section.name}] with sources:\n" +
                tab("\n".join(source.col(self._env) for source in sources))
            )
        elif len(applicable) >= 2:
            names = " ".join(s.name for s in applicable)
            raise RuntimeError(f"Multiple strategies applicable: {names}")

        return applicable[0]

