from typing import List

import pisek.util as util
from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob, TaskJobManager

class SampleManager(TaskJobManager):
    def __init__(self):
        super().__init__("Sample Manager")

    def _get_jobs(self, env: Env) -> List[Job]:
        samples = util.get_samples(env.config.get_samples_dir())
        if len(samples) <= 0:
            return self.fail(
                f"In subfolder {self._env.task_config.samples_subdir} of task folder are no samples "
                "(files sample*.in with according sample*.out)",
            )

        jobs = []
        for fname in sum(map(list, samples), start=[]):
            existence = SampleExists(fname, env)
            non_empty = SampleNotEmpty(fname, env)
            non_empty.add_prerequisite(existence)
            jobs += [existence, non_empty]

        return jobs

    def _get_status(self) -> str:
        if self.state == State.succeeded:
            return "Samples checked"
        else:
            current = sum(map(lambda x: x.state == State.succeeded, self.jobs))
            return f"Checking samples ({current}/{len(self.jobs)})"

class SampleExists(TaskJob):
    def __init__(self, filename: str, env: Env) -> None:
        self.filename = filename
        super().__init__(f"Sample {self.filename} exists", env)
    
    def _run(self):
        if not self._file_exists(self.filename):
            return self.fail(f"Sample does not exists or is not file: {self.filename}")

class SampleNotEmpty(TaskJob):
    def __init__(self, filename: str, env: Env) -> None:
        self.filename = filename
        super().__init__(f"Sample {self.filename} is not empty", env)
    
    def _run(self):
        if not self._file_not_empty(self.filename):
            return self.fail(f"Sample is empty: {self.filename}")
