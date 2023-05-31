from typing import List

from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob
from pisek.tests.parts.general import Compile

from pisek.checker import Checker

class CheckerManager(JobManager):
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
            self.config.no_checker = "Skipping checking"
        
        if self.skipped_checker != "":
            return []

        checker = Checker(env)
        
        jobs = [compile := Compile(checker, env)]
        
        for input_file in env.config:
                jobs.append(gen := (checker, env))
                gen.add_prerequisite(compile)                
        return jobs
    
    def _get_status(self) -> str:
        if self.skipped_checker:
            return self.skipped_checker
        else:
            return ""

    def _get_jobs(self, env: Env) -> list[Job]:
        checker = Checker(env)
        compile = Compile(checker_fname)
        testcases = []
        for input in env.get_inputs():
            testcases.append(CheckerTestCase(checker_fname, input, env))


class CheckerTestCase(TaskJob):
    def __init__(self, checker_fname: str, input_fname: str, env):
        super().__init__(
            name=f"Check {input_fname}",
            required_files=[checker_fname, input_fname],
            env=env
        )

    def _run(self):
        pass
