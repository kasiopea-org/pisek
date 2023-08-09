import os

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager

class SampleManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking samples")

    def _get_jobs(self) -> list[Job]:
        samples = self._get_samples()
        unzipped_samples : list[str] = sum(map(list[str], samples), start=[])
        if len(samples) <= 0:
            self._fail(
                f"In subfolder {self._env.config.samples_subdir} of task folder are no samples "
                "(files sample*.in with according sample*.out)",
            )
            return []

        jobs : list[Job] = []
        for fname in unzipped_samples:
            jobs += [
                existence := SampleExists(self._env).init(fname),
                non_empty := SampleNotEmpty(self._env).init(fname),
                copy := CopySample(self._env).init(fname),
            ]
            non_empty.add_prerequisite(existence)
            copy.add_prerequisite(existence)

        return jobs


class SampleJob(TaskJob):
    def _init(self, name: str, sample : str) -> None:
        self.sample = self._sample(sample)
        super()._init(name)

class SampleExists(SampleJob):
    def _init(self, sample: str) -> None:
        super()._init(f"Sample {sample} exists", sample)

    def _run(self):
        if not self._file_exists(self.sample):
            return self._fail(f"Sample does not exists or is not file: {self.sample}")

class SampleNotEmpty(SampleJob):
    def _init(self, sample: str) -> None:
        super()._init(f"Sample {sample} is not empty", sample)

    def _run(self):
        if not self._file_not_empty(self.sample):
            return self._fail(f"Sample is empty: {self.sample}")

class CopySample(SampleJob):
    """Copies samples into data so we can treat them as inputs."""
    def _init(self, sample: str) -> None:
        data_subdir = self._env.config.data_subdir.rstrip("/") + "/"
        super()._init(f"Copy {sample} to {data_subdir}", sample)


    def _run(self):
        self._copy_file(self.sample, self._data(os.path.basename(self.sample)))
