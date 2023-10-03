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

from typing import Optional

from pisek.jobs.job_pipeline import JobPipeline

from pisek.jobs.parts.tools import ToolsManager
from pisek.jobs.parts.generator import RunOnlineGenerator
from pisek.jobs.parts.solution import RunPrimarySolution

class RunGen(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""
    def __init__(self, env, subtask: int, seed: int, file: Optional[str] = None):
        super().__init__()
        if env.config.contest_type == "cms":
            raise NotImplementedError("RunGen for cms is not implemented.")
 
        self.pipeline = [
            tools := ToolsManager(),
            generator := RunOnlineGenerator(subtask, seed, file)
        ]
        generator.add_prerequisite(tools)

class RunSol(JobPipeline):
    """JobPipeline that checks whether task behaves as expected."""
    def __init__(self, env, input: str, output: Optional[str] = None):
        super().__init__()
 
        self.pipeline = [
            tools := ToolsManager(),
            solve := RunPrimarySolution(input, output)
        ]
        solve.add_prerequisite(tools)
