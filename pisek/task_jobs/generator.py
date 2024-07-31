# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import abstractmethod
from dataclasses import dataclass
import random
import os
import shutil
from typing import Any
import yaml

from pisek.env.env import Env
from pisek.utils.paths import TaskPath, GENERATED_SUBDIR
from pisek.config.config_types import GenType
from pisek.config.task_config import ProgramType
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.task_jobs.task_job import TaskJob, TaskJobManager
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.compile import Compile


@dataclass
class InputInfo:
    name: str
    repeat: int = 1
    is_generated: bool = True
    seeded: bool = True

    @staticmethod
    def generated(name: str, repeat: int = 1, seeded: bool = True) -> "InputInfo":
        return InputInfo(name, repeat, True, seeded)

    @staticmethod
    def static(name: str) -> "InputInfo":
        return InputInfo(name, 1, False, False)

    def task_path(self, env: Env, seed: int) -> TaskPath:
        filename = self.name
        if self.seeded:
            filename += f"_{seed:x}"
        filename += ".in"

        return TaskPath.input_path(env, filename)


def input_info_representer(dumper, input_info: InputInfo):
    return dumper.represent_sequence(
        "!InputInfo",
        [
            input_info.name,
            input_info.repeat,
            input_info.is_generated,
            input_info.seeded,
        ],
    )


def input_info_constructor(loader, value):
    [name, repeat, generated, seeded] = loader.construct_sequence(value)
    return InputInfo(name, repeat, generated, seeded)


yaml.add_representer(InputInfo, input_info_representer)
yaml.add_constructor("!InputInfo", input_info_constructor)


class GeneratorManager(TaskJobManager):
    """Manager that generates inputs and test generator."""

    def __init__(self):
        self._inputs = []
        super().__init__("Prepare generator")

    def _get_jobs(self) -> list[Job]:
        generator = self._env.config.in_gen

        jobs: list[Job] = [
            compile_gen := Compile(self._env, generator),
            list_inputs := list_inputs_job(self._env, generator),
        ]
        list_inputs.add_prerequisite(compile_gen)
        self._list_inputs = list_inputs

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        return {"inputs": self._list_inputs.result}


def gen():
    return None
    if self._env.config.contest_type == "kasiopea":
        random.seed(4)  # Reproducibility!
        seeds = random.sample(range(0, 16**4), self._env.inputs)
        for sub_num, _ in self._env.config.subtasks.items():
            if sub_num == 0:
                continue  # skip samples
            last_gen: OnlineGeneratorGenerate
            for i, seed in enumerate(seeds):
                self._inputs.append(
                    input_ := TaskPath.generated_input_file(
                        self._env, int(sub_num), seed
                    )
                )

                jobs.append(
                    gen := OnlineGeneratorGenerate(
                        self._env, generator, input_, sub_num, seed
                    )
                )
                gen.add_prerequisite(compile_gen)
                if i == 0:
                    jobs.append(
                        det := OnlineGeneratorDeterministic(
                            self._env, generator, input_, sub_num, seed
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
                            last_gen.input_,
                            gen.input_,
                        )
                    )
                    rs.add_prerequisite(last_gen)
                    rs.add_prerequisite(gen)
                last_gen = gen
    else:
        jobs.append(gen2 := CmsOldListInputs(self._env, generator))
        gen2.add_prerequisite(compile_gen)


class RunOnlineGeneratorMan(TaskJobManager):
    def __init__(self, subtask: int, seed: int, file: str):
        self._subtask = subtask
        self._seed = seed
        self._file = file
        super().__init__("Running generator")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = [
            compile_gen := Compile(self._env, self._env.config.in_gen),
            gen := OnlineGeneratorGenerate(
                self._env,
                self._env.config.in_gen,
                TaskPath(self._file),
                self._subtask,
                self._seed,
            ),
        ]
        gen.add_prerequisite(compile_gen)

        return jobs


class GeneratorListInputs(ProgramsJob):
    """Lists all inputs generator can generate."""

    def __init__(
        self, env: Env, generator: TaskPath, *, name: str = "", **kwargs
    ) -> None:
        self.generator = generator
        super().__init__(env, name or "List generator inputs", **kwargs)

    @abstractmethod
    def _run(self) -> list[InputInfo]:
        pass


def list_inputs_job(env: Env, generator: TaskPath) -> GeneratorListInputs:
    return {
        GenType.opendata_v1: OpendataV1ListInputs,
        GenType.cms_old: CmsOldListInputs,
    }[env.config.gen_type](env, generator)


class GenerateInput(ProgramsJob):
    """Generates input with given name."""

    def __init__(
        self, env: Env, input_name: str, seed: int, *, name: str = "", **kwargs
    ) -> None:
        if env.config.gen_type != GenType.cms_old:
            filename = f"{input_name}_{seed:x}.in"
        else:
            filename = f"{input_name}.in"

        self._input_name = input_name
        self._seed = seed
        self._input = TaskPath.input_path(env, filename)
        super().__init__(env, name or f"Generate {filename}", **kwargs)

    def _run(self) -> None:
        self._gen()

    @abstractmethod
    def _gen(self) -> None:
        pass


class OpendataV1ListInputs(GeneratorListInputs):
    """Lists all inputs for opendata-v1 gen - one for each subtask."""

    def _run(self) -> list[InputInfo]:
        return [
            InputInfo.generated(f"{subtask:02}")
            for subtask in self._env.config.subtasks
            if subtask != 0
        ]


class CmsOldListInputs(GeneratorListInputs):
    """Lists all inputs for cms-old generator - by running it."""

    def __init__(self, env: Env, generator: TaskPath, **kwargs) -> None:
        super().__init__(env, generator, name="Run generator", **kwargs)

    def _run(self) -> list[InputInfo]:
        """Generates all inputs."""
        gen_dir = TaskPath.generated_path(self._env, ".")
        try:
            shutil.rmtree(gen_dir.path)
        except FileNotFoundError:
            pass
        self.makedirs(gen_dir, exist_ok=False)

        run_result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=[gen_dir.path],
            stderr=TaskPath.log_file(self._env, None, self.generator.name),
        )
        self._access_file(gen_dir)

        if run_result.kind != RunResultKind.OK:
            raise self._create_program_failure("Generator failed:", run_result)

        inputs = []
        for inp in os.listdir(TaskPath.generated_path(self._env, ".").path):
            if inp.endswith(".in"):
                inputs.append(
                    InputInfo.generated(inp.removesuffix(".in"), seeded=False)
                )
        return inputs


class OnlineGeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    def __init__(
        self,
        env: Env,
        name: str,
        generator: TaskPath,
        input_: TaskPath,
        subtask: int,
        seed: int,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.generator = generator
        self.subtask = subtask
        self.seed = seed
        self.input_ = input_

    def _gen(self, input_file: TaskPath, seed: int, subtask: int) -> RunResult:
        if seed < 0:
            raise PipelineItemFailure(f"Seed {seed} is negative.")

        input_dir = os.path.dirname(input_file.path)

        difficulty = str(subtask)
        hexa_seed = f"{seed:x}"

        result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=[difficulty, hexa_seed],
            stdout=input_file,
            stderr=TaskPath.log_file(self._env, self.input_.name, self.generator.name),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on subtask {subtask}, seed {seed:x}:", result
            )

        return result


class OnlineGeneratorGenerate(OnlineGeneratorJob):
    """Generates single input using OnlineGenerator."""

    def __init__(
        self,
        env: Env,
        generator: TaskPath,
        input_: TaskPath,
        subtask: int,
        seed: int,
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=f"Generate {input_.name}",
            generator=generator,
            input_=input_,
            subtask=subtask,
            seed=seed,
            **kwargs,
        )

    def _run(self) -> RunResult:
        return self._gen(self.input_, self.seed, self.subtask)


class OnlineGeneratorDeterministic(OnlineGeneratorJob):
    """Test whether generating given input again has same result."""

    def __init__(
        self,
        env: Env,
        generator: TaskPath,
        input_: TaskPath,
        subtask: int,
        seed: int,
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=f"Generator is deterministic (name {subtask}, seed {seed:x})",
            generator=generator,
            input_=input_,
            subtask=subtask,
            seed=seed,
            **kwargs,
        )

    def _run(self) -> None:
        copy_file = self.input_.replace_suffix(".in2")
        self._gen(copy_file, self.seed, self.subtask)
        if not self._files_equal(self.input_, copy_file):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {self.input_:p} and {copy_file:p} differ "
                f"(subtask {self.subtask}, seed {self.seed})",
            )
