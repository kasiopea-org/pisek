# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import glob
import random
import os
from typing import Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob
from pisek.jobs.parts.compile import Compile


class GeneratorManager(TaskJobManager):
    def __init__(self):
        self._inputs = []
        super().__init__("Running generator")

    def _get_jobs(self) -> list[Job]:
        generator = self._resolve_path(self._env.config.generator)

        jobs: list[Job] = [compile := Compile(self._env, generator)]

        if self._env.config.contest_type == "kasiopea":
            random.seed(4)  # Reproducibility!
            seeds = random.sample(range(0, 16**4), self._env.inputs)
            for sub_num in self._env.config.subtasks.keys():
                if sub_num == "0":
                    continue  # skip samples
                last_gen: OnlineGeneratorGenerate
                for i, seed in enumerate(seeds):
                    data_dir = self._env.config.get_data_dir()
                    self._inputs.append(
                        input_name := util.get_input_name(seed, sub_num)
                    )

                    jobs.append(
                        gen := OnlineGeneratorGenerate(
                            self._env, generator, input_name, sub_num, seed
                        )
                    )
                    gen.add_prerequisite(compile)
                    if i == 0:
                        jobs.append(
                            det := OnlineGeneratorDeterministic(
                                self._env, generator, input_name, sub_num, seed
                            )
                        )
                        det.add_prerequisite(gen)
                    elif i == 1:
                        jobs.append(
                            rs := OnlineGeneratorRespectsSeed(
                                self._env,
                                sub_num,
                                last_gen.seed,
                                gen.seed,
                                last_gen.input_file,
                                gen.input_file,
                            )
                        )
                        rs.add_prerequisite(last_gen)
                        rs.add_prerequisite(gen)
                    last_gen = gen
        else:
            jobs.append(gen2 := OfflineGeneratorGenerate(self._env, generator))
            gen2.add_prerequisite(compile)

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        if self._env.config.contest_type == "kasiopea":
            return {"inputs": self._inputs}
        else:
            return {"inputs": self.jobs[1].result}


class RunOnlineGeneratorMan(TaskJobManager):
    def __init__(self, subtask: int, seed: int, file: str):
        self._subtask = subtask
        self._seed = seed
        self._file = file
        super().__init__("Running generator")

    def _get_jobs(self) -> list[Job]:
        generator = self._resolve_path(self._env.config.generator)

        jobs: list[Job] = [
            compile := Compile(self._env, generator),
            gen := OnlineGeneratorGenerate(
                self._env, generator, self._file, self._subtask, self._seed
            ),
        ]
        gen.add_prerequisite(compile)

        return jobs


class OnlineGeneratorJob(ProgramJob):
    """Abstract class for jobs with OnlineGenerator."""

    def __init__(
        self,
        env: Env,
        name: str,
        generator: str,
        input_file: str,
        subtask: int,
        seed: int,
    ) -> None:
        super().__init__(env, name, generator)
        self.subtask = subtask
        self.seed = seed
        self.input_name = input_file
        self.input_file = self._data(input_file)

    def _gen(self, input_file: str, seed: int, subtask: int) -> RunResult:
        self._load_compiled()
        if seed < 0:
            raise PipelineItemFailure(f"Seed {seed} is negative.")

        input_dir = os.path.dirname(input_file)
        os.makedirs(input_dir, exist_ok=True)

        difficulty = str(subtask)
        hexa_seed = f"{seed:x}"

        result = self._run_program(
            [difficulty, hexa_seed], stdout=input_file, print_stderr=True
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.program} failed on subtask {subtask}, seed {seed:x}:", result
            )

        return result


class OnlineGeneratorGenerate(OnlineGeneratorJob):
    """Generates single input using OnlineGenerator."""

    def __init__(
        self, env: Env, generator: str, input_file: str, subtask: int, seed: int
    ) -> None:
        super().__init__(
            env, f"Generate {input_file}", generator, input_file, subtask, seed
        )

    def _run(self) -> RunResult:
        return self._gen(self.input_file, self.seed, self.subtask)


class OnlineGeneratorDeterministic(OnlineGeneratorJob):
    """Test whether generating given input again has same result."""

    def __init__(
        self, env: Env, generator: str, input_file: str, subtask: int, seed: int
    ) -> None:
        super().__init__(
            env,
            f"Generator is deterministic (subtask {subtask}, seed {seed:x})",
            generator,
            input_file,
            subtask,
            seed,
        )

    def _run(self) -> None:
        copy_file = self.input_file.replace(".in", ".copy")
        self._gen(copy_file, self.seed, self.subtask)
        if not self._files_equal(self.input_file, copy_file):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {self.input_name} and {os.path.basename(copy_file)} differ "
                f"(subtask {self.subtask}, seed {self.seed})",
            )


class OnlineGeneratorRespectsSeed(TaskJob):
    """Test whether two files generated with different seed are different."""

    def __init__(
        self, env: Env, subtask: int, seed1: int, seed2: int, file1: str, file2: str
    ) -> None:
        self.file1, self.file2 = file1, file2
        self.file1_name, self.file2_name = map(
            lambda s: str(os.path.basename(s)), (file1, file2)
        )
        self.subtask = subtask
        self.seed1, self.seed2 = seed1, seed2
        super().__init__(
            env,
            f"Generator respects seeds ({self.file1_name} and {self.file2_name} are different)",
        )

    def _run(self) -> None:
        if self._files_equal(self.file1, self.file2):
            raise PipelineItemFailure(
                f"Generator doesn't respect seed."
                f"Files {self.file1_name} (seed {self.seed1:x}) and {self.file2_name} (seed {self.seed2:x}) are same."
            )


class OfflineGeneratorGenerate(ProgramJob):
    """Job that generates all inputs using OfflineGenerator."""

    def __init__(self, env: Env, program: str) -> None:
        super().__init__(env, "Generate inputs", program)

    def _subtask_inputs(self, subtask: str):
        return self.globs_to_files(
            self._env.config.subtasks[subtask].in_globs, self._data(".")
        )

    def _gen(self) -> list[str]:
        """Generates all inputs."""
        self._load_compiled()

        # Clear old inputs
        ins = self.globs_to_files(["*.in"], self._data("."))
        samples = self._subtask_inputs("0")
        for inp in set(ins) - set(samples):
            os.remove(self._data(inp))

        data_dir = self._data(".")
        run_result = self._run_program([data_dir], print_stderr=True)

        if run_result is None:
            return None
        if run_result.kind != RunResultKind.OK:
            raise self._create_program_failure(f"Generator failed:", run_result)

        inputs = []
        for sub_num, subtask in self._env.config.subtasks.items():
            if sub_num == "0":
                continue
            files = self._subtask_inputs(sub_num)
            if len(files) == 0:
                raise PipelineItemFailure(
                    f"Generator did not generate any inputs for subtask {sub_num}."
                )
            for file in files:
                inputs.append(file)
                self._access_file(self._data(file))

        test_files = glob.glob(os.path.join(data_dir, "*.in"))
        if len(test_files) == 0:
            raise PipelineItemFailure(f"Generator did not generate ant inputs.")

        return inputs

    def _run(self) -> Optional[list[str]]:
        return self._gen()
