import os

from pisek.tests.jobs import State, Job, JobManager
from pisek.env import Env
import pisek.util as util

class SampleManager(JobManager):
    def __init__(self):
        super().__init__("Sample Manager")

    def _get_jobs(self, env) -> list[Job]:
        samples = util.get_samples(env.config.get_samples_dir())
        if len(samples) <= 0:
            return self.fail(
                f"In subfolder {self._env.task_config.samples_subdir} of task folder are no samples "
                "(files sample*.in with according sample*.out)",
            )

        jobs = []
        for fname in sum(map(list, samples), start=[]):
            existence = SampleExists(fname, env.fork())
            non_empty = SampleNotEmpty(fname, env.fork())
            non_empty.add_prerequisite(existence)
            jobs += [existence, non_empty]

        return jobs

    def _get_status(self) -> str:
        if self.state == State.succeeded:
            return "Samples checked"
        else:
            current = sum(map(lambda x: x.state == State.succeeded, self.jobs))
            return f"Checking samples ({current}/{len(self.jobs)})"


class SampleExists(Job):
    def __init__(self, filename: str, env: Env) -> None:
        self.filename = filename
        super().__init__(f"Sample {self.filename} exists", env)
    
    def _run(self):
        if not util.file_exists(self.filename):
            return self.fail(f"Sample does not exists or is not file: {self.filename}")
        self._access_file(self.filename)
        return "OK"

class SampleNotEmpty(Job):
    def __init__(self, filename: str, env: Env) -> None:
        self.filename = filename
        super().__init__(f"Sample {self.filename} is not empty", env)
    
    def _run(self):
        if not util.file_not_empty(self.filename):
            return self.fail(f"Sample is empty: {self.filename}")
        self._access_file(self.filename)
        return "OK"


class Compile(Job):
    def __init__(self, program_name: str, env) -> None:
        super().__init__(
            name=f"Compile {program_name}",
            required_files=[program_name],
            env=env
        )

class CheckerManager(JobManager):
    def _get_jobs(self, env) -> list[Job]:
        checker_fname = env.get("checker")
        compile = Compile(checker_fname)
        testcases = []
        for input in env.get_inputs():
            testcases.append(CheckerTestCase(checker_fname, input, env))


class CheckerTestCase(Job):
    def __init__(self, checker_fname: str, input_fname: str, env):
        super().__init__(
            name=f"Check {input_fname}",
            required_files=[checker_fname, input_fname],
            env=env
        )

    def _run(self):
        pass

class SolutionManager(JobManager):
    def __init__(self):
        pass

class SolutionTestCase(Job):
    def __init__(self, solution_fname: str, input_fname: str, env):
        # TODO: Add context manager to required files
        super().__init__(
            name=f"Test {solution_fname} on {input_fname}",
            required_files=[solution_fname, input_fname],
            env=env
        )

    def _run(self):
        pass
