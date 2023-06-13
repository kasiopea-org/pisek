# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from pisek.jobs.job_pipeline import JobPipeline

from pisek.jobs.parts.samples import SampleManager
from pisek.jobs.parts.generator import OnlineGeneratorManager
from pisek.jobs.parts.checker import CheckerManager
from pisek.jobs.parts.judge import JudgeManager
from pisek.jobs.parts.solution import SolutionManager

import os
from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.jobs.cache import Cache

class TaskPipeline(JobPipeline):
    def __init__(self, env):
        super().__init__(env)
        self.pipeline = [
            samples := SampleManager(),
            generator := OnlineGeneratorManager(),
            checker := CheckerManager(),
            judge := JudgeManager(),
            first_solution := SolutionManager(env.config.first_solution)
        ]
        checker.add_prerequisite(samples)
        checker.add_prerequisite(generator)
        
        first_solution.add_prerequisite(generator)
        first_solution.add_prerequisite(judge)

        for solution in env.config.solutions:
            if solution == env.config.first_solution:
                continue
            self.pipeline.append(solution := SolutionManager(solution))
            solution.add_prerequisite(first_solution)