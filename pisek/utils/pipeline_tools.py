# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from argparse import Namespace
from datetime import datetime
import os
import sys
from typing import Callable

from pisek.jobs.job_pipeline import JobPipeline
from pisek.utils.util import clean_non_relevant_files
from pisek.utils.text import eprint
from pisek.utils.terminal import TARGET_LINE_WIDTH
from pisek.utils.paths import INTERNALS_DIR
from pisek.utils.colors import ColorSettings
from pisek.env.env import Env
from pisek.jobs.cache import Cache

PATH = "."

LOCK_FILE = os.path.join(INTERNALS_DIR, "lock")


def run_pipeline(path: str, pipeline_class: Callable[[Env], JobPipeline], **env_args):
    with ChangedCWD(path):
        env = Env.load(**env_args)
        if env is None:
            return True
        cache = Cache.load()

        all_accessed_files: set[str] = set()
        for i in range(env.repeat):
            env.iteration = i  # XXX: Dirty trick
            if env.repeat > 1:
                if i != 0:
                    print()
                text = f" Run {i+1}/{env.repeat} "
                text = (
                    ((TARGET_LINE_WIDTH - len(text)) // 2) * "-"
                    + text
                    + ((TARGET_LINE_WIDTH - len(text) + 1) // 2) * "-"
                )
                print(ColorSettings.colored(text, "cyan"))
                print()

            pipeline = pipeline_class(env.fork())
            result = pipeline.run_jobs(cache, env)
            if result:
                return result
            all_accessed_files |= pipeline.all_accessed_files

        clean_non_relevant_files(all_accessed_files)
        return False


class ChangedCWD:
    def __init__(self, path):
        self._path = path

    def __enter__(self):
        self._orig_path = os.getcwd()
        os.chdir(self._path)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self._orig_path)


class Lock:
    def __init__(self, path):
        self._lock_file = os.path.join(path, LOCK_FILE)
        self._locked = False

    def __enter__(self):
        try:
            with open(self._lock_file, "x") as f:
                f.write(f"Locked by pisek at {datetime.now()}")
        except FileExistsError:
            eprint(
                f"Another pisek instance running in same directory. (Lockfile '{LOCK_FILE}')"
            )
            sys.exit(2)

        self._locked = True

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._locked and os.path.exists(self._lock_file):
            os.unlink(self._lock_file)


def locked_folder(f):
    def g(*args, **kwargs):
        with Lock(PATH):
            res = f(*args, **kwargs)
        return res

    return g


def with_env(fun: Callable[[Env, Namespace], int]) -> Callable[[Namespace], int]:
    def wrap(args) -> int:
        env = Env.load(**vars(args))

        if env is None:
            return 1

        return fun(env, args)

    return wrap
