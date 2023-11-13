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

from collections import deque

from pisek.jobs.job_pipeline import JobPipeline
from pisek.env import Env

from pisek.jobs.parts.tools import ToolsManager
from pisek.jobs.parts.samples import SampleManager
from pisek.jobs.parts.generator import GeneratorManager
from pisek.jobs.parts.checker import CheckerManager
from pisek.jobs.parts.judge import JudgeManager
from pisek.jobs.parts.solution import SolutionManager
from pisek.jobs.parts.data import DataManager


class TaskPipeline(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""

    def __init__(self, env: Env):
        super().__init__()
        self.pipeline = deque(
            [
                tools := ToolsManager(),
                samples := SampleManager(),
                generator := GeneratorManager(),
                checker := CheckerManager(),
            ]
        )
        generator.add_prerequisite(tools)

        checker.add_prerequisite(samples)
        checker.add_prerequisite(generator)

        solutions = []
        if env.solutions:
            self.pipeline.append(judge := JudgeManager())
            judge.add_prerequisite(samples)

            self.pipeline.append(
                primary_solution := SolutionManager(env.config.primary_solution)
            )
            primary_solution.add_prerequisite(generator)
            primary_solution.add_prerequisite(judge)
            solutions.append(primary_solution)

        for solution in env.solutions:
            if solution == env.config.primary_solution:
                continue
            self.pipeline.append(solution := SolutionManager(solution))
            solution.add_prerequisite(primary_solution)
            solutions.append(solution)

        if env.solutions:
            self.pipeline.append(data_check := DataManager())

            data_check.add_prerequisite(samples, name=f"samples")
            data_check.add_prerequisite(generator, name=f"generator")
            for solution in solutions:
                data_check.add_prerequisite(
                    solution, name=f"solution_{solution.solution}"
                )
