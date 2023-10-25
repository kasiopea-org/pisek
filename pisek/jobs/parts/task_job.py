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

from enum import Enum
import filecmp
import os
import shutil
import glob
from typing import Optional, Any, Callable

import pisek.util as util
from pisek.env import Env
from pisek.task_config import SubtaskConfig
from pisek.jobs.jobs import Job
from pisek.jobs.status import StatusJobManager

BUILD_DIR = "build/"

Verdict = Enum("Verdict", ["ok", "partial", "wrong_answer", "error", "timeout"])
RESULT_MARK = {
    Verdict.ok: "·",
    Verdict.partial: "P",
    Verdict.error: "!",
    Verdict.timeout: "T",
    Verdict.wrong_answer: "W",
}


class TaskHelper:
    _env: Env

    def _get_build_dir(self) -> str:
        return BUILD_DIR

    def _resolve_path(self, *path: str) -> str:
        """Like os.path.join but adds current task directory."""
        return os.path.normpath(os.path.join(self._env.task_dir, *path))

    def _executable(self, name: str) -> str:
        """Path to executable with given basename."""
        return self._resolve_path(self._get_build_dir(), name)

    def _sample(self, name: str) -> str:
        """Path to sample with given basename."""
        return self._resolve_path(self._env.config.samples_subdir, name)

    def _data(self, name: str) -> str:
        """Path to data file (input or output) with given basename."""
        return self._resolve_path(self._env.config.data_subdir, name)

    def _output(self, input_name: str, solution: str):
        """Path to output from given input and solution."""
        return self._data(util.get_output_name(input_name, solution))

    def _solution(self, name: str) -> str:
        """Path to solution with given basename."""
        return self._resolve_path(self._env.config.solutions_subdir, name)

    def _get_seed(self, input_name: str):
        """Get seed from input name."""
        parts = os.path.splitext(os.path.basename(input_name))[0].split("_")
        if len(parts) == 1:
            return "0"
        else:
            return parts[-1]

    def _get_samples(self) -> list[tuple[str, str]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        ins = self._globs_to_files(
            self._env.config.subtasks[0].all_globs, dir=self._env.config.samples_subdir
        )
        outs = list(map(lambda inp: os.path.splitext(inp)[0] + ".out", ins))

        def basename(s: str):
            return str(os.path.basename(s))

        return list(zip(map(basename, ins), map(basename, outs)))

    def _all_inputs(self) -> list[str]:
        """Get all input files"""
        all_inputs: list[str] = sum(
            [
                self._subtask_inputs(subtask)
                for _, subtask in sorted(self._env.config.subtasks.items())
            ],
            start=[],
        )
        seen = set()
        unique_all = []
        for inp in all_inputs:
            if inp not in seen:
                seen.add(inp)
                unique_all.append(inp)
        return unique_all

    def _subtask_inputs(self, subtask: SubtaskConfig) -> list[str]:
        """Get all inputs of given subtask."""
        if self._env.config.contest_type == "cms":
            return self._globs_to_files(subtask.all_globs)
        else:
            inputs = set([])
            for glob in subtask.all_globs:
                inputs |= set(self._globs_to_files([glob])[: self._env.inputs])
            return list(sorted(inputs))

    def _subtask_new_inputs(self, subtask: SubtaskConfig) -> list[str]:
        """Get new inputs of given subtask."""
        inputs = self._globs_to_files(subtask.in_globs)
        if self._env.config.contest_type == "kasiopea":
            inputs = inputs[: self._env.inputs]
        return inputs

    def _globs_to_files(self, globs: list[str], dir: Optional[str] = None):
        if dir is None:
            dir = self._env.config.data_subdir
        dir = self._resolve_path(dir)

        input_filenames: list[str] = []
        for g in globs:
            input_filenames += [
                os.path.basename(f) for f in glob.glob(os.path.join(dir, g))
            ]
        input_filenames.sort()
        return input_filenames


class TaskJobManager(StatusJobManager, TaskHelper):
    """JobManager class that implements useful methods"""

    def _get_timeout(self, target: str) -> float:
        if self._env.timeout is not None:
            return self._env.timeout

        if target == "solve":
            return self._env.config.timeout_model_solution
        elif target == "sec_solve":
            return self._env.config.timeout_other_solutions
        else:
            raise ValueError(f"Unknown timeout for: {target}.")

    def _compile_args(self) -> dict[str, str]:
        compile_args = {}
        if self._env.config.solution_manager:
            compile_args["manager"] = self._resolve_path(
                self._env.config.solution_manager
            )
        return compile_args


class TaskJob(Job, TaskHelper):
    """Job class that implements useful methods"""

    @staticmethod
    def _file_access(files: int):
        """Adds first i args as accessed files."""

        def dec(f: Callable[..., Any]) -> Callable[..., Any]:
            def g(self, *args, **kwargs):
                for i in range(files):
                    self._access_file(args[i])
                return f(self, *args, **kwargs)

            return g

        return dec

    @_file_access(1)
    def _open_file(self, filename: str, mode="r", **kwargs):
        if "w" in mode:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        return open(filename, mode, **kwargs)

    @_file_access(1)
    def _file_exists(self, filename: str):
        return os.path.isfile(os.path.join(filename))

    @_file_access(1)
    def _file_size(self, filename: str):
        return os.path.getsize(filename)

    @_file_access(1)
    def _file_not_empty(self, filename: str):
        with self._open_file(filename) as f:
            content = f.read()
        return len(content.strip()) > 0

    @_file_access(2)
    def _copy_file(self, filename: str, dst: str):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        return shutil.copy(filename, dst)

    @_file_access(2)
    def _files_equal(self, file_a: str, file_b: str) -> bool:
        return filecmp.cmp(file_a, file_b)
