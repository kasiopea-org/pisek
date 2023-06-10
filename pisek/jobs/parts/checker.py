import termcolor
from typing import List

from pisek.env import Env
from pisek.jobs.cache import CacheResultEnum
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import ProgramJob, Compile


CheckerResult = CacheResultEnum('ok', 'failed')
class CheckerManager(TaskJobManager):
    def __init__(self):
        self.skipped_checker = ""
        super().__init__("Checker Manager")

    def _get_jobs(self) -> List[Job]:
        if self._env.config.checker is None:
            if self._env.strict:
                return self.fail("No checker specified in config.")
            self.skipped_checker = termcolor.colored(
                "Warning: No checker specified in config.\n"
                "It is recommended to set `checker` is section [tests]",
            color="yellow")
        if self._env.no_checker:
            self.skipped_checker = termcolor.colored("Skipping checking", color="yellow")

        if self.skipped_checker != "":
            return []

        checker = self._resolve_path(self._env.config.checker)

        jobs = [compile := Compile(checker, self._env.fork())]
        
        for sub_num, sub in self._env.config.subtasks.items():
            for inp in self._subtask_inputs(sub):
                jobs.append(check := CheckerJob(checker, inp, sub_num, self._env.fork()))
                check.add_prerequisite(compile)

        return jobs
    
    def _get_status(self) -> str:
        if self.skipped_checker:
            return self.skipped_checker
        else:
            return super()._get_status()


class CheckerJob(ProgramJob):
    def __init__(self, checker: str, input_name: str, subtask: int, env):
        self.subtask = subtask
        super().__init__(
            name=f"Check {input_name} on subtask {subtask}",
            program=checker,
            env=env
        )
        self.input_name = self._data(input_name)

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

# TODO: Checker distinguishes subtasks