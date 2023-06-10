from typing import List

from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import ProgramJob, Compile

from pisek.generator import OnlineGenerator

DIFF_NAME = "diff.sh"

class JudgeManager(TaskJobManager):
    def __init__(self):
        super().__init__("Judge Manager")

    def _get_jobs(self) -> List[Job]:
        jobs = []
        if self._env.config.judge_type == "diff":
            jobs = [
                build := BuildDiffJudge(self._env.fork()),
                comp := Compile(self._executable(DIFF_NAME), self._env.fork()) 
            ]
            comp.add_prerequisite(build)
        else:
            jobs = [
                Compile(self._resolve_path(self._env.config.judge), self._env.fork()) 
            ]

        return jobs

class BuildDiffJudge(TaskJob):
    def __init__(self, env: Env) -> None:
        super().__init__("Build WhiteDiffJudge", env)

    def _run(self):
        with self._open_file(self._executable(DIFF_NAME), "w") as f:
            f.write(
                "#!/bin/bash\n"
                "if [ $(diff -Bbq $TEST_OUTPUT -) ]; then\n"
                "   exit 1\n"
                "fi\n"
            )
        
