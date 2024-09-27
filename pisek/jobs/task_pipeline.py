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

from pisek.task_jobs.task_manager import (
    TOOLS_MAN_CODE,
    INPUTS_MAN_CODE,
    GENERATOR_MAN_CODE,
    CHECKER_MAN_CODE,
    JUDGE_MAN_CODE,
    SOLUTION_MAN_CODE,
)

from pisek.task_jobs.tools import ToolsManager
from pisek.task_jobs.data.manager import DataManager
from pisek.task_jobs.generator.manager import (
    PrepareGenerator,
    RunGenerator,
    InputsInfoMixin,
)
from pisek.task_jobs.checker import CheckerManager
from pisek.task_jobs.judge import JudgeManager
from pisek.task_jobs.solution.manager import SolutionManager
from pisek.task_jobs.testing_log import CreateTestingLog
from pisek.task_jobs.completeness_check import CompletenessCheck
from pisek.utils.paths import TaskPath


class TaskPipeline(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""

    def __init__(self, env: Env):
        super().__init__()
        named_pipeline = [
            tools := (ToolsManager(), TOOLS_MAN_CODE),
            generator := (PrepareGenerator(), GENERATOR_MAN_CODE),
            checker := (CheckerManager(), CHECKER_MAN_CODE),
            inputs := (DataManager(), INPUTS_MAN_CODE),
        ]
        generator[0].add_prerequisite(*tools)
        checker[0].add_prerequisite(*tools)
        inputs[0].add_prerequisite(*generator)
        inputs[0].add_prerequisite(*checker)

        solutions = []
        self.input_generator: InputsInfoMixin

        if env.target == TestingTarget.generator:
            named_pipeline.append(gen_inputs := (RunGenerator(), ""))
            gen_inputs[0].add_prerequisite(*inputs)
            self.input_generator = gen_inputs[0]

        else:
            named_pipeline.append(judge := (JudgeManager(), JUDGE_MAN_CODE))
            judge[0].add_prerequisite(*inputs)

            # First solution generates inputs
            first_solution_name = (
                env.config.primary_solution
                if env.config.judge_needs_out
                or env.config.primary_solution in env.solutions
                else env.solutions[0]
            )

            named_pipeline.append(
                first_solution := (
                    SolutionManager(first_solution_name, True),
                    f"{SOLUTION_MAN_CODE}{first_solution_name}",
                )
            )
            solutions.append(first_solution)
            first_solution[0].add_prerequisite(*judge)
            self.input_generator = first_solution[0]

            for sol_name in env.solutions:
                if sol_name == first_solution_name:
                    continue
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

        if env.target in (TestingTarget.solution, TestingTarget.all):
            named_pipeline.append(completeness_check := (CompletenessCheck(), ""))
            completeness_check[0].add_prerequisite(*judge)
            for solution in solutions:
                completeness_check[0].add_prerequisite(*solution)

        self.pipeline = deque(map(lambda x: x[0], named_pipeline))

    def input_dataset(self) -> list[TaskPath]:
        if self.input_generator.result is None:
            raise RuntimeError("Input dataset has not been computed yet.")
        return self.input_generator.result["inputs"]
