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

import filecmp
import glob
import os
import fnmatch
import shutil
from typing import Optional, Any, Callable

import pisek.util as util
import subprocess
from pisek.env import Env
from pisek.task_config import SubtaskConfig
from pisek.jobs.jobs import Job
from pisek.jobs.status import StatusJobManager

BUILD_DIR = "build/"

GENERATED_SUBDIR = "generated/"
INPUTS_SUBDIR = "inputs/"
OUTPUTS_SUBDIR = "out/"

TOOLS_MAN_CODE = "tools"
GENERATOR_MAN_CODE = "generator"
INPUTS_MAN_CODE = "inputs"
CHECKER_MAN_CODE = "checker"
JUDGE_MAN_CODE = "judge"
SOLUTION_MAN_CODE = "solution"
DATA_MAN_CODE = "data"


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
    
    def _data(self, *path: list[str]) -> str:
        """Path to data file."""
        return self._resolve_path(self._env.config.data_subdir, *path)
    
    def _static(self, name: str) -> str:
        """Path to generated input."""
        return self._resolve_path(self._env.config.static_subdir, name)

    def _generated_input(self, name: str) -> str:
        """Path to generated input."""
        return self._data(GENERATED_SUBDIR, name)

    def _input(self, name: str) -> str:
        """Path to input."""
        return self._data(INPUTS_SUBDIR, name)

    def _output(self, name: str):
        """Path to output from given input and solution."""
        return self._data(OUTPUTS_SUBDIR, name)

    def _output_from_input(self, input_name: str, solution: str):
        """Path to output from given input and solution."""
        return self._data(OUTPUTS_SUBDIR, util.get_output_name(input_name, solution))

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

    @staticmethod
    def filter_globs(files: list[str], globs: list[str]):
        return [file for file in files if any(fnmatch.fnmatch(file, g) for g in globs)]

    @staticmethod
    def globs_to_files(globs: list[str], directory: Optional[str] = None) -> list[str]:
        files: list[str] = sum(
            (glob.glob(g, root_dir=directory) for g in globs), start=[]
        )
        return list(sorted(set(files)))

    @staticmethod
    def _short_text(text: str, max_lines: int = 15, max_chars: int = 100) -> str:
        short_text = []
        for i, line in enumerate(text.split("\n", max_lines)):
            if i < max_lines:
                if len(line) > max_chars:
                    line = f"{line[:max_chars-3]}..."
                short_text.append(line)
            else:
                short_text[-1] = "[...]\n"
                break

        return "\n".join(short_text)


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

    def _get_samples(self) -> list[tuple[str, str]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        ins = self._subtask_inputs(self._env.config.subtasks['0'])
        outs = map(lambda x: x.replace(".in", ".out"), ins)
        return list(zip(ins, outs))

    def _all_inputs(self) -> list[str]:
        """Get all input files"""
        return self.prerequisites_results[INPUTS_MAN_CODE]["inputs"]

    def _subtask_inputs(self, subtask: SubtaskConfig) -> list[str]:
        """Get all inputs of given subtask."""
        return self.filter_globs(self._all_inputs(), subtask.all_globs)

    def _subtask_new_inputs(self, subtask: SubtaskConfig) -> list[str]:
        """Get new inputs of given subtask."""
        return self.filter_globs(self._all_inputs(), subtask.in_globs)


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

    @_file_access(2)
    def _diff_files(self, file_a: str, file_b: str) -> str:
        diff = subprocess.run(
            ["diff", file_a, file_b, "-B", "-u2"], stdout=subprocess.PIPE
        )
        return diff.stdout.decode("utf-8")
