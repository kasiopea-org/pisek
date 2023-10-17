# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
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
from pisek.jobs.jobs import State, Job
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import ProgramJob

class ToolsManager(TaskJobManager):
    def __init__(self):
        super().__init__("Preparing tools")

    def _get_jobs(self) -> list[Job]:
        jobs = [
            PrepareMinibox(self._env).init(),
            PrepareTextPreprocessor(self._env).init()
        ]
        return jobs


class PrepareMinibox(TaskJob):
    """Compiles minibox."""
    def _init(self) -> None:
        super()._init("Prepare Minibox")

    def _run(self):
        source = files('pisek').joinpath('tools/minibox.c')
        executable = self._executable('minibox')
        self._access_file(executable)
        os.makedirs(self._executable("."), exist_ok=True)
        gcc = subprocess.run([
            "gcc", source, "-o", executable,
            "-std=gnu11", "-D_GNU_SOURCE", "-O2", "-Wall", "-Wextra", "-Wno-parentheses", "-Wno-sign-compare", "-Wno-unused-result"
        ])
        if gcc.returncode != 0:
            self._fail("Minibox compilation failed.")

class PrepareTextPreprocessor(TaskJob):
    """Copies Text Preprocessor."""
    def _init(self) -> None:
        super()._init("Prepare text preprocessor")

    def _run(self):
        source = files("pisek").joinpath("tools/text-preproc.c")
        executable = self._executable("text-preproc")
        self._access_file(executable)
        os.makedirs(self._executable("."), exist_ok=True)
        gcc = subprocess.run([
            "gcc", source, "-o", executable,
            "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Wno-parentheses", "-Wno-sign-compare"
        ])
        if gcc.returncode != 0:
            self._fail("Text preprocessor compilation failed.")

class SanitizeAbstract(ProgramJob):
    def _sanitize(self, input_: str, output: str):
        result = self._run_program([], stdin=input_, stdout=output)
        if result is None:  # Something wrong in _run_program
            return None
        elif result.returncode == 42:
            return None
        elif result.returncode == 43:
            return self._program_fail(f"Text preprocessor failed on file: {self.input}", result)


class Sanitize(SanitizeAbstract):
    """Sanitize text file using Text Preprocessor."""
    def _init(self, input_: str, output: Optional[str] = None) -> None:
        self.input = self._data(input_)
        self.output = self._data(output if output is not None else input_ + ".clean")
        return super()._init(f"Sanitize {input_} -> {output}", "text-preproc")

    def _run(self):
        return self._sanitize(self.input, self.output)

        
class IsClean(SanitizeAbstract):
    """Check that file is same after using Text Preprocessor."""
    def _init(self, input_: str, output: Optional[str] = None) -> None:
        self.input = self._data(input_)
        self.output = self._data(output if output is not None else input_ + ".clean")
        return super()._init(f"{input_} is clean", "text-preproc")

    def _run(self):
        self._sanitize(self.input, self.output)
        if self.state == State.failed:
            return None
        
        if not self._files_equal(self.input, self.output):
            return self._fail(
                f"File {self.input} is not clean. Check encoding, missing newline at the end or \\r."
            )
