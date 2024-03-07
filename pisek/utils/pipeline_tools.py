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
from pisek.utils.text import eprint
from pisek.env.env import Env
from pisek.jobs.cache import Cache

PATH = "."

LOCK_FILE = ".pisek_lock"


def run_pipeline(path: str, pipeline_class: Callable[[Env], JobPipeline], **env_args):
    with ChangedCWD(path):
        env = Env.load(**env_args)
        if env is None:
            return 1
        pipeline = pipeline_class(env.fork())
        return pipeline.run_jobs(Cache(env), env)


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
        if os.path.exists(self._lock_file):
            eprint("Another pisek instance running in same directory.")
            sys.exit(2)

        with open(self._lock_file, "w") as f:
            f.write(f"Locked by pisek at {datetime.now()}")
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
