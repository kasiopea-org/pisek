import glob
import random
import os
from typing import List, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.jobs.status import tab
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob, Compile

class GeneratorManager(TaskJobManager):
    def __init__(self):
        super().__init__("Running generator")

    def _get_jobs(self) -> List[Job]:
        generator = self._resolve_path(self._env.config.generator)

        jobs = [compile := Compile(generator, self._env.fork())]

        if self._env.config.contest_type == "kasiopea":
            random.seed(4)  # Reproducibility!
            seeds = random.sample(range(0, 16**4), self._env.get_without_log('inputs'))
            for sub_num in self._env.config.subtasks.keys():
                if sub_num == "0":
                    continue  # skip samples
                last_gen = None
                for i, seed in enumerate(seeds):
                    data_dir = self._env.config.get_data_dir()
                    input_name = util.get_input_name(seed, sub_num)

                    jobs.append(gen := OnlineGeneratorGenerate(generator, input_name, sub_num, seed, self._env.fork()))
                    gen.add_prerequisite(compile)
                    if i == 0:
                        jobs.append(det := OnlineGeneratorDeterministic(generator, input_name, sub_num, seed, self._env.fork()))
                        det.add_prerequisite(gen)
                    elif i == 1:
                        jobs.append(rs := OnlineGeneratorRespectsSeed(sub_num, last_gen.seed, gen.seed,
                                                                    last_gen.input_file, gen.input_file, self._env.fork()))
                        rs.add_prerequisite(last_gen)
                        rs.add_prerequisite(gen)
                    last_gen = gen
        else:
            jobs.append(OfflineGeneratorGenerate(generator, self._env.fork()))

        return jobs


class OnlineGeneratorJob(ProgramJob):
    """Abstract class for jobs with OnlineGenerator."""
    def __init__(self, name: str, generator : str, input_file: str, subtask: int, seed: int, env: Env) -> None:
        self.subtask = subtask
        self.seed = seed
        super().__init__(name, generator, env)
        self.input_name = input_file
        self.input_file = self._data(input_file)

    def _gen(self, input_file: str, seed: int, subtask: int) -> Optional[RunResult]:
        if not self._load_compiled():
            return None
        if seed < 0:
            return self._fail(f"Seed {seed} is negative.")

        input_dir = os.path.dirname(input_file)
        os.makedirs(input_dir, exist_ok=True)

        difficulty = str(subtask)
        hexa_seed = f"{seed:x}"

        result = self._run_program(
            [difficulty, hexa_seed],
            stdout=input_file,
        )
        if result is None:
            return
        if result.kind != RunResultKind.OK:
            return self._program_fail(f"{self.program} failed on subtask {subtask}, seed {seed:x}:", result)
        
        return result


class OnlineGeneratorGenerate(OnlineGeneratorJob):
    """Generates single input using OnlineGenerator."""
    def __init__(self, generator: str, input_file: str, subtask: int, seed: int, env: Env) -> None:
        super().__init__(f"Generate {input_file}", generator, input_file, subtask, seed, env)

    def _run(self) -> Optional[RunResult]:
        return self._gen(self.input_file, self.seed, self.subtask)
        

class OnlineGeneratorDeterministic(OnlineGeneratorJob):
    """Test whether generating given input again has same result."""
    def __init__(self, generator: str, input_file: str, subtask: int, seed: int, env: Env) -> None:
        super().__init__(
            f"Generator is deterministic (subtask {subtask}, seed {seed:x})",
            generator, input_file, subtask, seed, env
        )

    def _run(self) -> None:
        copy_file = self.input_file.replace(".in", ".copy")
        if not self._gen(copy_file, self.seed, self.subtask):
            return
        if not self._files_equal(self.input_file, copy_file):
            return self._fail(
                f"Generator is not deterministic. Files {self.input_name} and {os.path.basename(copy_file)} differ "
                f"(subtask {self.subtask}, seed {self.seed})",
            )

class OnlineGeneratorRespectsSeed(TaskJob):
    """Test whether two files generated with different seed are different."""
    def __init__(self, subtask: int, seed1: int, seed2: int, file1: str, file2: str, env: Env) -> None:
        self.file1, self.file2 = file1, file2
        self.file1_name, self.file2_name = map(os.path.basename, (file1, file2))
        self.subtask = subtask
        self.seed1, self.seed2 = seed1, seed2
        super().__init__(f"Generator respects seeds ({self.file1_name} and {self.file2_name} are different)", env)

    def _run(self) -> None:
        if self._files_equal(self.file1, self.file2):
            return self._fail(
                f"Generator doesn't respect seed."
                f"Files {self.file1_name} (seed {self.seed1:x}) and {self.file2_name} (seed {self.seed2:x}) are same."
            )

class OfflineGeneratorGenerate(ProgramJob):
    """Job that generates all inputs using OfflineGenerator."""
    def __init__(self, program: str, env: Env) -> None:
        super().__init__("Generate inputs", program, env)

    def _gen(self) -> Optional[RunResult]:
        """Generates all inputs."""
        if not self._load_compiled():
            return None

        # Clear old inputs
        samples = self._subtask_inputs(self._env.config.subtasks['0'])
        for inp in self._all_inputs():
            if inp not in samples:
                os.remove(self._data(inp))

        data_dir = self._env.config.get_data_dir()
        result = self._run_program([data_dir])

        if result is None:
            return
        if result.kind != RunResultKind.OK:
            return self._program_fail(f"Generator failed:", result)

        for sub_num, subtask in self._env.config.subtasks.items():
            if sub_num == "0":
                continue
            files = self._subtask_inputs(subtask)
            if len(files) == 0:
                return self._fail(f"Generator did not generate any inputs for subtask {sub_num}.")
            for file in files:
                self._access_file(self._data(file))

        test_files = glob.glob(os.path.join(data_dir, "*.in"))
        if len(test_files) == 0:
            return self._fail(f"Generator did not generate ant inputs.")

        return result

    def _run(self) -> Optional[RunResult]:
        return self._gen()
