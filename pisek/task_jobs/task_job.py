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

from decimal import Decimal
import filecmp
import glob
from math import ceil
import os
import shutil
from typing import (
    Any,
    Callable,
    Concatenate,
    Iterable,
    Literal,
    Optional,
    ParamSpec,
    TypeVar,
)

import subprocess
from pisek.env.env import Env
from pisek.config.task_config import RunConfig
from pisek.utils.paths import TaskPath
from pisek.utils.text import tab
from pisek.config.task_config import ProgramType
from pisek.jobs.jobs import Job

T = TypeVar("T")
P = ParamSpec("P")


class TaskHelper:
    _env: Env

    def _globs_to_files(
        self, globs: Iterable[str], directory: TaskPath
    ) -> list[TaskPath]:
        """Get files in given directory that match any glob."""
        files: list[str] = sum(
            (glob.glob(g, root_dir=directory.path) for g in globs),
            start=[],
        )
        files = list(sorted(set(files)))
        return [TaskPath.from_abspath(directory.path, file) for file in files]

    def _format_points(self, points: Optional[Decimal | int]) -> str:
        precision = self._env.config.score_precision
        if points is None:
            text = "?" + "." * (precision > 0) + "?" * precision
        else:
            text = f"{points:.{precision}f}"

        return text + "p"

    def _path_list(self, paths: list[TaskPath]) -> str:
        return "\n".join(path.col(self._env) for path in paths)

    @staticmethod
    def _short_list(arr: list[str], cutoff: int = 1) -> str:
        inputs_text = ", ".join(arr[:cutoff])
        if len(arr) > cutoff:
            inputs_text += ",…"
        return inputs_text

    @staticmethod
    def _short_text(
        text: str,
        style: Literal["h", "t", "ht"] = "h",
        max_lines: int = 10,
        max_chars: int = 100,
    ) -> str:
        """
        Shorten text to max_lines lines and max_chars on line.
        Keep lines from head / tail / both depending on style.
        """
        s_text = []
        for line in text.split("\n"):
            if len(line) > max_chars:
                line = line[: max_chars - 1] + "…"
            s_text.append(line)
        if len(s_text) < max_lines:
            return "\n".join(s_text)

        tail = max(ceil(("t" in style) * max_lines / len(style)) - 1, 0)
        head = max_lines - tail - 1
        return "\n".join(s_text[:head] + ["[…]"] + (s_text[-tail:] if tail else []))

    @staticmethod
    def makedirs(path: TaskPath, exist_ok: bool = True):
        """Make directories"""
        os.makedirs(path.path, exist_ok=exist_ok)

    @staticmethod
    def make_filedirs(path: TaskPath, exist_ok: bool = True):
        """Make directories for given file"""
        os.makedirs(os.path.dirname(path.path), exist_ok=exist_ok)


class TaskJob(Job, TaskHelper):
    """Job class that implements useful methods"""

    def _access_dir(self, dirname: TaskPath) -> None:
        for file in self._globs_to_files(["**"], dirname):
            self._access_file(file)

    @staticmethod
    def _file_access(files: int):
        """Adds first i args as accessed files."""

        def dec(
            f: Callable[Concatenate["TaskJob", P], T],
        ) -> Callable[Concatenate["TaskJob", P], T]:
            def g(self: "TaskJob", *args: P.args, **kwargs: P.kwargs) -> T:
                for i in range(files):
                    arg = args[i]
                    assert isinstance(arg, TaskPath)
                    self._access_file(arg)
                return f(self, *args, **kwargs)

            return g

        return dec

    @_file_access(1)
    def _open_file(self, filename: TaskPath, mode="r", **kwargs):
        if "w" in mode:
            self.make_filedirs(filename)
        return open(filename.path, mode, **kwargs)

    @_file_access(1)
    def _exists(self, path: TaskPath):
        return os.path.exists(path.path)

    @_file_access(1)
    def _is_file(self, path: TaskPath):
        return os.path.isfile(path.path)

    @_file_access(1)
    def _is_dir(self, path: TaskPath):
        return os.path.isdir(path.path)

    def _remove_file(self, filename: TaskPath):
        "Removes given file. It must be created inside this job."
        self._accessed_files.remove(filename.path)
        return os.remove(filename.path)

    @_file_access(1)
    def _file_size(self, filename: TaskPath):
        return os.path.getsize(filename.path)

    @_file_access(1)
    def _file_not_empty(self, filename: TaskPath):
        with self._open_file(filename) as f:
            content = f.read()
        return len(content.strip()) > 0

    @_file_access(2)
    def _copy_file(self, filename: TaskPath, dst: TaskPath) -> None:
        self.make_filedirs(dst)
        shutil.copy(filename.path, dst.path)

    def _copy_dir(self, path: TaskPath, dst: TaskPath) -> None:
        self.make_filedirs(dst)
        shutil.copytree(path.path, dst.path)
        self._access_dir(path)
        self._access_dir(dst)

    def _copy_target(self, path: TaskPath, dst: TaskPath):
        if self._is_dir(path):
            self._copy_dir(path, dst)
        else:
            self._copy_file(path, dst)

    @_file_access(2)
    def _rename_file(self, filename: TaskPath, dst: TaskPath) -> None:
        self.make_filedirs(dst)
        return os.rename(filename.path, dst.path)

    @_file_access(2)
    def _link_file(self, filename: TaskPath, dst: TaskPath, overwrite: bool = False):
        self.make_filedirs(dst)
        if overwrite and os.path.exists(dst.path):
            os.remove(dst.path)

        # os.link should follow symlinks, but doesn't:
        # https://bugs.python.org/issue37612
        source = filename.path
        while os.path.islink(source):
            source = os.readlink(source)

        return os.link(source, dst.path)

    @_file_access(2)
    def _symlink_file(self, filename: TaskPath, dst: TaskPath, overwrite: bool = False):
        self.make_filedirs(dst)
        if overwrite and os.path.exists(dst.path):
            os.remove(dst.path)

        return os.symlink(
            os.path.relpath(filename.path, os.path.dirname(dst.path)), dst.path
        )

    @_file_access(2)
    def _files_equal(self, file_a: TaskPath, file_b: TaskPath) -> bool:
        return filecmp.cmp(file_a.path, file_b.path)

    @_file_access(2)
    def _diff_files(self, file_a: TaskPath, file_b: TaskPath) -> str:
        diff = subprocess.run(
            ["diff", file_a.path, file_b.path, "-Bb", "-u2"],
            stdout=subprocess.PIPE,
        )
        return diff.stdout.decode("utf-8")

    def _globs_to_files(
        self, globs: Iterable[str], directory: TaskPath
    ) -> list[TaskPath]:
        self._accessed_globs |= set(globs)
        return super()._globs_to_files(globs, directory)

    def _quote_file(self, file: TaskPath, **kwargs) -> str:
        """Get shortened file contents"""
        with self._open_file(file) as f:
            return self._short_text(f.read().strip(), **kwargs)

    def _quote_file_with_name(
        self, file: TaskPath, force_content: bool = False, **kwargs
    ) -> str:
        """
        Get file name (with its shortened content if env.file_contents or force_content)
        for printing into terminal
        """
        if force_content or self._env.file_contents:
            return f"{file.col(self._env)}\n{self._colored(tab(self._quote_file(file, **kwargs)), 'yellow')}\n"
        else:
            return f"{file.col(self._env)}\n"
