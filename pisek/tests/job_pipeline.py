from abc import ABC, abstractmethod
from collections import deque

from pisek.tests.jobs import State, Job, JobManager

class JobPipeline(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def run_jobs(self, cache):
        self.job_managers = deque()
        self.jobs = deque(self.jobs)
        while len(self.jobs) or len(self.job_managers):
            job = self.jobs.popleft()
            if isinstance(job, JobManager):
                self.job_managers.append(job)
                self.jobs.extend(job.create_jobs())
            elif isinstance(job, Job):
                job.run_job(cache)
            else:
                raise TypeError(f"Objects in {self.__class__.__name__} should be either Job or JobManager.")

            while len(self.job_managers) and self.job_managers[0].state == State.finished:
                job_man = self.job_managers.popleft() 
                print(job_man.update())
            if len(self.job_managers):
                print(self.job_managers[0].update(), end='\r')
