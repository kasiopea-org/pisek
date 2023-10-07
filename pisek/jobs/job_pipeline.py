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

from abc import ABC, abstractmethod
from collections import deque
import sys
import ansi.cursor as cur

from pisek.env import Env
from pisek.jobs.jobs import State, PipelineItem, Job, JobManager
from pisek.jobs.cache import Cache

class JobPipeline(ABC):
    """Runs given Jobs and JobManagers according to their prerequisites."""
    @abstractmethod
    def __init__(self):
        self.failed = False
        self._tmp_lines = 0

    def run_jobs(self, cache: Cache, env: Env) -> bool:
        self.job_managers : deque[JobManager] = deque()
        self.pipeline : deque[PipelineItem] = deque(self.pipeline)
        while len(self.pipeline) or len(self.job_managers):
            p_item = self.pipeline.popleft()
            if isinstance(p_item, JobManager):
                self.job_managers.append(p_item)
                self.pipeline.extendleft(reversed(p_item.create_jobs(env)))
            elif isinstance(p_item, Job):
                p_item.run_job(cache)
                p_item.finish()
            else:
                raise TypeError(f"Objects in {self.__class__.__name__} should be either Job or JobManager.")

            if p_item.dirty:
                self._tmp_lines = 0

            # we really need to call status_update to update messages
            # Also no logs into env for just writing to stdout
            self.failed |= not self._status_update(env.fork())
            if self.failed and not env.full:
                break

        cache.seal(not self.failed)  # Remove duplicate cache entries and seal
        return self.failed

    def _status_update(self, env: Env) -> bool:
        """Display current progress. Return true if there were no failures."""
        for _ in range(self._tmp_lines):
            print(f"{cur.up()}{cur.erase_line()}", end="")
        self._tmp_lines = 0

        while len(self.job_managers):
            job_man = self.job_managers.popleft()
            ongoing_msg = job_man.update()  # We are updating job_man's state with this call!
            if not env.full and job_man.any_failed():
                self._print(ongoing_msg, env)
                self._print(job_man.failures(), env, end='', file=sys.stderr)
                return False
            if job_man.state == State.failed or job_man.ready():
                msg = job_man.finalize()
                if msg:
                    self._print(msg, env)
                if job_man.state == State.failed:
                    self._print(job_man.failures(), env, end='', file=sys.stderr)
                    return False
            elif job_man.state == State.canceled:
                self._print(ongoing_msg, env)
            else:
                self._print_tmp(ongoing_msg, env)
                self.job_managers.appendleft(job_man)
                break

        if len(self.pipeline):
            self._print_tmp(f"Active job: {self.pipeline[0].name}", env)
        return True

    def _print_tmp(self, msg, env: Env, *args, **kwargs):
        """Prints a text to be rewriten latter."""
        if not env.plain:
            self._tmp_lines += msg.count('\n') + 1
            print(str(msg), *args, **kwargs)

    def _print(self, msg, env: Env, *args, **kwargs):
        """Prints a text."""
        self._tmp_lines += 0
        print(str(msg), *args, **kwargs)
