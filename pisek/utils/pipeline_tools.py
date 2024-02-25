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

from datetime import datetime
import os
import sys

from pisek.utils.terminal import eprint
from pisek.config.env import Env
from pisek.jobs.cache import Cache

PATH = "."

LOCKED = False
LOCK_FILE = ".pisek_lock"


def run_pipeline(path, pipeline, **env_args):
    env = Env.load(path, **env_args)
    if env is None:
        return 1
    pipeline = pipeline(env.fork())
    return pipeline.run_jobs(Cache(env), env)


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
