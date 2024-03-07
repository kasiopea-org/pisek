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
from pisek.env.env import Env

from pisek.jobs.parts.task_job import (
    TOOLS_MAN_CODE,
    INPUTS_MAN_CODE,
    GENERATOR_MAN_CODE,
    CHECKER_MAN_CODE,
    JUDGE_MAN_CODE,
    SOLUTION_MAN_CODE,
    DATA_MAN_CODE,
)

from pisek.jobs.parts.tools import ToolsManager
from pisek.jobs.parts.data import DataManager
from pisek.jobs.parts.generator import GeneratorManager
from pisek.jobs.parts.checker import CheckerManager
from pisek.jobs.parts.judge import JudgeManager
from pisek.jobs.parts.solution import SolutionManager
from pisek.jobs.parts.data import DataCheckingManager
from pisek.jobs.parts.testing_log import CreateTestingLog


class TaskPipeline(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""

    def __init__(self, env: Env):
        super().__init__()
        named_pipeline = [
            tools := (ToolsManager(), TOOLS_MAN_CODE),
            generator := (GeneratorManager(), GENERATOR_MAN_CODE),
            inputs := (DataManager(), INPUTS_MAN_CODE),
        ]
        generator[0].add_prerequisite(*tools)
        inputs[0].add_prerequisite(*generator)

        if env.target != "solution":
            named_pipeline.append(checker := (CheckerManager(), CHECKER_MAN_CODE))
            checker[0].add_prerequisite(*inputs)

        solutions = []
        if env.solutions:
            named_pipeline.append(judge := (JudgeManager(), JUDGE_MAN_CODE))
            judge[0].add_prerequisite(*inputs)

            if env.config.judge_needs_out or (
                env.config.primary_solution in env.solutions
            ):
                named_pipeline.append(
                    primary_solution := (
                        SolutionManager(env.config.primary_solution),
                        f"{SOLUTION_MAN_CODE}{env.config.primary_solution}",
                    )
                )
                solutions.append(primary_solution)

        for sol_name in env.solutions:
            if sol_name == env.config.primary_solution:
                continue
            named_pipeline.append(
                solution := (
                    SolutionManager(sol_name),
                    f"{SOLUTION_MAN_CODE}{sol_name}",
                )
            )
            if env.config.judge_needs_out:
                solution[0].add_prerequisite(*primary_solution)
            solutions.append(solution)

        for solution in solutions:
            solution[0].add_prerequisite(*inputs)
            solution[0].add_prerequisite(*judge)

        named_pipeline.append(data_check := (DataCheckingManager(), DATA_MAN_CODE))
        data_check[0].add_prerequisite(*inputs)
        for solution in solutions:
            data_check[0].add_prerequisite(*solution)

        if env.testing_log:
            named_pipeline.append(testing_log := (CreateTestingLog(), ""))
            for solution in solutions:
                testing_log[0].add_prerequisite(*solution)

        self.pipeline = deque(map(lambda x: x[0], named_pipeline))
