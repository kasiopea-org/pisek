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
import os
from typing import Optional
from functools import partial

import pisek.utils.util as util
from pisek.jobs.job_pipeline import JobPipeline
from pisek.utils.pipeline_tools import run_pipeline
from pisek.env.env import Env
from pisek.jobs.cache import Cache

from pisek.jobs.parts.tools import ToolsManager
from pisek.jobs.parts.generator import RunOnlineGeneratorMan
from pisek.jobs.parts.solution import RunPrimarySolutionMan
from pisek.jobs.parts.solution_result import SolutionResult
from pisek.jobs.parts.judge import RunKasiopeaJudgeMan


class KasiopeaInputCase:
    def __init__(self, path: str, subtask: int, seed: int):
        self.path = path

        self.subtask: int = subtask
        self.seed: int = seed

        self.input: Optional[str] = None
        self.correct_output: Optional[str] = None

    def gen_input(self, input_: Optional[str] = None) -> None:
        if input_ is None:
            input_ = util.get_input_name(self.seed, self.subtask)
        self.input = input_

        res = run_pipeline(
            self.path,
            partial(
                ServerGenKasiopea, subtask=self.subtask, seed=self.seed, file=self.input
            ),
        )
        if res != 0:
            raise RuntimeError("Generating input failed.")

    def gen_correct_output(
        self, input_: Optional[str] = None, correct_output: Optional[str] = None
    ) -> None:
        self.input = input_ or self.input
        if self._needs_generating(self.input):
            self.gen_input(self.input)
        assert self.input is not None

        if correct_output is None:
            correct_output = util.get_output_name(self.input, "")
        self.correct_output = correct_output

        res = run_pipeline(
            self.path,
            partial(ServerSolve, input_=self.input, output=self.correct_output),
        )

        if res != 0:
            raise RuntimeError("Generating correct output failed.")

    def judge(
        self,
        output: str,
        input_: Optional[str] = None,
        correct_output: Optional[str] = None,
    ):
        env = Env.load()
        if env is None:
            return 1

        self.input = input_ or self.input
        if env.config.judge_needs_in:
            if self._needs_generating(self.input):
                self.gen_input(self.input)
            assert self.input is not None
        else:
            self.input = "/dev/null"

        self.correct_output = correct_output or self.correct_output
        if env.config.judge_needs_out:
            if self._needs_generating(self.correct_output):
                self.gen_correct_output(self.correct_output)
            assert self.correct_output is not None
        else:
            self.correct_output = "/dev/null"

        pipeline = ServerJudgeKasiopea(
            env.fork(),
            subtask=self.subtask,
            seed=self.seed,
            input_=self.input,
            output=output,
            correct_output=self.correct_output,
        )
        res = pipeline.run_jobs(cache := Cache(env), env)

        if res != 0:
            raise RuntimeError("Judging failed.")

        judging_res = pipeline.judge_result()
        return judging_res.points, judging_res.judge_stderr

    def _needs_generating(self, put: Optional[str]):
        return put is None or not os.path.exists(os.path.join(self.path, "data/", put))


class ServerGenKasiopea(JobPipeline):
    """Generate an input."""

    def __init__(self, env, subtask: int, seed: int, file: str):
        super().__init__()
        if env.config.contest_type == "cms":
            raise NotImplementedError("RunGen for cms is not implemented.")

        self.pipeline = deque(
            [
                tools := ToolsManager(),
                generator := RunOnlineGeneratorMan(subtask, seed, file),
            ]
        )
        generator.add_prerequisite(tools)


class ServerSolve(JobPipeline):
    """Run a primary solution."""

    def __init__(self, env, input_: str, output: Optional[str]):
        super().__init__()

        self.pipeline = deque(
            [
                tools := ToolsManager(),
                solve := RunPrimarySolutionMan(input_, output),
            ]
        )
        solve.add_prerequisite(tools)


class ServerJudgeKasiopea(JobPipeline):
    """Run a primary solution."""

    def __init__(
        self,
        env,
        subtask: int,
        seed: int,
        input_: str,
        output: str,
        correct_output: str,
    ):
        super().__init__()

        self.pipeline = deque(
            [
                tools := ToolsManager(),
                judge := RunKasiopeaJudgeMan(
                    subtask, seed, input_, output, correct_output
                ),
            ]
        )
        judge.add_prerequisite(tools)
        self._judge_man = judge

    def judge_result(self) -> SolutionResult:
        return self._judge_man.judge_result()
