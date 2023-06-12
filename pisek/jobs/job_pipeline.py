from abc import ABC, abstractmethod
from collections import deque

from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.cache import Cache

class JobPipeline(ABC):
    @abstractmethod
    def __init__(self, env):
        env.reserve()

    def run_jobs(self, cache: Cache, env: Env):
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
            self.status_update()

        cache.export()  # Remove duplicate entries

    def status_update(self) -> None:
        while len(self.job_managers):
            job_man = self.job_managers.popleft()
            print(job_man.update(), end='\r')
            if job_man.ready():
                msg = job_man.finish()
                if msg: print(msg)
            elif job_man.state == State.failed:
                msg = job_man.finish()
                if msg: print(msg)
                print(job_man.failures(), end='')
            elif job_man.state == State.canceled:
                print()
            else:
                self.job_managers.appendleft(job_man)
                break
