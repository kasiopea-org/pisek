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

import os
from importlib.resources import files
from typing import Optional

import subprocess
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.env.task_config import ProgramType
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import ProgramsJob


class ToolsManager(TaskJobManager):
    """Manager that prepares all tools necessary for task testing."""

    def __init__(self):
        super().__init__("Preparing tools")

    def _get_jobs(self) -> list[Job]:
        self.makedirs(TaskPath.executable_path(self._env, "."))
        jobs: list[Job] = [
            PrepareMinibox(self._env),
            PrepareTextPreprocessor(self._env),
        ]
        return jobs


class PrepareMinibox(TaskJob):
    """Compiles minibox."""

    def __init__(self, env: Env, **kwargs) -> None:
        super().__init__(env=env, name="Prepare Minibox", **kwargs)

    def _run(self):
        source = files("pisek").joinpath("tools/minibox.c")
        executable = TaskPath.executable_path(self._env, "minibox")
        self._access_file(executable)
        gcc = subprocess.run(
            [
                "gcc",
                source,
                "-o",
                executable.path,
                "-std=gnu11",
                "-D_GNU_SOURCE",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Wno-parentheses",
                "-Wno-sign-compare",
                "-Wno-unused-result",
            ]
        )
        if gcc.returncode != 0:
            raise PipelineItemFailure("Minibox compilation failed.")


class PrepareTextPreprocessor(TaskJob):
    """Compiles Text Preprocessor."""

    def __init__(self, env: Env, **kwargs) -> None:
        super().__init__(env=env, name="Prepare text preprocessor", **kwargs)

    def _run(self):
        source = files("pisek").joinpath("tools/text-preproc.c")
        executable = TaskPath.executable_path(self._env, "text-preproc")
        self._access_file(executable)
        gcc = subprocess.run(
            [
                "gcc",
                source,
                "-o",
                executable.path,
                "-std=gnu11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Wno-parentheses",
                "-Wno-sign-compare",
            ]
        )
        if gcc.returncode != 0:
            raise PipelineItemFailure("Text preprocessor compilation failed.")


class SanitizeAbstract(ProgramsJob):
    """Abstract job that has method for file sanitization."""

    def _sanitize(self, input_: TaskPath, output: TaskPath) -> None:
        result = self._run_program(
            ProgramType.tool,
            TaskPath.executable_path(self._env, "text-preproc"),
            stdin=input_,
            stdout=output,
        )
        if result.returncode == 43:
            raise self._create_program_failure(
                f"Text preprocessor failed on file: {input_:p}", result
            )


class Sanitize(SanitizeAbstract):
    """Sanitize text file using Text Preprocessor."""

    def __init__(
        self, env: Env, input_: TaskPath, output: Optional[TaskPath] = None, **kwargs
    ) -> None:
        self.input = input_
        self.output = (
            output if output else TaskPath.sanitized_file(self._env, input_.path)
        )
        super().__init__(
            env=env, name=f"Sanitize {self.input:n} -> {self.output:n}", **kwargs
        )

    def _run(self):
        return self._sanitize(self.input, self.output)


class IsClean(SanitizeAbstract):
    """Check that file is same after sanitizing with Text Preprocessor."""

    def __init__(
        self, env: Env, input_: TaskPath, output: Optional[TaskPath] = None, **kwargs
    ) -> None:
        self.input = input_
        self.output = (
            output if output else TaskPath.sanitized_file(self._env, input_.path)
        )
        super().__init__(env=env, name=f"{self.input:n} is clean", **kwargs)

    def _run(self):
        self._sanitize(self.input, self.output)
        if not self._files_equal(self.input, self.output):
            raise PipelineItemFailure(
                f"File {self.input:n} is not clean. Check encoding, missing newline at the end or \\r."
            )
