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
import re
import difflib
import subprocess
from glob import glob
import shutil
from typing import Optional, Iterator, List, Tuple

import termcolor

from .compile import supported_extensions
from .task_config import TaskConfig

DEFAULT_TIMEOUT = 360
BUILD_DIR = "build/"


def rm_f(fn):
    try:
        os.unlink(fn)
    except FileNotFoundError:
        pass


def files_are_equal(file_a: str, file_b: str) -> bool:
    """
    Checks if the contents of `file_a` and `file_b` are equal,
    ignoring leading and trailing whitespace.

    If one or both files don't exist, False is returned.
    """

    try:
        with open(file_a, "r") as fa:
            with open(file_b, "r") as fb:
                while True:
                    la = fa.readline()
                    lb = fb.readline()
                    if not la and not lb:
                        # We have reached the end of both files
                        return True
                    # ignore leading/trailing whitespace
                    la = la.strip()
                    lb = lb.strip()
                    if la != lb:
                        return False
    except FileNotFoundError:
        return False


def diff_files(
    file_a: str,
    file_b: str,
    file_a_name: Optional[str] = None,
    file_b_name: Optional[str] = None,
) -> Iterator[str]:
    """
    Produces a human-friendly diff of `file_a` and `file_b`
    as a string iterator.

    Uses `file_a_name` and `file_b_name` for specifying
    a human-friendly name for the files.
    """
    if file_a_name is None:
        file_a_name = file_a
    if file_b_name is None:
        file_b_name = file_b

    try:
        with open(file_a, "r") as fa:
            lines_a = [line.strip() + "\n" for line in fa.readlines()]
    except FileNotFoundError:
        lines_a = [f"({file_a_name} neexistuje)"]

    try:
        with open(file_b, "r") as fb:
            lines_b = [line.strip() + "\n" for line in fb.readlines()]
    except FileNotFoundError:
        lines_b = [f"({file_b_name} neexistuje)"]

    diff = difflib.unified_diff(
        lines_a, lines_b, fromfile=file_a_name, tofile=file_b_name, n=2
    )

    return diff


def resolve_extension(path: str, name: str) -> Optional[str]:
    """
    Given a directory and `name`, finds a file named `name`.[ext],
    where [ext] is a file extension for one of the supported languages.

    If a name with a valid extension is given, it is returned unchanged
    """
    extensions = supported_extensions()
    candidates = []
    for name in [name, get_name_without_expected_score(name)]:
        for ext in extensions:
            if os.path.isfile(os.path.join(path, name + ext)):
                candidates.append(name + ext)
            if name.endswith(ext) and os.path.isfile(os.path.join(path, name)):
                # Extension already present in `name`
                candidates.append(name)
        if len(candidates):
            break

    if len(candidates) > 1:
        raise RuntimeError(
            f"Existuje více řešení se stejným názvem: {', '.join(candidates)}"
        )

    return candidates[0] if candidates else None


def get_build_dir(task_dir: str) -> str:
    return os.path.join(task_dir, BUILD_DIR)


def get_samples(task_dir: str) -> List[Tuple[str, str]]:
    """Returns the list [(sample1.in, sample1.out), …] in the given directory."""
    ins = glob(os.path.join(task_dir, "sample*.in"))
    outs = []
    for i in ins:
        out = os.path.splitext(i)[0] + ".out"
        if not os.path.isfile(out):
            raise RuntimeError(f"Ke vzorovému vstupu {i} neexistuje výstup {out}")
        outs.append(out)
    return list(zip(ins, outs))


def get_input_name(seed: int, subtask: int) -> str:
    return f"{seed:x}_{subtask}.in"


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
    config = TaskConfig(task_dir)
    # XXX: ^ safeguard, raises an exception if task_dir isn't really a task
    # directory
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
    config = TaskConfig(task_dir)

    from .cms.pack import SAMPLES_ZIP, TESTS_ZIP

    rm_f(SAMPLES_ZIP)
    rm_f(TESTS_ZIP)

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


def get_name_without_expected_score(solution_name: str) -> str:
    match = re.search(r"_([0-9]{1,3}|X)b$", solution_name)

    if match:
        return solution_name[: match.span()[0]]
    return solution_name


def quote_output(s, color="yellow", max_length=1500, max_lines=20):
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

    s = "\n".join(("  " + termcolor.colored(l, color)) for l in lines)

    if add_ellipsis:
        s += "\n  [...]"

    return s


def quote_process_output(
    proc: subprocess.CompletedProcess, include_stdout=True, include_stderr=True
):
    res = []
    if include_stdout:
        cur = "stdout:"
        if proc.stdout:
            cur += "\n" + quote_output(proc.stdout)
        else:
            cur += " (žádný)"
        res.append(cur)

    if include_stderr:
        cur = "stderr:"
        if proc.stderr:
            cur += "\n" + quote_output(proc.stderr)
        else:
            cur += " (žádný)"
        res.append(cur)

    return "\n".join(res)


def file_is_newer(file_a: str, file_b: str) -> Optional[bool]:
    """
    Returns True if file in `path_a` is newer (more recently modified) than `path_b`.
    Returns None if either of the files does not exist.
    """
    try:
        return os.path.getmtime(file_a) > os.path.getmtime(file_b)
    except FileNotFoundError:
        return None
