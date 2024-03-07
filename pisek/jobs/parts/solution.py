# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
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
from typing import Any, Optional

from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.env.task_config import ProgramType, FailMode
from pisek.utils.text import pad, pad_left, tab
from pisek.utils.terminal import MSG_LEN
from pisek.jobs.parts.verdicts_eval import evaluate_verdicts
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, ProgramsJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.solution_result import Verdict, SolutionResult
from pisek.jobs.parts.judge import judge_job, RunJudge, RunCMSJudge, RunBatchJudge


class SolutionManager(TaskJobManager):
    """Runs a solution and checks if it works as expected."""

    def __init__(self, solution_label: str) -> None:
        self.solution_label: str = solution_label
        self.solution_points: Optional[float] = None
        self.subtasks: list[SubtaskJobGroup] = []
        self._outputs: list[tuple[TaskPath, RunJudge]] = []
        super().__init__(f"Solution {solution_label} Manager")

    def _get_jobs(self) -> list[Job]:
        self.is_primary: bool = self._env.config.solutions[self.solution_label].primary
        self._solution = TaskPath.solution_path(
            self._env, self._env.config.solutions[self.solution_label].source
        )

        jobs: list[Job] = []

        jobs.append(compile_ := Compile(self._env, self._solution, True))
        self._compile_job = compile_

        self._judges: dict[TaskPath, RunJudge] = {}
        for sub_num, sub in self._env.config.subtasks.items():
            self.subtasks.append(SubtaskJobGroup(self._env, sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in self._judges:
                    run_sol: RunSolution
                    run_judge: RunJudge
                    if self._env.config.task_type == "batch":
                        run_sol, run_judge = self._create_batch_jobs(sub_num, inp)
                        jobs += [run_sol, run_judge]
                        self._outputs.append((run_judge.output, run_judge))

                    elif self._env.config.task_type == "communication":
                        run_sol = run_judge = self._create_communication_jobs(inp)
                        jobs.append(run_sol)

                    self._judges[inp] = run_judge
                    self.subtasks[-1].new_jobs.append(run_judge)
                    self.subtasks[-1].new_run_jobs.append(run_sol)
                else:
                    self.subtasks[-1].previous_jobs.append(self._judges[inp])

        return jobs

    def _create_batch_jobs(
        self, sub_num: int, inp: TaskPath
    ) -> tuple["RunSolution", RunBatchJudge]:
        """Create RunSolution and RunBatchJudge jobs for batch task type."""
        run_solution = RunBatchSolution(
            self._env,
            self._solution,
            self.is_primary,
            inp,
        )
        run_solution.add_prerequisite(self._compile_job)

        if sub_num == 0:
            c_out = TaskPath.output_static_file(self._env, inp.name)
        else:
            primary_sol = self._env.config.solutions[
                self._env.config.primary_solution
            ].source
            c_out = TaskPath.output_file(self._env, inp.name, primary_sol)

        out = TaskPath.output_file(self._env, inp.name, self._solution.name)
        run_judge = judge_job(
            inp,
            out,
            c_out,
            sub_num,
            lambda: self._get_seed(inp.name),
            None,
            self._env,
        )
        run_judge.add_prerequisite(run_solution, name="run_solution")

        return (run_solution, run_judge)

    def _create_communication_jobs(self, inp: TaskPath) -> "RunCommunication":
        """Create RunCommunication job for communication task type."""
        if self._env.config.out_judge is None:
            raise RuntimeError("Unset judge for communication.")

        judge = TaskPath(self._env.config.out_judge)
        return RunCommunication(self._env, self._solution, self.is_primary, judge, inp)

    def _update(self):
        """Cancel running on inputs that can't change anything."""
        expected = self._env.config.solutions[self.solution_label].subtasks

        for subtask in self.subtasks:
            if subtask.definitive(expected[subtask.num]):
                subtask.cancel()

    def _get_status(self) -> str:
        msg = f"Testing {self.solution_label} "
        if self.state == State.canceled:
            return self._job_bar(msg)
        msg = pad(msg, MSG_LEN)

        INT_PLACES = len(str(self._env.config.total_points))
        DEC_PLACES = 2
        if self.solution_points is None:
            points = "?" + "." + "?" * DEC_PLACES
        else:
            points = format(self.solution_points, f".{DEC_PLACES}f")
        points = pad_left(f"{points}p ", INT_PLACES + DEC_PLACES + 3)

        subtasks_res = "|".join(map(str, self.subtasks))
        return msg + points + subtasks_res

    def _evaluate(self) -> None:
        """Evaluates whether solution preformed as expected."""
        self.solution_points = 0
        solution_conf = self._env.config.solutions[self.solution_label]
        expected = solution_conf.subtasks
        for sub_job in self.subtasks:
            subtask = self._env.config.subtasks[sub_job.num]
            sub_points = sub_job.points(expected[sub_job.num])
            self.solution_points += subtask.points * sub_points

        points = solution_conf.points
        above = solution_conf.points_above
        below = solution_conf.points_below

        if points is not None and self.solution_points != points:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten {points} but got {self.solution_points} points."
            )
        elif above is not None and self.solution_points < above:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten at least {above} but got {self.solution_points} points."
            )
        elif below is not None and self.solution_points > below:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten at most {below} but got {self.solution_points} points."
            )

    def _compute_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        result["outputs"] = {
            Verdict.ok: [],
            Verdict.partial: [],
            Verdict.wrong_answer: [],
            Verdict.timeout: [],
            Verdict.error: [],
        }
        for output, job in self._outputs:
            if job.result is not None:
                result["outputs"][job.result.verdict].append(output)

        result["results"] = {}
        for inp in self._judges:
            result["results"][inp] = self._judges[inp].result

        return result


class SubtaskJobGroup:
    """Groups jobs of a single subtask."""

    def __init__(self, env: Env, num) -> None:
        self.num = int(num)
        self._env = env
        self.new_run_jobs: list[RunSolution] = []
        self.previous_jobs: list[RunJudge] = []
        self.new_jobs: list[RunJudge] = []

    def _job_results(self, jobs: list[RunJudge]) -> list[Optional[SolutionResult]]:
        return list(map(lambda j: j.result, jobs))

    def _finished_jobs(self, jobs: list[RunJudge]) -> list[RunJudge]:
        return list(filter(lambda j: j.result is not None, jobs))

    def _finished_job_results(self, jobs: list[RunJudge]) -> list[SolutionResult]:
        filtered = []
        for res in self._job_results(jobs):
            if res is not None:
                filtered.append(res)
        return filtered

    def _judge_verdicts(self, jobs: list[RunJudge]) -> list[Optional[Verdict]]:
        return list(
            map(lambda r: r.verdict if r is not None else None, self._job_results(jobs))
        )

    def _jobs_points(self) -> list[float]:
        return list(
            map(
                lambda r: r.points,
                self._finished_job_results(self.new_jobs + self.previous_jobs),
            )
        )

    def __str__(self) -> str:
        s = "("
        previous = list(
            map(
                lambda x: x.verdict if x else None,
                self._job_results(self.previous_jobs),
            )
        )
        for verdict in Verdict:
            count = previous.count(verdict)
            if count > 0:
                s += f"{count}{verdict.mark()}"
        s += ") "
        if s == "() ":
            s = ""

        for job, result in zip(self.new_jobs, self._job_results(self.new_jobs)):
            if job.state == State.canceled:
                s += "-"
            elif result is None:
                s += " "
            else:
                s += str(result)

        return s

    def definitive(self, expected_str: str) -> bool:
        """Checks whether subtask jobs have resulted in outcome that cannot be changed."""
        if self._env.all_inputs:
            return False

        if self._env.skip_on_timeout and Verdict.timeout in self._judge_verdicts(
            self.new_jobs
        ):
            return True

        if expected_str == "X" and min(self._jobs_points(), default=1) > 0:
            return False  # Cause X is very very special

        return self._as_expected(expected_str)[1]

    def points(self, expected_str: str) -> float:
        """Returns points from this subtask. Raises PipelineItemFailure if not as expected."""
        ok, _, breaker = self._as_expected(expected_str)
        if not ok:
            msg = f"Subtask {self.num} did not result as expected: '{expected_str}'"
            if breaker is not None:
                msg += f"\n{tab(breaker.message())}"
            raise PipelineItemFailure(msg)

        return min(self._jobs_points(), default=1.0)

    def _as_expected(self, expected_str: str) -> tuple[bool, bool, Optional[RunJudge]]:
        """
        Returns tuple:
            - whether subtask jobs have resulted as expected
            - whether the result is definitive (cannot be changed)
            - a job that makes the result different than expected (if there is one particular)
        """

        jobs = self.new_jobs + (
            [] if self._env.config.fail_mode == FailMode.all else self.previous_jobs
        )

        finished_jobs = self._finished_jobs(jobs)
        verdicts = self._finished_job_results(jobs)

        result, definitive, breaker = evaluate_verdicts(
            self._env.config, list(map(lambda r: r.verdict, verdicts)), expected_str
        )

        breaker_job = None if breaker is None else finished_jobs[breaker]

        return result, definitive, breaker_job

    def cancel(self):
        for job in self.new_run_jobs:
            job.cancel()


class RunPrimarySolutionMan(TaskJobManager):
    def __init__(self, input_: str, output: Optional[str]):
        self._input = input_
        self._output = output
        super().__init__("Running primary solution")

    def _get_jobs(self) -> list[Job]:
        solution = TaskPath.solution_path(
            self._env,
            self._env.config.solutions[self._env.config.primary_solution].source,
        )

        jobs: list[Job] = [
            compile := Compile(self._env, solution, True),
            run_solution := RunBatchSolution(
                self._env,
                solution,
                True,
                TaskPath(self._input),
                TaskPath(self._output) if self._output else None,
            ),
        ]
        run_solution.add_prerequisite(compile)

        return jobs


RUN_JOB_NAME = r"Run (.*) on input (.*)"


class RunSolution(ProgramsJob):
    """Runs solution on given input."""

    def __init__(
        self,
        env: Env,
        name: str,
        solution: TaskPath,
        is_primary: bool,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.solution = solution
        self.is_primary = is_primary

    def _solution_type(self) -> ProgramType:
        return (ProgramType.solve) if self.is_primary else (ProgramType.sec_solve)


class RunBatchSolution(RunSolution):
    def __init__(
        self,
        env: Env,
        solution: TaskPath,
        is_primary: bool,
        input_: TaskPath,
        output: Optional[TaskPath] = None,
        **kwargs,
    ) -> None:
        name = RUN_JOB_NAME.replace(r"(.*)", solution.name, 1).replace(
            r"(.*)", input_.name, 1
        )
        super().__init__(
            env=env, name=name, solution=solution, is_primary=is_primary, **kwargs
        )
        self.input = input_
        self.output = (
            output
            if output
            else TaskPath.output_file(self._env, self.input.name, solution.name)
        )
        self.log_file = TaskPath.log_file(self._env, input_.name, self.solution.name)

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
        solution: TaskPath,
        is_primary: bool,
        judge: TaskPath,
        input_: TaskPath,
        expected_points: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            env=env,
            name=RUN_JOB_NAME.replace(r"(.*)", solution.name, 1).replace(
                r"(.*)", input_.name, 1
            ),
            judge=judge,
            input_=input_,
            expected_points=expected_points,
            judge_log_file=TaskPath.log_file(self._env, input_.name, solution.name),
            solution=solution,
            is_primary=is_primary,
            **kwargs,
        )
        self.solution = solution
        self.sol_log_file = TaskPath.log_file(
            self._env, self.input.name, self.solution.name
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
        return f"solution {self.solution:p} on input {self.input:p}"
