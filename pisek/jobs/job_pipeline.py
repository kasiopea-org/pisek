from abc import ABC, abstractmethod
from collections import deque
import sys

from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.cache import Cache

class JobPipeline(ABC):
    @abstractmethod
    def __init__(self, env):
        env.reserve()
        self.failed = False

    def run_jobs(self, cache: Cache, env: Env) -> bool:
        self.job_managers = deque()
        self.pipeline = deque(self.pipeline)
        while len(self.pipeline) or len(self.job_managers):
            p_item = self.pipeline.popleft()
            if isinstance(p_item, JobManager):
                self.job_managers.append(p_item)
                self.pipeline.extendleft(reversed(p_item.create_jobs(env.fork())))
            elif isinstance(p_item, Job):
                p_item.run_job(cache)
                p_item.finish()
            else:
                raise TypeError(f"Objects in {self.__class__.__name__} should be either Job or JobManager.")
            if not self.status_update() and not env.full:  # we really need to call status_update to update messages
                break

        cache.export()  # Remove duplicate cache entries
        return self.failed

    def status_update(self) -> bool:
        while len(self.job_managers):
            job_man = self.job_managers.popleft()
            print(job_man.update(), end='\r')
            if job_man.state == State.failed or job_man.ready():
                msg = job_man.finish()
                if msg:
                    print(msg)
                if job_man.state == State.failed:
                    print(job_man.failures(), end='', file=sys.stderr)
                    self.failed = True
                    return False
            elif job_man.state == State.canceled:
                print()
            else:
                self.job_managers.appendleft(job_man)
                break
        return True
