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
from typing import Any

from pisek.env.env import Env
from pisek.utils.paths import TaskPath, GENERATED_SUBDIR
from pisek.config.config_types import GenType
from pisek.jobs.jobs import Job
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.compile import Compile

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism
from .cms_old import CmsOldListInputs, CmsOldGenerate
from .opendata_v1 import (
    OpendataV1ListInputs,
    OpendataV1Generate,
    OpendataV1TestDeterminism,
)


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
) -> GeneratorTestDeterminism:
    return {GenType.opendata_v1: OpendataV1TestDeterminism}[env.config.gen_type](
        env=env, generator=generator, input_info=input_info, seed=seed
    )
