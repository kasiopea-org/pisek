# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import re
import difflib
import subprocess
from glob import glob
import shutil
from typing import Optional, Iterator, List, Tuple

from pisek.jobs.cache import CACHE_FILENAME
from .compile import supported_extensions
from .task_config import TaskConfig

DEFAULT_TIMEOUT = 360
BUILD_DIR = "build/"


def rm_f(fn):
    try:
        os.unlink(fn)
    except FileNotFoundError:
        pass


def resolve_extension(path: str, name: str) -> Optional[str]:
    """
    Given a directory and `name`, finds a file named `name`.[ext],
    where [ext] is a file extension for one of the supported languages.

    If a name with a valid extension is given, it is returned unchanged
    """
    extensions = supported_extensions()
    candidates = []
    for ext in extensions:
        if os.path.isfile(os.path.join(path, name + ext)):
            candidates.append(name + ext)
        if name.endswith(ext) and os.path.isfile(os.path.join(path, name)):
            # Extension already present in `name`
            candidates.append(name)

    if len(candidates) > 1:
        raise RuntimeError(
            f"Existuje více řešení se stejným názvem: {', '.join(candidates)}"
        )

    return candidates[0] if candidates else None


def get_build_dir(task_dir: str) -> str:
    return os.path.normpath(os.path.join(task_dir, BUILD_DIR))


def pad_num(what: int, length=2):
    return f"{'0'*(length-len(str(what)))}{what}"


def get_input_name(seed: int, subtask: int) -> str:
    return f"{pad_num(subtask)}_{seed:x}.in"


def get_output_name(input_file: str, solution_name: str) -> str:
    """
    >>> get_output_name("sample.in", "solve_6b")
    'sample.solve_6b.out'
    """
    return "{}.{}.out".format(
        os.path.splitext(os.path.basename(input_file))[0],
        os.path.basename(solution_name),
    )


def _clean_subdirs(task_dir: str, subdirs: List[str]) -> None:
    for subdir in subdirs:
        full = os.path.join(task_dir, subdir)
        try:
            shutil.rmtree(full)
        except FileNotFoundError:
            pass


def clean_data_dir(task_config: TaskConfig, leave_inputs=False) -> None:
    """
    `leave_inputs` retains non-sample `.in` files.
    """
    data_dir = task_config.get_data_dir()

    try:
        for file in os.listdir(data_dir):
            if not leave_inputs or ("sample" in file) or (not file.endswith(".in")):
                os.remove(os.path.join(data_dir, file))
    except FileNotFoundError:
        pass


def clean_task_dir(task_dir: str) -> None:
    config = TaskConfig()
    err = config.load(task_dir)
    if err:
        print(err, file=sys.stderr)
        exit(1)
    # XXX: ^ safeguard, raises an exception if task_dir isn't really a task
    # directory

    from .cms.pack import SAMPLES_ZIP, TESTS_ZIP
    rm_f(SAMPLES_ZIP)
    rm_f(TESTS_ZIP)
    rm_f(CACHE_FILENAME)
    return _clean_subdirs(task_dir, [config.data_subdir, BUILD_DIR])


def get_expected_score(solution_name: str, config: TaskConfig) -> Optional[int]:
    """
    solve -> 10 (assuming 10 is the maximum score)
    solve_0b -> 0
    solve_jirka_4b -> 4
    """
    match = re.search(r"_([0-9]{1,3}|X)b$", solution_name)

    if match:
        if match[1] == "X":
            return None
        score = int(match[1])
        return score
    else:
        return config.get_maximum_score()


def quote_output(s, max_length=1500, max_lines=20):
    """
    Indicates that a string is a quote of another program's output by adding
    indentation and color.
    """
    if isinstance(s, bytes):
        s = s.decode("utf-8")

    while s and s[-1] == "\n":
        s = s[:-1]

    add_ellipsis = False

    if len(s) > max_length:
        s = s[:max_length]
        add_ellipsis = True

    lines = s.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        add_ellipsis = True

    s = "\n".join(("  " + l) for l in lines)

    if add_ellipsis:
        s += "\n  [...]"

    return s
