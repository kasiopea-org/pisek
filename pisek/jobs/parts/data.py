from pisek.env import Env

from pisek.jobs.jobs import Job
from pisek.jobs.parts.task_job import TaskJobManager, TaskJob

MB = 1024*1024

class DataManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking data")

    def _get_jobs(self) -> list[Job]:
        jobs : list[Job] = []

        files = self._globs_to_files(["*"])
        for file in files:
            if file.endswith(".in"):
                jobs.append(InputSmall(self._env).init(file))
            if file.endswith(".out"):
                jobs.append(OutputSmall(self._env).init(file))

        return jobs


class CheckData(TaskJob):
    """Abstract class for checking input and output files."""
    def _init(self, name: str, data_file: str) -> None:
        self.data = self._data(data_file)
        super()._init(name)

class InputSmall(CheckData):
    """Checks that input is small enough to download."""
    def _init(self, input_file: str) -> None:
        super()._init(f"Input {input_file} is smaller than {self._env.config.input_max_size}MB", input_file)

    def _run(self):
        if self._file_size(self.data) > self._env.config.input_max_size*MB:
            self._fail("Input too big.")

class OutputSmall(CheckData):
    """Checks that output is small enough to upload."""
    def _init(self, output_file: str) -> None:
        super()._init(f"Output {output_file} is smaller than {self._env.config.output_max_size}MB", output_file)

    def _run(self):
        if self._file_size(self.data) > self._env.config.output_max_size*MB:
            self._fail("Output too big.")
