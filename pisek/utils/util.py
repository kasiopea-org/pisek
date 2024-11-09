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

from pisek.jobs.cache import CACHE_FILENAME
from pisek.config.task_config import load_config

BUILD_DIR = "build/"


def rm_f(fn):
    try:
        os.unlink(fn)
    except FileNotFoundError:
        pass


def _clean_subdirs(task_dir: str, subdirs: list[str]) -> None:
    for subdir in subdirs:
        full = os.path.join(task_dir, subdir)
        try:
            shutil.rmtree(full)
        except FileNotFoundError:
            pass


def clean_task_dir(task_dir: str, pisek_directory: Optional[str]) -> bool:
    config = load_config(
        task_dir, suppress_warnings=True, pisek_directory=pisek_directory
    )
    if config is None:
        return False
    # XXX: ^ safeguard, raises an exception if task_dir isn't really a task
    # directory

    rm_f(os.path.join(task_dir, CACHE_FILENAME))
    _clean_subdirs(task_dir, [config.data_subdir.path, BUILD_DIR])
    return True
