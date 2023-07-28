import os
from importlib.resources import files

import subprocess
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager

class ToolsManager(TaskJobManager):
    def __init__(self):
        super().__init__("Preparing tools")

    def _get_jobs(self) -> list[Job]:
        jobs = [PrepareMinibox(self._env).init()]
        return jobs


class PrepareMinibox(TaskJob):
    """Copies samples into data so we can treat them as inputs."""
    def _init(self) -> None:
        super()._init("Prepare Minibox")

    def _run(self):
        source = files('pisek').joinpath('tools/minibox.c')
        executable = self._executable('minibox')
        self._access_file(executable)
        os.makedirs(self._executable("."), exist_ok=True)
        gcc = subprocess.run([
            "gcc", source, "-o", executable,
            "-std=gnu11", "-D_GNU_SOURCE", "-O2", "-Wall", "-Wextra", "-Wno-parentheses", "-Wno-sign-compare"
        ])
        if gcc.returncode != 0:
            self._fail("Minibox compilation failed.")
