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

from collections import deque

from pisek.jobs.job_pipeline import JobPipeline
from pisek.env.env import Env, TestingTarget
from pisek.utils.paths import InputPath
from pisek.task_jobs.task_manager import (
    TOOLS_MAN_CODE,
    INPUTS_MAN_CODE,
    BUILD_MAN_CODE,
    GENERATOR_MAN_CODE,
    JUDGE_MAN_CODE,
    SOLUTION_MAN_CODE,
)

from pisek.jobs.jobs import JobManager
from pisek.task_jobs.tools import ToolsManager
from pisek.task_jobs.data.manager import DataManager
from pisek.task_jobs.generator.manager import (
    PrepareGenerator,
    RunGenerator,
    TestcaseInfoMixin,
)
from pisek.task_jobs.judge import JudgeManager
from pisek.task_jobs.builder.build import BuildManager
from pisek.task_jobs.solution.manager import SolutionManager
from pisek.task_jobs.testing_log import CreateTestingLog
from pisek.task_jobs.completeness_check import CompletenessCheck


class TaskPipeline(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""

    def __init__(self, env: Env):
        super().__init__()
        named_pipeline: list[tuple[JobManager, str]] = [
            tools := (ToolsManager(), TOOLS_MAN_CODE),
            build := (BuildManager(), BUILD_MAN_CODE),
        ]
        build[0].add_prerequisite(*tools)
        if env.config.in_gen is not None:
            named_pipeline.append(generator := (PrepareGenerator(), GENERATOR_MAN_CODE))
            generator[0].add_prerequisite(*build)
        named_pipeline.append(inputs := (DataManager(), INPUTS_MAN_CODE))

        inputs[0].add_prerequisite(*build)
        if env.config.in_gen is not None:
            inputs[0].add_prerequisite(*generator)

        solutions = []
        self.input_generator: TestcaseInfoMixin

        if env.target == TestingTarget.generator or not env.config.solutions:
            named_pipeline.append(gen_inputs := (RunGenerator(), ""))
            gen_inputs[0].add_prerequisite(*inputs)
            self.input_generator = gen_inputs[0]

        else:
            named_pipeline.append(judge := (JudgeManager(), JUDGE_MAN_CODE))
            judge[0].add_prerequisite(*inputs)

            # First solution generates inputs
            assert (
                not env.config.judge_needs_out
                or env.solutions[0] == env.config.primary_solution
            )

            named_pipeline.append(
                first_solution := (
                    SolutionManager(env.solutions[0], True),
                    f"{SOLUTION_MAN_CODE}{env.solutions[0]}",
                )
            )
            solutions.append(first_solution)
            first_solution[0].add_prerequisite(*judge)
            self.input_generator = first_solution[0]

            for sol_name in env.solutions[1:]:
                named_pipeline.append(
                    solution := (
                        SolutionManager(sol_name, False),
                        f"{SOLUTION_MAN_CODE}{sol_name}",
                    )
                )

                solution[0].add_prerequisite(*first_solution)
                solutions.append(solution)

            for solution in solutions:
                solution[0].add_prerequisite(*inputs)

        if env.testing_log:
            named_pipeline.append(testing_log := (CreateTestingLog(), ""))
            for solution in solutions:
                testing_log[0].add_prerequisite(*solution)

        if solutions:
            named_pipeline.append(completeness_check := (CompletenessCheck(), ""))
            completeness_check[0].add_prerequisite(*judge)
            for solution in solutions:
                completeness_check[0].add_prerequisite(*solution)

        self.pipeline = deque(map(lambda x: x[0], named_pipeline))

    def input_dataset(self) -> list[InputPath]:
        if self.input_generator.result is None:
            raise RuntimeError("Input dataset has not been computed yet.")
        return self.input_generator.result["inputs"]
