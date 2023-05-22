from pisek.tests.jobs import State, Job, JobManager

def get_inputs():
    return []

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
