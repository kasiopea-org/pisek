import os
import re
from typing import List
import random

from pisek.program import Program
from pisek.generator import OnlineGenerator
from pisek.checker import Checker

from pisek.tests.jobs import State, Job, JobManager
from pisek.env import Env
import pisek.util as util

# ------------- Sample jobs ---------------
class SampleManager(JobManager):
    def __init__(self):
        super().__init__("Sample Manager")

    def _get_jobs(self, env: Env) -> List[Job]:
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

# ------------------ Generic jobs -------------------
class Compile(Job):
    def __init__(self, program: Program, env) -> None:
        self.program = program
        super().__init__(        
            name=f"Compile {program.name}",
            env=env
        )
    
    def _run(self):
        self.program.compile()


# ------------- Online generator jobs ---------------
class OnlineGeneratorManager(JobManager):
    def __init__(self):
        super().__init__("Generator Manager")

    def _get_jobs(self, env: Env) -> List[Job]:
        generator = OnlineGenerator(env)
        
        jobs = [compile := Compile(generator, env)]
        
        random.seed(4)  # Reproducibility!
        seeds = random.sample(range(0, 16**4), env.inputs)
        for subtask in env.config.subtasks:
            last_gen = None
            for i, seed in enumerate(seeds):
                data_dir = env.config.get_data_dir()
                input_name = os.path.join(data_dir, util.get_input_name(seed, subtask))

                jobs.append(gen := OnlineGeneratorGenerate(generator, input_name, subtask, seed, env))
                gen.add_prerequisite(compile)
                if i == 0:
                    jobs.append(det := OnlineGeneratorDeterministic(generator, input_name, subtask, seed, env))
                    det.add_prerequisite(gen)
                elif i == 1:
                    jobs.append(rs := OnlineGeneratorRespectsSeed(subtask, last_gen.seed, gen.seed,
                                                                  last_gen.input_file, gen.input_file, env))
                    rs.add_prerequisite(last_gen)
                    rs.add_prerequisite(gen)
                last_gen = gen

        return jobs

    def _get_status(self) -> str:
        return ""

class GeneratorJob(Job):
    def __init__(self, name: str, generator : OnlineGenerator, input_file: str, subtask: int, seed: int, env: Env) -> None:
        self.generator = generator
        self.subtask = subtask
        self.seed = seed
        self.input_file = input_file
        super().__init__(name, env)

    def _gen(self, input_file: str, seed: int, subtask: int) -> None:
        if not self.generator.generate(input_file, seed, subtask):
            return self.fail(
                f"Error when generating input {input_file} of subtask {self.subtask}"
                f" with seed {self.seed}"
            )

class OnlineGeneratorGenerate(GeneratorJob):
    def __init__(self, generator: OnlineGenerator, input_file: str, subtask: int, seed: int, env: Env) -> None:
        super().__init__(f"Generate {input_file}", generator, input_file, subtask, seed, env)

    def _run(self):
        self._gen(self.input_file, self.seed, self.subtask)


class OnlineGeneratorDeterministic(GeneratorJob):
    def __init__(self, generator: OnlineGenerator, input_file: str, subtask: int, seed: int, env: Env) -> None:
        super().__init__(
            f"Generator is deterministic (subtask {subtask}, seed {seed})",
            generator, input_file, subtask, seed, env
        )

    def _run(self):
        copy_file = os.path.join(self._env.config.get_data_dir(), util.get_output_name(self.input_file, "copy"))
        self._gen(copy_file, self.seed, self.subtask)
        if not util.files_are_equal(self.input_file, copy_file):
            return self.fail(
                f"Generator is not deterministic. Files {self.input_file} and {copy_file} differ "
                f"(subtask {self.subtask}, seed {self.seed})",
            )

class OnlineGeneratorRespectsSeed(Job):
    def __init__(self, subtask: int, seed1: int, seed2: int, file1: str, file2: str, env: Env) -> None:
        self.file1, self.file2 = file1, file2
        self.subtask = subtask
        self.seed1, self.seed2 = seed1, seed2
        super().__init__(f"Generator respects seeds ({file1} and {file2} are different)", env)

    def _run(self):
        if util.files_are_equal(self.file1, self.file2):
            return self.fail(
                f"Generator doesn't respect seed."
                f"Files {self.file1} (seed {self.seed1}) and {self.file2} (seed {self.seed2}) are same."
            )

# ------------ Checker jobs ---------------
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
        
        for subtask in env.config.subtasks:
            for seed in seeds:
                jobs.append(gen := OnlineGeneratorGenerate(checker, subtask, seed, env))
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
