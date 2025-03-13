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
from typing import cast, Any, Optional
from hashlib import blake2b

from pisek.env.env import Env
from pisek.utils.paths import TaskPath, InputPath, OutputPath
from pisek.config.config_types import GenType, DataFormat
from pisek.jobs.jobs import Job, JobManager
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.compile import Compile
from pisek.task_jobs.program import RunResultKind
from pisek.task_jobs.data.data import InputSmall, OutputSmall
from pisek.task_jobs.tools import IsClean
from pisek.task_jobs.validator import ValidatorJob
from pisek.task_jobs.solution.solution import RunBatchSolution
from pisek.task_jobs.data.testcase_info import TestcaseInfo, TestcaseGenerationMode

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
from .pisek_v1 import (
    PisekV1ListInputs,
    PisekV1Generate,
    PisekV1TestDeterminism,
)

SEED_BYTES = 8
SEED_RANGE = range(0, 1 << (SEED_BYTES * 8))


class PrepareGenerator(TaskJobManager):
    """Prepares generator for use."""

    def __init__(self):
        self._inputs = []
        super().__init__("Prepare generator")

    def _get_jobs(self) -> list[Job]:
        assert self._env.config.in_gen is not None
        jobs: list[Job] = [
            compile_gen := Compile(self._env, self._env.config.in_gen_path),
            list_inputs := list_inputs_job(self._env, self._env.config.in_gen),
        ]
        list_inputs.add_prerequisite(compile_gen)
        self._list_inputs = list_inputs

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        return {"inputs": self._list_inputs.result}


def list_inputs_job(env: Env, generator: str) -> GeneratorListInputs:
    LIST_INPUTS: dict[GenType, type[GeneratorListInputs]] = {
        GenType.opendata_v1: OpendataV1ListInputs,
        GenType.cms_old: CmsOldListInputs,
        GenType.pisek_v1: PisekV1ListInputs,
    }

    return LIST_INPUTS[env.config.gen_type](env=env, generator=generator)


def generate_input(
    env: Env, generator: str, testcase_info: TestcaseInfo, seed: Optional[int]
) -> GenerateInput:
    return {
        GenType.opendata_v1: OpendataV1Generate,
        GenType.cms_old: CmsOldGenerate,
        GenType.pisek_v1: PisekV1Generate,
    }[env.config.gen_type](
        env=env, generator=generator, testcase_info=testcase_info, seed=seed
    )


def generator_test_determinism(
    env: Env, generator: str, testcase_info: TestcaseInfo, seed: Optional[int]
) -> Optional[GeneratorTestDeterminism]:
    TEST_DETERMINISM = {
        GenType.opendata_v1: OpendataV1TestDeterminism,
        GenType.pisek_v1: PisekV1TestDeterminism,
    }

    if env.config.gen_type not in TEST_DETERMINISM:
        return None
    return TEST_DETERMINISM[env.config.gen_type](
        env=env, generator=generator, testcase_info=testcase_info, seed=seed
    )


class TestcaseInfoMixin(JobManager):
    def __init__(self, name: str, **kwargs) -> None:
        self.inputs: set[InputPath] = set()
        self._gen_inputs_job: dict[Optional[int], GenerateInput] = {}
        super().__init__(name=name, **kwargs)

    def _get_seed(self, iteration: int, testcase_info: TestcaseInfo) -> int:
        name_hash = blake2b(digest_size=SEED_BYTES)
        name_hash.update(
            f"{self._env.iteration} {iteration} {testcase_info.name}".encode()
        )
        return int.from_bytes(name_hash.digest())

    def _testcase_info_jobs(self, testcase_info: TestcaseInfo, test: int) -> list[Job]:
        seeds: list[Optional[int]]
        if testcase_info.seeded:
            seeds = []
            for i in range(testcase_info.repeat):
                seeds.append(self._get_seed(i, testcase_info))
        else:
            seeds = [None]

        jobs: list[Job] = []
        self._gen_inputs_job = {}

        skipped: bool = False
        for i, seed in enumerate(seeds):
            if self._skip_testcase(testcase_info, seed, test):
                skipped = True
                self._register_skipped_testcase(testcase_info, seed, test)
                continue

            self.inputs.add(testcase_info.input_path(self._env, seed))

            inp_jobs = self._generate_input_jobs(testcase_info, seed, test, i == 0)
            out_jobs = self._solution_jobs(testcase_info, seed, test)
            if seed in self._gen_inputs_job and len(out_jobs) > 0:
                out_jobs[0].add_prerequisite(self._gen_inputs_job[seed])

            jobs += inp_jobs + out_jobs

        if (
            self._env.config.checks.generator_respects_seed
            and testcase_info.seeded
            and not skipped
        ):
            jobs += self._respects_seed_jobs(
                testcase_info, cast(list[int], seeds), test
            )
        return jobs

    def _skip_testcase(
        self, testcase_info: TestcaseInfo, seed: Optional[int], test: int
    ) -> bool:
        return testcase_info.input_path(self._env, seed) in self.inputs

    def _register_skipped_testcase(
        self, testcase_info: TestcaseInfo, seed: Optional[int], test: int
    ) -> None:
        pass

    def _generate_input_jobs(
        self,
        testcase_info: TestcaseInfo,
        seed: Optional[int],
        test: int,
        test_determinism: bool,
    ) -> list[Job]:
        jobs: list[Job] = []
        input_path = testcase_info.input_path(self._env, seed)

        gen_inp: Optional[GenerateInput]
        if testcase_info.generation_mode == TestcaseGenerationMode.generated:
            jobs.append(gen_inp := self._generate_input_job(testcase_info, seed))
            self._gen_inputs_job[seed] = gen_inp
        else:
            gen_inp = None

        if (
            testcase_info.generation_mode == TestcaseGenerationMode.generated
            and test_determinism
        ):
            assert self._env.config.in_gen is not None
            test_det = generator_test_determinism(
                self._env, self._env.config.in_gen, testcase_info, seed
            )
            if test_det is not None:
                jobs.append(test_det)
                test_det.add_prerequisite(gen_inp)

        jobs += self._check_input_jobs(input_path)

        if self._env.config.validator is not None and test > 0:
            jobs.append(
                check_input := ValidatorJob(
                    self._env,
                    self._env.config.validator,
                    input_path,
                    test,
                )
            )
            check_input.add_prerequisite(gen_inp)

        return jobs

    def _generate_input_job(
        self, testcase_info: TestcaseInfo, seed: Optional[int]
    ) -> GenerateInput:
        assert self._env.config.in_gen is not None
        gen_inp = generate_input(
            self._env, self._env.config.in_gen, testcase_info, seed
        )
        self._gen_inputs_job[seed] = gen_inp
        return gen_inp

    def _solution_jobs(
        self, testcase_info: TestcaseInfo, seed: Optional[int], test: int
    ) -> list[Job]:
        return []

    def _respects_seed_jobs(
        self, testcase_info: TestcaseInfo, seeds: list[int], test: int
    ) -> list[Job]:
        assert (
            testcase_info.generation_mode == TestcaseGenerationMode.generated
            and testcase_info.seeded
        )

        jobs: list[Job] = []

        if len(seeds) == 1:
            seeds.append(seed := self._get_seed(1, testcase_info))
            jobs += [self._generate_input_job(testcase_info, seed)]

        jobs.append(
            check_seeded := GeneratorRespectsSeed(self._env, testcase_info, *seeds[:2])
        )
        for i in range(2):
            check_seeded.add_prerequisite(self._gen_inputs_job[seeds[i]])

        return jobs

    def _check_input_jobs(
        self, input_path: InputPath, prerequisite: Optional[Job] = None
    ) -> list[Job]:
        jobs: list[Job] = []
        if self._env.config.in_format == DataFormat.text:
            jobs.append(input_clean := IsClean(self._env, input_path))
            input_clean.add_prerequisite(prerequisite)

        if self._env.config.limits.input_max_size != 0:
            jobs.append(input_small := InputSmall(self._env, input_path))
            input_small.add_prerequisite(prerequisite)

        return jobs

    def _check_output_jobs(
        self, output_path: OutputPath, prerequisite: Optional[RunBatchSolution]
    ) -> list[Job]:
        jobs: list[Job] = []
        if self._env.config.out_format == DataFormat.text:
            jobs.append(out_clean := IsClean(self._env, output_path))
            if prerequisite is not None:
                out_clean.add_prerequisite(
                    prerequisite,
                    condition=lambda r: r.kind == RunResultKind.OK,
                )

        if self._env.config.limits.output_max_size != 0:
            jobs.append(out_small := OutputSmall(self._env, output_path))
            out_small.add_prerequisite(prerequisite)

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        return {"inputs": list(sorted(self.inputs, key=lambda i: i.name))}


class RunGenerator(TaskJobManager, TestcaseInfoMixin):
    def __init__(self) -> None:
        super().__init__("Run generator")

    def _get_jobs(self) -> list[Job]:
        jobs = []

        for sub_num, inputs in self._all_testcases().items():
            for inp in inputs:
                jobs += self._testcase_info_jobs(inp, sub_num)

        return jobs
