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

import pisek.util as util
from pisek.jobs.job_pipeline import JobPipeline
from pisek.pipeline_tools import run_pipeline

from pisek.jobs.parts.tools import ToolsManager
from pisek.jobs.parts.generator import RunOnlineGeneratorMan
from pisek.jobs.parts.solution import RunPrimarySolutionMan
from pisek.jobs.parts.judge import judge_job

class KasiopeaInputCase():
    def __init__(self, subtask: int, seed: int):
        self.subtask: int = subtask
        self.seed: int = seed
 
        self.input: Optional[str] = None
        self.correct_output: Optional[str] = None

    def gen_input(self, input: str) -> None:
        self.input = input
        res = run_pipeline(
            path,
            partial(ServerGenKasiopea, self.subtask, self.seed, self.input),
            **env_args
        )
        if res != 0:
            raise RuntimeError("Generating input failed.")

    def gen_correct_output(self, input: Optional[str] = None, correct_output: Optional[str] = None) -> None:
        self.input = input or self.input
        if self.input is None:
            self.gen_input()

        self.correct_output = correct_output
        res = run_pipeline(
            path,
            partial(ServerSolve, input=input, output=self.correct_output),
            **env_args
        )
        if res != 0:
            raise RuntimeError("Generating output failed.")

    def judge(self):
        pass


class ServerGenKasiopea(JobPipeline):
    """Generate an input."""
    def __init__(self, env, subtask: int, seed: int, file: str):
        super().__init__()
        if env.config.contest_type == "cms":
            raise NotImplementedError("RunGen for cms is not implemented.")
 
        self.pipeline = [
            tools := ToolsManager(),
            generator := RunOnlineGeneratorMan(subtask, seed, file)
        ]
        generator.add_prerequisite(tools)

class ServerSolve(JobPipeline):
    """Run a primary solution."""
    def __init__(self, env, input: str, output: Optional[str]):
        super().__init__()
 
        self.pipeline = [
            tools := ToolsManager(),
            solve := RunPrimarySolutionMan(input, output),
        ]
        solve.add_prerequisite(tools)

class ServerJudgeKasiopea(JobPipeline):
    """Run a primary solution."""
    def __init__(self, env, input: str, output: Optional[str]):
        super().__init__()
 
        self.pipeline = [
            tools := ToolsManager(),
            judge := judge_job(),
        ]
        judge.add_prerequisite(tools)
