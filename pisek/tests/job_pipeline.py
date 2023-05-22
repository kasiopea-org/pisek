from abc import ABC, abstractmethod
from collections import deque

from pisek.tests.jobs import State, Job, JobManager

class JobPipeline(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def run_jobs(self, cache):
        self.job_managers = deque()
        self.pipeline = deque(self.pipeline)
        while len(self.pipeline) or len(self.job_managers):
            p_item = self.pipeline.popleft()
            if isinstance(p_item, JobManager):
                self.job_managers.append(p_item)
                self.pipeline.extend(p_item.create_jobs())
            elif isinstance(p_item, Job):
                p_item.run_job(cache)
                p_item.finish()
            else:
                raise TypeError(f"Objects in {self.__class__.__name__} should be either Job or JobManager.")

            while len(self.job_managers) and self.job_managers[0].state == State.finished:
                job_man = self.job_managers.popleft() 
                print(job_man.finish())
            if len(self.job_managers):
                print(self.job_managers[0].update(), end='\r')
