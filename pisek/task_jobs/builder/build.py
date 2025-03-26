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
from typing import Optional

from pisek.utils.text import tab
from pisek.utils.paths import TaskPath, BUILD_DIR

from pisek.env.env import Env, TestingTarget
from pisek.config.task_config import BuildConfig, RunConfig
from pisek.config.config_types import BuildStrategyName, OutCheck

from pisek.task_jobs.tools import PrepareTokenJudge, PrepareShuffleJudge
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.task_jobs.task_job import TaskJob
from pisek.task_jobs.task_manager import TaskJobManager

from pisek.task_jobs.builder.strategies import (
    BuildStrategy,
    AUTO_STRATEGIES,
    ALL_STRATEGIES,
)

WORKING_DIR = os.path.join(BUILD_DIR, "_workspace")


class BuildManager(TaskJobManager):
    """Builds task programs."""

    def __init__(self):
        super().__init__("Build programs")

    def _build(self, run: Optional[RunConfig]) -> Optional["Build"]:
        if run is None:
            return None
        return Build(self._env, run.build)

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job | None] = []

        jobs.append(self._build(self._env.config.in_gen))
        jobs.append(self._build(self._env.config.validator))
        if self._env.target in (TestingTarget.solution, TestingTarget.all):
            if self._env.config.out_check == OutCheck.judge:
                jobs.append(self._build(self._env.config.out_judge))
            elif self._env.config.out_check == OutCheck.tokens:
                jobs.append(PrepareTokenJudge(self._env))
            elif self._env.config.out_check == OutCheck.shuffle:
                jobs.append(PrepareShuffleJudge(self._env))

            for solution in self._env.solutions:
                jobs.append(self._build(self._env.config.solutions[solution].run))

        filtered_jobs = []
        for j in jobs:
            if j is not None:
                filtered_jobs.append(j)
        return filtered_jobs


class Build(TaskJob):
    """Job that compiles a program."""

    def __init__(
        self,
        env: Env,
        build_section: BuildConfig,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=f"Build {build_section.program_name}", **kwargs)
        self.build_section = build_section

    def _resolve_program(self, glob: TaskPath) -> set[TaskPath]:
        result = self._globs_to_files([f"{glob.path}.*", glob.path], TaskPath("."))
        if len(result) == 0:
            raise PipelineItemFailure(f"No paths found for {glob.col(self._env)}.")
        return set(result)

    def _check_nonmixed_sources(self, sources: set[TaskPath]) -> None:
        if any(map(self._is_dir, sources)) and any(map(self._is_file, sources)):
            raise PipelineItemFailure(
                f"Mixed files and directories for sources:\n"
                + tab(self._path_list(list(sorted(sources))))
            )

    def _strategy_sources(
        self, strategy: type[BuildStrategy], sources: set[TaskPath]
    ) -> set[TaskPath]:
        new_sources = set()
        if strategy.extra_sources is not None:
            for part in getattr(self.build_section, strategy.extra_sources):
                new_sources |= self._resolve_program(part)
        return sources | new_sources

    def _strategy_extras(
        self, strategy: type[BuildStrategy], extras: set[TaskPath]
    ) -> set[TaskPath]:
        new_extras = set()
        if strategy.extra_nonsources is not None:
            new_extras = set(getattr(self.build_section, strategy.extra_nonsources))
        return extras | new_extras

    def _run(self) -> None:
        sources: set[TaskPath] = set()
        extras: set[TaskPath] = set(self.build_section.extras)
        for part in self.build_section.sources:
            sources |= self._resolve_program(part)
        self._check_nonmixed_sources(sources)

        if self.build_section.strategy == BuildStrategyName.auto:
            strategy = self._resolve_strategy(sources)
        else:
            strategy = ALL_STRATEGIES[self.build_section.strategy]

        sources = self._strategy_sources(strategy, sources)
        extras = self._strategy_extras(strategy, extras)
        self._check_nonmixed_sources(sources)

        if self._env.verbosity >= 1:
            msg = f"Building '{self.build_section.program_name}' using build strategy '{strategy.name}'."
            self._print(self._colored(tab(msg), "magenta"))

        if os.path.exists(WORKING_DIR):
            shutil.rmtree(WORKING_DIR)
        os.makedirs(WORKING_DIR, exist_ok=True)

        for path in sources | extras:
            # Intentionally avoiding caching results
            dst = os.path.join(WORKING_DIR, path.name)
            if self._is_dir(path):
                shutil.copytree(path.path, dst)
                self._access_dir(path)
            elif self._is_file(path):
                shutil.copy(path.path, dst)
                self._access_file(path)
            else:
                raise PipelineItemFailure(f"No path {path.col(self._env)} exists.")

        target = TaskPath(BUILD_DIR, self.build_section.program_name)
        self.make_filedirs(target)
        if os.path.isdir(target.path):
            shutil.rmtree(target.path)
        elif os.path.isfile(target.path):
            os.remove(target.path)

        executable_name = strategy(self.build_section, self._env, self._print).build(
            WORKING_DIR,
            list(map(lambda p: p.name, sources)),
            list(map(lambda p: p.name, extras)),
        )
        executable = os.path.join(WORKING_DIR, executable_name)
        # Intentionally avoiding caching sources
        if os.path.isdir(executable):
            shutil.copytree(executable, target.path)
            self._access_dir(target)
        else:
            shutil.copy(executable, target.path)
            self._access_file(target)

    def _resolve_strategy(self, sources: set[TaskPath]) -> type[BuildStrategy]:
        applicable = []
        for strategy in AUTO_STRATEGIES:
            strat_sources = self._strategy_sources(strategy, sources)
            if strategy.applicable(
                self.build_section, list(map(lambda p: p.path, strat_sources))
            ):
                applicable.append(strategy)
        if len(applicable) == 0:
            raise PipelineItemFailure(
                f"No applicable build strategy for [{self.build_section.section_name}] with sources:\n"
                + tab(self._path_list(list(sorted(sources))))
            )
        elif len(applicable) >= 2:
            names = " ".join(s.name for s in applicable)
            raise RuntimeError(f"Multiple strategies applicable: {names}")

        return applicable[0]
