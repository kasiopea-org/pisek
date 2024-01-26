# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
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
from pisek.env import Env
from pisek.task_config import ProgramType
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import ProgramsJob


class ToolsManager(TaskJobManager):
    """Manager that prepares all tools necessary for task testing."""

    def __init__(self):
        super().__init__("Preparing tools")

    def _get_jobs(self) -> list[Job]:
        self.makedirs(self._executable("."))
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
        executable = self._executable("minibox")
        self._access_file(executable)
        gcc = subprocess.run(
            [
                "gcc",
                source,
                "-o",
                executable,
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
        executable = self._executable("text-preproc")
        self._access_file(executable)
        gcc = subprocess.run(
            [
                "gcc",
                source,
                "-o",
                executable,
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

    def _sanitize(self, input_: str, output: str) -> None:
        result = self._run_program(
            ProgramType.tool, "text-preproc", stdin=input_, stdout=output
        )
        if result.returncode == 43:
            raise self._create_program_failure(
                f"Text preprocessor failed on file: {input_}", result
            )


class Sanitize(SanitizeAbstract):
    """Sanitize text file using Text Preprocessor."""

    def __init__(
        self, env: Env, input_: str, output: Optional[str] = None, **kwargs
    ) -> None:
        super().__init__(env=env, name=f"Sanitize {input_} -> {output}", **kwargs)
        self.input = self._data(input_)
        self.output = self._data(output if output is not None else input_ + ".clean")

    def _run(self):
        return self._sanitize(self.input, self.output)


class IsClean(SanitizeAbstract):
    """Check that file is same after sanitizing with Text Preprocessor."""

    def __init__(
        self, env: Env, input_: str, output: Optional[str] = None, **kwargs
    ) -> None:
        super().__init__(env=env, name=f"{os.path.basename(input_)} is clean", **kwargs)
        self.input = input_
        self.output = self._sanitized(
            output if output is not None else os.path.basename(input_) + ".clean"
        )

    def _run(self):
        self._sanitize(self.input, self.output)
        if self.state == State.failed:
            return None

        if not self._files_equal(self.input, self.output):
            raise PipelineItemFailure(
                f"File {self.input} is not clean. Check encoding, missing newline at the end or \\r."
            )
