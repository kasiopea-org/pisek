import os
from typing import List

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager

class SampleManager(TaskJobManager):
    def __init__(self):
        super().__init__("Sample Manager")

    def _get_jobs(self) -> List[Job]:
        samples = self._get_samples()
        unziped_samples = sum(map(list, samples), start=[])
        if len(samples) <= 0:
            self.fail(
                f"In subfolder {self._env.config.samples_subdir} of task folder are no samples "
                "(files sample*.in with according sample*.out)",
            )
            return []

        jobs = []
        for fname in unziped_samples:
            jobs += [
                existence := SampleExists(fname, self._env.fork()),
                non_empty := SampleNotEmpty(fname, self._env.fork()),
                copy := CopySample(fname, self._env.fork())
            ]
            non_empty.add_prerequisite(existence)
            copy.add_prerequisite(existence)

        return jobs


class SampleJob(TaskJob):
    def __init__(self, name, sample: str, env: Env) -> None:
        super().__init__(name, env)
        self.sample = self._resolve_path(env.config.samples_subdir, sample)

class SampleExists(SampleJob):
    def __init__(self, sample: str, env: Env) -> None:
        super().__init__(f"Sample {sample} exists", sample, env)

    def _run(self):
        if not self._file_exists(self.sample):
            return self.fail(f"Sample does not exists or is not file: {self.sample}")

class SampleNotEmpty(SampleJob):
    def __init__(self, sample: str, env: Env) -> None:
        super().__init__(f"Sample {sample} is not empty", sample, env)

    def _run(self):
        if not self._file_not_empty(self.sample):
            return self.fail(f"Sample is empty: {self.sample}")

class CopySample(SampleJob):
    """Copies samples into data so we can treat them as inputs."""
    def __init__(self, sample: str, env: Env) -> None:
        data_subdir = env.config.data_subdir.rstrip("/") + "/"
        super().__init__(f"Copy {sample} to {data_subdir}", sample, env)
    
    def _run(self):
        self._copy_file(self.sample, self._data(os.path.basename(self.sample)))
