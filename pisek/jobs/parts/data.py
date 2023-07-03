from pisek.env import Env

from pisek.jobs.jobs import Job
from pisek.jobs.parts.task_job import TaskJobManager, TaskJob

MB = 1024*1024

class DataManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking data")

    def _get_jobs(self) -> list[Job]:
        jobs : list[Job] = []

        files = self._globs_to_files([self._data("*")])
        for file in files:
            if file.endswith(".in"):
                jobs.append(InputSmall(file, self._env.fork()))
            if file.endswith(".out"):
                jobs.append(OutputSmall(file, self._env.fork()))

        return jobs


class CheckData(TaskJob):
    """Abstract class for checking input and output files."""
    def __init__(self, name: str, data_file: str, env: Env) -> None:
        super().__init__(name, env)
        self.data = self._data(data_file)
    
class InputSmall(CheckData):
    """Checks that input is small enough to download."""
    def __init__(self, input_file: str, env: Env) -> None:
        super().__init__(
            f"Input {input_file} is smaller than {env.config.input_max_size}MB",
            input_file,
            env
        )

    def _run(self):
        if self._file_size(self.data) > self._env.config.input_max_size*MB:
            self._fail("Input too big.")

class OutputSmall(CheckData):
    """Checks that output is small enough to upload."""
    def __init__(self, output_file: str, env: Env) -> None:
        super().__init__(
            f"Output {output_file} is smaller than {env.config.output_max_size}MB",
            output_file,
            env
        )

    def _run(self):
        if self._file_size(self.data) > self._env.config.output_max_size*MB:
            self._fail("Output too big.")
