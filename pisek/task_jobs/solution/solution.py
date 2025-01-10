# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import tempfile
import time
from typing import Optional

from pisek.env.env import Env
from pisek.utils.paths import TaskPath, InputPath
from pisek.config.config_types import ProgramType
from pisek.task_jobs.program import RunResult, ProgramsJob
from pisek.task_jobs.solution.solution_result import Verdict, SolutionResult
from pisek.task_jobs.judge import RunCMSJudge


class RunSolution(ProgramsJob):
    """Runs solution on given input."""

    def __init__(
        self,
        env: Env,
        name: str,
        solution: str,
        is_primary: bool,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.solution = solution
        self.is_primary = is_primary

    def _solution_type(self) -> ProgramType:
        return (
            (ProgramType.primary_solution)
            if self.is_primary
            else (ProgramType.secondary_solution)
        )


class RunBatchSolution(RunSolution):
    def __init__(
        self,
        env: Env,
        solution: str,
        is_primary: bool,
        input_: InputPath,
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=f"Run {solution} on input {input_:n}",
            solution=solution,
            is_primary=is_primary,
            **kwargs,
        )
        self.input = input_
        self.output = input_.to_output()
        self.log_file = input_.to_log("solution")

    def _run(self) -> RunResult:
        return self._run_program(
            program_type=self._solution_type(),
            program=self.solution,
            stdin=self.input,
            stdout=self.output,
            stderr=self.log_file,
        )


class RunCommunication(RunCMSJudge, RunSolution):
    def __init__(
        self,
        env: Env,
        solution: str,
        is_primary: bool,
        judge: str,
        test: int,
        input_: InputPath,
        expected_verdict: Optional[Verdict] = None,
        **kwargs,
    ):
        self.sol_log_file = input_.to_log("solution")
        super().__init__(
            env=env,
            name=f"Run {solution} on input {input_:n}",
            judge=judge,
            test=test,
            input_=input_,
            expected_verdict=expected_verdict,
            judge_log_file=self.sol_log_file.to_judge_log(judge),
            solution=solution,
            is_primary=is_primary,
            **kwargs,
        )

    def _get_solution_run_res(self) -> RunResult:
        with tempfile.TemporaryDirectory() as fifo_dir:
            fifo_from_solution = os.path.join(fifo_dir, "solution-to-manager")
            fifo_to_solution = os.path.join(fifo_dir, "manager-to-solution")

            os.mkfifo(fifo_from_solution)
            os.mkfifo(fifo_to_solution)

            pipes = [
                os.open(fifo_from_solution, os.O_RDWR),
                os.open(fifo_to_solution, os.O_RDWR),
                # Open fifos to prevent blocking on future opens
                fd_from_solution := os.open(fifo_from_solution, os.O_WRONLY),
                fd_to_solution := os.open(fifo_to_solution, os.O_RDONLY),
            ]

            self._load_program(
                ProgramType.judge,
                self.judge,
                stdin=self.input,
                stdout=self.points_file,
                stderr=self.judge_log_file,
                args=[fifo_from_solution, fifo_to_solution],
            )

            self._load_program(
                self._solution_type(),
                self.solution,
                stdin=fd_to_solution,
                stdout=fd_from_solution,
                stderr=self.sol_log_file,
            )

            def close_pipes(_):
                time.sleep(0.05)
                for pipe in pipes:
                    os.close(pipe)

            self._load_callback(close_pipes)

            judge_res, sol_res = self._run_programs()
            self._judge_run_result = judge_res

            return sol_res

    def _judge(self) -> SolutionResult:
        return self._load_solution_result(self._judge_run_result)

    def _judging_message(self) -> str:
        return f"solution {self.solution} on input {self.input:p}"
