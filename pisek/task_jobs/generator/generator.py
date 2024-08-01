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
from pisek.config.task_config import ProgramType
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.task_jobs.task_job import TaskJob, TaskJobManager
from pisek.task_jobs.run_result import RunResult, RunResultKind
from pisek.task_jobs.program import ProgramsJob
from pisek.task_jobs.compile import Compile

from .input_info import InputInfo
from .base_classes import GeneratorListInputs
from .cms_old import CmsOldListInputs, CmsOldGenerate
from .opendata_v1 import OpendataV1ListInputs, OpendataV1Generate


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
            last_gen: OpendataV1Generate
            for i, seed in enumerate(seeds):
                self._inputs.append(
                    input_ := TaskPath.generated_input_file(
                        self._env, int(sub_num), seed
                    )
                )

                jobs.append(
                    gen := OpendataV1Generate(
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
            gen := OpendataV1Generate(
                self._env,
                self._env.config.in_gen,
                TaskPath(self._file),
                self._subtask,
                self._seed,
            ),
        ]
        gen.add_prerequisite(compile_gen)

        return jobs


def list_inputs_job(env: Env, generator: TaskPath) -> GeneratorListInputs:
    return {
        GenType.opendata_v1: OpendataV1ListInputs,
        GenType.cms_old: CmsOldListInputs,
    }[env.config.gen_type](env, generator)


def generate_input(env: Env, generator: TaskPath, input_info: InputInfo, seed: int) -> None:
    return {
        GenType.opendata_v1: OpendataV1Generate,
        GenType.cms_old: CmsOldGenerate,
    }[
        env.config.gen_type
    ](env, generator, input_info, seed)
