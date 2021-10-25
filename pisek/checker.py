import os
import subprocess

from . import program
from .task_config import TaskConfig


class Checker(program.Program):
    def __init__(self, task_config: TaskConfig):
        assert task_config.checker
        super().__init__(task_config.task_dir, task_config.checker)
        self.task_config = task_config

    def run_on_file(
        self, input_file: str, subtask_num: int
    ) -> subprocess.CompletedProcess:
        """
        Runs the checker on the given file, assuming it is from a specific subtask.
        """

        with open(os.path.join(self.task_config.get_data_dir(), input_file)) as f:
            res = self.run_raw(
                [str(subtask_num)],
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        return res
