from enum import Enum
from typing import List

from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob, TaskJobManager
from pisek.tests.parts.program import ProgramJob, Compile

from pisek.checker import Checker

CheckerResult = Enum('CheckerResult', ['ok', 'failed'])
class CheckerManager(TaskJobManager):
    def __init__(self):
        self.skipped_checker = ""
        super().__init__("Checker Manager")

    def _get_jobs(self, env: Env) -> List[Job]:
        if env.config.checker is None:
            if env.strict:
                return self.fail("No checker specified in config.")
            self.skipped_checker = \
                "Warning: No checker specified in config. " \
                "It is recommended setting `checker` is section [tests]"
        if env.config.no_checker:
            self.skipped_checker = "Skipping checking"
        
        if self.skipped_checker != "":
            return []

        checker = self._resolve_file(env.config.checker)

        jobs = [compile := Compile(checker, env)]
        
        for subtask in env.config.get_subtasks():
                jobs.append(gen := (checker, env))
                gen.add_prerequisite(compile)                
        return jobs
    
    def _get_status(self) -> str:
        if self.skipped_checker:
            return self.skipped_checker
        else:
            return ""


class CheckerJob(ProgramJob):
    def __init__(self, checker: str, input_name: str, subtask: int, env):
        self.input_name = input_name
        self.subtask = subtask
        super().__init__(
            name=f"Check {input_name}",
            program=checker,
            env=env
        )

    def _check(self) -> bool:
        return self._run_program(
            [str(self.subtask)],
            stdin=self.input_name
        ).returncode == 0

    def _run(self) -> CheckerResult:
        if self._check():
            return CheckerResult.ok
        else:
            return CheckerResult.failed
