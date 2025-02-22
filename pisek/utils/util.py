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
import shutil
from typing import Optional

from pisek.config.task_config import load_config
from pisek.utils.paths import BUILD_DIR, TESTS_DIR, INTERNALS_DIR


class ChangedCWD:
    def __init__(self, path):
        self._path = path

    def __enter__(self):
        self._orig_path = os.getcwd()
        os.chdir(self._path)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self._orig_path)


def _clean_subdirs(task_dir: str, subdirs: list[str]) -> None:
    for subdir in subdirs:
        full = os.path.join(task_dir, subdir)
        try:
            shutil.rmtree(full)
        except FileNotFoundError:
            pass


def is_task_dir(task_dir: str, pisek_directory: Optional[str]) -> bool:
    # XXX: Safeguard, raises an exception if task_dir isn't really a task
    # directory
    config = load_config(
        task_dir, suppress_warnings=True, pisek_directory=pisek_directory
    )
    return config is not None


def clean_task_dir(task_dir: str, pisek_directory: Optional[str]) -> bool:
    _clean_subdirs(task_dir, [BUILD_DIR, TESTS_DIR, INTERNALS_DIR])
    return True


def clean_non_relevant_files(accessed_files: set[str]) -> None:
    for root, _, files in os.walk(TESTS_DIR):
        for file in files:
            path = os.path.join(root, file)
            if path not in accessed_files:
                os.remove(path)
