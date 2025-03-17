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

from abc import abstractmethod
from importlib.resources import files
import os
import subprocess

from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.utils.paths import TaskPath, SanitizablePath
from pisek.config.task_config import ProgramType
from pisek.task_jobs.task_job import TaskJob
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.run_result import RunResult, RunResultKind


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


class PrepareJudgeLibJudge(TaskJob):
    """Compiles judge from judgelib."""

    def __init__(self, env: Env, judge_name: str, judge: str, **kwargs) -> None:
        self.judge = judge
        super().__init__(env=env, name=f"Prepare {judge_name}", **kwargs)

    def _run(self):
        source_files = ["util.cc", "io.cc", "token.cc", "random.cc", f"{self.judge}.cc"]
        source_dir = files("pisek").joinpath("tools/judgelib")
        sources = [source_dir.joinpath(file) for file in source_files]

        executable = TaskPath.executable_path(self._env, self.judge)
        self._access_file(executable)

        gpp = subprocess.run(
            [
                "g++",
                *sources,
                "-I",
                source_dir,
                "-o",
                executable.path,
                "-std=gnu++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Wno-parentheses",
                "-Wno-sign-compare",
            ]
        )

        if gpp.returncode != 0:
            raise PipelineItemFailure(f"{self.judge_name} compilation failed.")


class PrepareTokenJudge(PrepareJudgeLibJudge):
    """Compiles judge-token from judgelib."""

    def __init__(self, env: Env, **kwargs) -> None:
        super().__init__(
            env=env, judge_name="token judge", judge="judge-token", **kwargs
        )


class PrepareShuffleJudge(PrepareJudgeLibJudge):
    """Compiles judge-shuffle from judgelib."""

    def __init__(self, env: Env, **kwargs) -> None:
        super().__init__(
            env=env, judge_name="shuffle judge", judge="judge-shuffle", **kwargs
        )


class TextPreprocAbstract(ProgramsJob):
    """Abstract job that has method for file sanitization."""

    def _run_text_preproc(self, input_: TaskPath, output: TaskPath) -> None:
        try:
            os.remove(output.path)
        except FileNotFoundError:
            pass

        result = self._run_tool(
            "text-preproc",
            stdin=input_,
            stdout=output,
        )
        if result.returncode != 42:
            raise self._create_program_failure(
                f"Text preprocessor failed on file: {input_:p}", result
            )


class SanitizeAbstact(TaskJob):
    def __init__(self, env: Env, input_: TaskPath, output: TaskPath, **kwargs) -> None:
        self.input = input_
        self.output = output
        super().__init__(env=env, **kwargs)

    def _run(self) -> None:
        result = self.prerequisites_results.get("create_source", None)
        if isinstance(result, RunResult) and result.kind != RunResultKind.OK:
            self._copy_file(self.input, self.output)
            return

        self._sanitize()

    @abstractmethod
    def _sanitize(self) -> None:
        pass


class Sanitize(SanitizeAbstact, TextPreprocAbstract):
    """Sanitize text file using Text Preprocessor."""

    def __init__(self, env: Env, input_: TaskPath, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env, input_, output, name=f"Sanitize {input_:n} -> {output:n}", **kwargs
        )

    def _sanitize(self):
        return self._run_text_preproc(self.input, self.output)


class IsClean(SanitizeAbstact, TextPreprocAbstract):
    """Check that file is same after sanitizing with Text Preprocessor."""

    def __init__(self, env: Env, input_: TaskPath, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env, input_, output, name=f"Check {input_:n} is clean", **kwargs
        )

    def _sanitize(self):
        self._run_text_preproc(self.input, self.output)
        if not self._files_equal(self.input, self.output):
            raise PipelineItemFailure(
                f"File {self.input:n} is not clean. Check encoding, missing newline at the end or \\r."
            )
