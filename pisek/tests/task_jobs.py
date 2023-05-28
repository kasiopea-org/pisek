import os

from pisek.tests.jobs import State, Job, JobManager
import pisek.util as util

class SampleManager(JobManager):
    def __init__(self):
        super().__init__("Sample Manager")

    def _get_jobs(self, env) -> list[Job]:
        existence = SampleExists(env.fork())
        non_empty = SampleNotEmpty(env.fork())

        non_empty.add_prerequisite(existence)

        return [existence, non_empty]

    def _get_status(self) -> str:
        if self.state == State.succeeded:
            return "Samples checked"
        else:
            return "Checking samples"

class SampleJob(Job):
    def __init__(self, env) -> None:
        self.samples = util.get_samples(env.config.get_samples_dir())
        super().__init__("Samples exist", env)

class SampleExists(SampleJob):
    def _run(self):
        if len(self.samples) <= 0:
            return self.fail(
                f"V podsložce {self._env.task_config.samples_subdir} složky s úlohou nejsou žádné samply "
                "(soubory tvaru sample*.in s odpovídajícím sample*.out)",
            )

        for sample_in, sample_out in self.samples:
            if not util.file_exists(sample_in):
                return self.fail(f"Vzorový vstup neexistuje nebo není soubor: {sample_in}")
            self._access_file(sample_in)

            if not util.file_exists(sample_out):
                return self.fail(f"Vzorový výstup neexistuje nebo není soubor: {sample_out}")
            self._access_file(sample_out)

class SampleNotEmpty(SampleJob):
    def _run(self):
        for sample_in, sample_out in self.samples:
            if not util.file_not_empty(sample_in):
                return self.fail(f"Vzorový vstup je prázdný: {sample_in}")
            self._access_file(sample_in)
            
            if not util.file_not_empty(sample_out):
                return self.fail(f"Vzorový vstup je prázdný: {sample_out}")
            self._access_file(sample_out)


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
