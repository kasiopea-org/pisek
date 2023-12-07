# pisek  - Tool for developing tasks for programming competitions.
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

import os
from typing import Any, Optional, Callable, Iterable

import pisek.util as util
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env import Env
from pisek.terminal import pad, tab, MSG_LEN
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, ProgramsJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.solution_result import (
    RESULT_MARK,
    Verdict,
    SolutionResult,
    SUBTASK_SPEC,
    solution_res_true,
)
from pisek.jobs.parts.judge import judge_job, RunJudge, RunBatchJudge


class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks: list[SubtaskJobGroup] = []
        self._outputs: list[tuple[str, RunJudge]] = []
        super().__init__(f"Solution {solution} Manager")

    def _get_jobs(self) -> list[Job]:
        self._solution_file = self._solution(
            self._env.config.solutions[self.solution].source
        )
        self._judge = self._executable(self._env.config.judge)

        jobs: list[Job] = []

        jobs.append(compile_ := Compile(self._env, self._solution_file, True))
        self._compile_job = compile_

        if self._env.config.solutions[self.solution].primary:
            self._timeout = self._get_timeout("solve")
        else:
            self._timeout = self._get_timeout("sec_solve")

        testcases = {}
        for sub_num, sub in self._env.config.subtasks.subenvs():
            self.subtasks.append(SubtaskJobGroup(self._env, sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in testcases:
                    run_sol: RunSolution
                    run_judge: RunJudge
                    if self._env.config.task_type == "batch":
                        run_sol, run_judge = self._create_batch_jobs(sub_num, inp)
                        jobs += [run_sol, run_judge]
                        self._outputs.append((run_judge.output_name, run_judge))

                    elif self._env.config.task_type == "communication":
                        run_sol = run_judge = self._create_communication_jobs(inp)
                        jobs.append(run_sol)

                    testcases[inp] = run_judge
                    self.subtasks[-1].new_jobs.append(run_judge)
                    self.subtasks[-1].new_run_jobs.append(run_sol)
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp])

        return jobs

    def _create_batch_jobs(
        self, sub_num: int, inp: str
    ) -> tuple["RunSolution", RunBatchJudge]:
        """Create RunSolution and RunBatchJudge jobs for batch task type."""
        run_solution = RunBatchSolution(
            self._env, self._solution_file, self._timeout, inp
        )
        run_solution.add_prerequisite(self._compile_job)

        if sub_num == "0":
            c_out = inp.replace(".in", ".out")
        else:
            primary_sol = self._env.config.solutions[
                self._env.config.primary_solution
            ].source
            c_out = util.get_output_name(inp, primary_sol)

        out = util.get_output_name(inp, self._solution_file)
        run_judge = judge_job(
            self._judge,
            inp,
            out,
            c_out,
            sub_num,
            lambda: self._get_seed(inp),
            None,
            self._env,
        )
        run_judge.add_prerequisite(run_solution, name="run_solution")

        return (run_solution, run_judge)

    def _create_communication_jobs(self, inp: str) -> "RunCommunication":
        """Create RunCommunication job for communication task type."""
        return RunCommunication(
            self._env, self._solution_file, self._judge, self._timeout, inp
        )

    def _update(self):
        expected = self._env.config.solutions[self.solution].subtasks

        for subtask in self.subtasks:
            if subtask.definitive(expected[subtask.num]):
                subtask.cancel()

    def _get_status(self) -> str:
        msg = f"Testing {self.solution} "
        if self.state == State.canceled:
            return self._job_bar(msg)
        return pad(msg, MSG_LEN) + "|".join(map(str, self.subtasks))

    def _evaluate(self) -> Any:
        """Evaluates whether solution preformed as expected."""
        total_points = 0
        solution_conf = self._env.config.solutions[self.solution]
        expected = solution_conf.subtasks
        for sub_job in self.subtasks:
            subtask = self._env.config.subtasks[sub_job.num]
            points = sub_job.points(expected[sub_job.num])
            total_points += subtask.score * points

        points = solution_conf.points
        above = solution_conf.points_above
        below = solution_conf.points_below

        if points is not None and total_points != points:
            raise PipelineItemFailure(
                f"Solution {self.solution} should have gotten {points} but got {total_points} points."
            )
        elif above is not None and total_points < above:
            raise PipelineItemFailure(
                f"Solution {self.solution} should have gotten at least {above} but got {total_points} points."
            )
        elif below is not None and total_points > below:
            raise PipelineItemFailure(
                f"Solution {self.solution} should have gotten at most {below} but got {total_points} points."
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
                result["outputs"][job.result.verdict].append(os.path.basename(output))

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
                s += f"{count}{RESULT_MARK[verdict]}"
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

        return min(self._jobs_points())

    def _as_expected(self, expected_str: str) -> tuple[bool, bool, Optional[RunJudge]]:
        """Returns whether subtask jobs have resulted as expected and whether the result is definitive."""
        mode_quantifier = self._get_quant()
        jobs = self.new_jobs + ([] if mode_quantifier == all else self.previous_jobs)
        verdicts = self._finished_job_results(jobs)

        result = True
        definitive = True
        breaker = None
        quantifiers = [all, mode_quantifier]
        for i, quant in enumerate(quantifiers):
            oks = list(map(SUBTASK_SPEC[expected_str][i], verdicts))
            ok = quant(oks)

            result &= ok
            definitive &= (
                (quant == any and ok)
                or (quant == all and not ok)
                or (SUBTASK_SPEC[expected_str][i] == solution_res_true)
            )
            if quant == all and ok == False:
                breaker = jobs[oks.index(False)]

        return result, definitive, breaker

    def _get_quant(self) -> Callable[[Iterable[bool]], bool]:
        return all if self._env.config.fail_mode == "all" else any

    def cancel(self):
        for job in self.new_run_jobs:
            job.cancel()


class RunPrimarySolutionMan(TaskJobManager):
    def __init__(self, input_: str, output: Optional[str]):
        self._input_file = input_
        self._output_file = output
        super().__init__("Running primary solution")

    def _get_jobs(self) -> list[Job]:
        solution = self._solution(
            self._env.config.solutions[self._env.config.primary_solution].source
        )

        jobs: list[Job] = [
            compile := Compile(self._env, solution, True),
            run_solution := RunBatchSolution(
                self._env,
                solution,
                self._get_timeout("solve"),
                self._input_file,
                self._output_file,
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
        solution: str,
        timeout: float,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self.solution = solution
        self.timeout = timeout


class RunBatchSolution(RunSolution):
    def __init__(
        self,
        env: Env,
        solution: str,
        timeout: float,
        input_name: str,
        output_name: Optional[str] = None,
        **kwargs,
    ) -> None:
        name = RUN_JOB_NAME.replace(r"(.*)", os.path.basename(solution), 1).replace(
            r"(.*)", input_name, 1
        )
        super().__init__(
            env=env, name=name, solution=solution, timeout=timeout, **kwargs
        )
        self.input_name = self._input(input_name)
        self.output_name = (
            self._output(output_name)
            if output_name
            else self._output_from_input(self.input_name, solution)
        )
        self.log_file = self._log_file(input_name, self.solution)

    def _run(self) -> RunResult:
        return self._run_program(
            self.solution,
            stdin=self.input_name,
            stdout=self.output_name,
            stderr=self.log_file,
            timeout=self.timeout,
        )


class RunCommunication(RunJudge, RunSolution):
    def __init__(
        self,
        env: Env,
        solution: str,
        judge: str,
        timeout: float,
        input_name: str,
        expected_points: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            env=env,
            name=RUN_JOB_NAME.replace(r"(.*)", os.path.basename(solution), 1).replace(
                r"(.*)", input_name, 1
            ),
            judge=judge,
            input_name=input_name,
            expected_points=expected_points,
            solution=solution,
            timeout=timeout,
            **kwargs,
        )
        self.solution = solution
        self.judge_log_file = self._log_file(os.path.basename(self.input), self.judge)
        self.sol_log_file = self._log_file(os.path.basename(self.input), self.solution)
        self.timeout = timeout

    def _get_solution_run_res(self) -> RunResult:
        judge_in, sol_out = os.pipe()
        sol_in, judge_out = os.pipe()
        self._access_file(self.input)
        self._load_program(
            self.judge,
            stdin=judge_in,
            stdout=judge_out,
            stderr=self.judge_log_file,
            timeout=self.timeout,
            env={"TEST_INPUT": self.input},
        )
        self._load_program(
            self.solution,
            stdin=sol_in,
            stdout=sol_out,
            stderr=self.sol_log_file,
            timeout=self.timeout,
        )
        judge_res, sol_res = self._run_programs()
        self._judge_run_result = judge_res
        return sol_res

    def _load_stderr(self, run_result: RunResult) -> dict[str, Any]:
        KNOWN_METADATA = {"POINTS": float}
        lines = run_result.raw_stderr().split("\n")
        res = {"msg": lines[0]}
        for line in lines[1:]:
            if line.strip() == "":
                continue
            if line.count("=") != 1:
                raise PipelineItemFailure(
                    f"Metadata line must be in format 'KEY=value': {line}"
                )
            key, val = map(str.strip, line.split("="))
            if key not in KNOWN_METADATA:
                raise PipelineItemFailure(f"Unknown key {key}")

            try:
                res[key] = KNOWN_METADATA[key](val)
            except ValueError:
                raise PipelineItemFailure(f"Invalid value '{val}' for metadata {key}")

        return res

    def _judge(self) -> SolutionResult:
        if self._judge_run_result.returncode == 42:
            metadata = self._load_stderr(self._judge_run_result)
            points = metadata.get("POINTS", 1.0)
            if points == 1.0:
                return SolutionResult(
                    Verdict.ok,
                    1.0,
                    self._judge_run_result.raw_stderr(),
                    self._quote_program(self._judge_run_result),
                )
            else:
                return SolutionResult(
                    Verdict.partial,
                    points,
                    self._judge_run_result.raw_stderr(),
                    self._quote_program(self._judge_run_result),
                )
        elif self._judge_run_result.returncode == 43:
            return SolutionResult(
                Verdict.wrong_answer,
                0.0,
                self._judge_run_result.raw_stderr(),
                self._quote_program(self._judge_run_result),
            )
        else:
            raise self._create_program_failure(
                f"Judge failed on {self._judging_message()}:", self._judge_run_result
            )

    def _judging_message(self) -> str:
        return f"solution {os.path.basename(self.solution)} on input {self.input_name}"
