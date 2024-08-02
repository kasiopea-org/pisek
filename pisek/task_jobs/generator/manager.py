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

import random
from typing import Any, Optional

from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.config.config_types import GenType, DataFormat
from pisek.jobs.jobs import Job, JobManager
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.compile import Compile
from pisek.task_jobs.data.data import InputSmall
from pisek.task_jobs.tools import IsClean
from pisek.task_jobs.checker import CheckerJob

from .input_info import InputInfo
from .base_classes import (
    GeneratorListInputs,
    GenerateInput,
    GeneratorTestDeterminism,
    GeneratorRespectsSeed,
)
from .cms_old import CmsOldListInputs, CmsOldGenerate
from .opendata_v1 import (
    OpendataV1ListInputs,
    OpendataV1Generate,
    OpendataV1TestDeterminism,
)

SEED_RANGE = range(0, 16**8)


class PrepareGenerator(TaskJobManager):
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


def list_inputs_job(env: Env, generator: TaskPath) -> GeneratorListInputs:
    return {
        GenType.opendata_v1: OpendataV1ListInputs,
        GenType.cms_old: CmsOldListInputs,
    }[env.config.gen_type](env=env, generator=generator)


def generate_input(
    env: Env, generator: TaskPath, input_info: InputInfo, seed: int
) -> GenerateInput:
    return {
        GenType.opendata_v1: OpendataV1Generate,
        GenType.cms_old: CmsOldGenerate,
    }[
        env.config.gen_type
    ](env=env, generator=generator, input_info=input_info, seed=seed)


def generator_test_determinism(
    env: Env, generator: TaskPath, input_info: InputInfo, seed: int
) -> Optional[GeneratorTestDeterminism]:
    TEST_DETERMINISM = {GenType.opendata_v1: OpendataV1TestDeterminism}

    if env.config.gen_type not in TEST_DETERMINISM:
        return None
    return TEST_DETERMINISM[env.config.gen_type](
        env=env, generator=generator, input_info=input_info, seed=seed
    )


class InputsInfoMixin(JobManager):
    def __init__(self, name: str, **kwargs) -> None:
        self._generate_inputs: dict[int, GenerateInput] = {}
        super().__init__(name=name, **kwargs)

    def _input_info_jobs(self, input_info: InputInfo, subtask: int) -> list[Job]:
        repeat = input_info.repeat * (self._env.inputs if input_info.seeded else 1)

        jobs: list[Job] = []

        random.seed(4)  # Reproducibility!
        seeds = random.sample(SEED_RANGE, repeat)
        for i, seed in enumerate(seeds):
            if self._skip_input(input_info, seed, subtask):
                continue

            inp_jobs = self._generate_input_jobs(input_info, seed, subtask, i == 0)
            out_jobs = self._solution_jobs(input_info, seed, subtask)
            if seed in self._generate_inputs and len(out_jobs) > 0:
                out_jobs[0].add_prerequisite(self._generate_inputs[seed])

            jobs += inp_jobs + out_jobs

        jobs += self._respects_seed_jobs(input_info, seeds, subtask)
        return jobs

    def _skip_input(self, input_info: InputInfo, seed: int, subtask: int) -> bool:
        return not self._env.config.subtasks[subtask].new_in_subtask(
            input_info.task_path(self._env, seed).name
        )

    def _generate_input_jobs(
        self, input_info: InputInfo, seed: int, subtask: int, test_determinism: bool
    ) -> list[Job]:
        if not input_info.is_generated:
            return []

        jobs: list[Job] = [gen_inp := self._generate_input_job(input_info, seed)]
        self._generate_inputs[seed] = gen_inp
        input_path = input_info.task_path(self._env, seed)

        if test_determinism:
            test_det = generator_test_determinism(
                self._env, self._env.config.in_gen, input_info, seed
            )
            if test_det is not None:
                jobs.append(test_det)
                test_det.add_prerequisite(gen_inp)

        if self._env.config.in_format == DataFormat.text:
            jobs.append(input_clean := IsClean(self._env, input_path))
            input_clean.add_prerequisite(gen_inp)

        if self._env.config.limits.input_max_size != 0:
            jobs.append(input_small := InputSmall(self._env, input_path))
            input_small.add_prerequisite(gen_inp)

        if self._env.config.checker is not None:
            jobs.append(
                check_input := CheckerJob(
                    self._env,
                    self._env.config.checker,
                    input_path,
                    subtask,
                )
            )
            check_input.add_prerequisite(gen_inp)

        return jobs

    def _generate_input_job(self, input_info: InputInfo, seed: int) -> GenerateInput:
        gen_inp = generate_input(self._env, self._env.config.in_gen, input_info, seed)
        self._generate_inputs[seed] = gen_inp
        return gen_inp

    def _solution_jobs(
        self, input_info: InputInfo, seed: int, subtask: int
    ) -> list[Job]:
        return []

    def _respects_seed_jobs(
        self, input_info: InputInfo, seeds: list[int], subtask: int
    ) -> list[Job]:
        if not (input_info.is_generated and input_info.seeded):
            return []

        if not self._env.config.subtasks[subtask].new_in_subtask(
            input_info.task_path(self._env, seeds[0]).name
        ):
            return []

        jobs: list[Job] = []
        if len(seeds) == 1:
            while (seed := random.choice(SEED_RANGE)) == seeds[0]:
                pass
            seeds.append(seed)
            jobs += [self._generate_input_job(input_info, seed)]

        jobs.append(
            check_seeded := GeneratorRespectsSeed(self._env, input_info, *seeds[:2])
        )
        for i in range(2):
            check_seeded.add_prerequisite(self._generate_inputs[seeds[i]])

        return jobs


class RunGenerator(TaskJobManager, InputsInfoMixin):
    def __init__(self) -> None:
        super().__init__("Run generator")

    def _get_jobs(self) -> list[Job]:
        jobs = []

        for sub_num, inputs in self._all_inputs().items():
            for inp in inputs:
                jobs += self._input_info_jobs(inp, sub_num)

        return jobs
