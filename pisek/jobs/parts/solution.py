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
from typing import Any, Optional

import pisek.util as util
from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env import Env
from pisek.terminal import pad, tab, MSG_LEN
from pisek.jobs.parts.task_job import TaskJobManager
from pisek.jobs.parts.program import RunResult, ProgramJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.solution_result import RESULT_MARK, Verdict, SolutionResult
from pisek.jobs.parts.judge import judge_job, RunJudge


class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks: list[SubtaskJobGroup] = []
        self._outputs: list[tuple[str, RunJudge]] = []
        super().__init__(f"Solution {solution} Manager")

    def _get_jobs(self) -> list[Job]:
        solution = self._solution(self._env.config.solutions[self.solution].source)
        judge = self._executable(self._env.config.judge)

        jobs: list[Job] = []

        jobs.append(compile := Compile(self._env, solution, True, self._compile_args()))

        if self._env.config.solutions[self.solution].primary:
            timeout = self._get_timeout("solve")
        else:
            timeout = self._get_timeout("sec_solve")

        testcases = {}
        used_inp = set()
        for sub_num, sub in self._env.config.subtasks.items():
            self.subtasks.append(SubtaskJobGroup(self._env, sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    jobs.append(
                        run_solution := RunSolution(self._env, solution, timeout, inp)
                    )
                    run_solution.add_prerequisite(compile)

                    if sub_num == "0":
                        c_out = inp.replace(".in", ".out")
                    else:
                        primary_sol = self._env.config.solutions[
                            self._env.config.primary_solution
                        ].source
                        c_out = util.get_output_name(inp, primary_sol)

                    out = util.get_output_name(inp, solution)
                    jobs.append(
                        run_judge := judge_job(
                            judge,
                            inp,
                            out,
                            c_out,
                            sub_num,
                            lambda: self._get_seed(inp),
                            None,
                            self._env,
                        )
                    )
                    self._outputs.append((out, run_judge))

                    run_judge.add_prerequisite(run_solution, name="run_solution")
                    testcases[inp] = (run_solution, run_judge)

                    used_inp.add(inp)
                    self.subtasks[-1].new_jobs.append(testcases[inp][1])
                    self.subtasks[-1].new_run_jobs.append(testcases[inp][0])
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp][1])

        return jobs

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
            exp_sub = expected[sub_job.num]
            (points, err), results = sub_job.result(self._env.config.fail_mode)
            if points is None:
                raise PipelineItemFailure(
                    f"Scoring on subtask {sub_job.num} failed:\n"
                    + tab(f"{err}:\n{tab(results[0 if exp_sub is None else exp_sub])}")
                )

            if exp_sub == 1 and points != 1:
                raise PipelineItemFailure(
                    f"Solution {self.solution} should have succeeded on subtask {sub_job.num}:\n"
                    + tab(results[1])
                )
            elif exp_sub == 0 and points != 0:
                raise PipelineItemFailure(
                    f"Solution {self.solution} should have failed on subtask {sub_job.num}:\n"
                    + tab(results[0])
                )

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
                result["outputs"][job.result.verdict].append(output)

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

    def _judge_verdicts(self, jobs: list[RunJudge]) -> list[Optional[Verdict]]:
        return list(
            map(lambda r: r.verdict if r is not None else None, self._job_results(jobs))
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

    @staticmethod
    def _to_points(job: RunJudge) -> float:
        res = job.result
        if res is None:
            raise RuntimeError(f"Job {job.name} has not finished yet.")
        return res.points

    @staticmethod
    def _finished(jobs: list[RunJudge]) -> list[RunJudge]:
        return list(filter(lambda j: j.state == State.succeeded, jobs))

    @staticmethod
    def _convert_to_points(jobs: list[RunJudge]) -> list[float]:
        return list(map(SubtaskJobGroup._to_points, SubtaskJobGroup._finished(jobs)))

    def definitive(self, expected_points: Optional[float]) -> bool:
        """
        Checks whether subtask jobs have resulted in outcome that cannot be changed.
        """
        if self._env.all_inputs:
            return False

        old_points = self._convert_to_points(self.previous_jobs)
        new_points = self._convert_to_points(self.new_jobs)
        all_points = old_points + new_points
        if len(all_points) == 0:
            return False

        if self._env.config.fail_mode == "all":
            if min(new_points, default=1) != max(new_points, default=1):
                return True  # Inconsistent on this subtasks
            if expected_points is not None:
                if min(all_points) < expected_points:
                    return True  # Points too low
                if min(new_points, default=expected_points) != expected_points:
                    return True  # Subtask cannot be as expected
                if (
                    self._env.skip_on_timeout
                    and Verdict.timeout in self._judge_verdicts(self.new_jobs)
                ):
                    return True
        else:
            if min(all_points) == 0:
                return True

        return False

    def result(
        self, fail_mode: str
    ) -> tuple[tuple[Optional[float], str], tuple[str, str]]:
        """
        Checks whether subtask jobs have resulted as expected and computes points.
        Returns (points, error msg), (best program output, worst program output)
        """
        prev_points = self._convert_to_points(self.previous_jobs)
        new_points = self._convert_to_points(self.new_jobs)

        # We need new first because we return first occurrence
        all_jobs = SubtaskJobGroup._finished(self.new_jobs + self.previous_jobs)
        all_points = new_points + prev_points
        result_msg = (
            self._job_msg(all_jobs[all_points.index(max(all_points))]),
            self._job_msg(all_jobs[all_points.index(min(all_points))]),
        )

        if len(all_points) == 0:
            return (1.0, ""), result_msg

        if fail_mode == "all" and self.num > 0:  # Don't check this on samples
            if max(new_points, default=1) != min(new_points, default=1):
                return (None, "Only some inputs were incorrect"), result_msg
            if min(new_points, default=1) > min(prev_points, default=1):
                return (None, "Previous subtask failed but this did not"), result_msg

        return (min(all_points), ""), result_msg

    def cancel(self):
        for job in self.new_run_jobs:
            job.cancel()

    def _job_msg(self, job: RunJudge) -> str:
        res = job.result
        inp = os.path.basename(job.input_name)
        out = os.path.basename(job.output_name)
        if res is None:
            raise RuntimeError(f"Job {job.name} has not finished yet.")
        judge = self._env.config.judge_type.capitalize()
        if res.verdict == Verdict.ok:
            head = f"{judge} accepted {out}"
        elif res.verdict == Verdict.wrong_answer:
            head = f"{judge} rejected {out}"
        elif res.verdict == Verdict.partial:
            head = f"{judge} partially accepted {out}"
        elif res.verdict == Verdict.error:
            head = f"Solution failed on input {inp}"
        elif res.verdict == Verdict.timeout:
            head = f"Solution did timeout on input {inp}"

        text = f"{head}:\n{tab(res.output)}"
        if res.diff != "":
            text += "\n" + tab(f"diff:\n{tab(res.diff)}")
        return text


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
            compile := Compile(self._env, solution, True, self._compile_args()),
            run_solution := RunSolution(
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


class RunSolution(ProgramJob):
    """Runs solution on given input."""

    def __init__(
        self,
        env: Env,
        solution: str,
        timeout: float,
        input_name: str,
        output_name: Optional[str] = None,
    ) -> None:
        name = RUN_JOB_NAME.replace(r"(.*)", solution, 1).replace(
            r"(.*)", input_name, 1
        )
        super().__init__(env, name, solution)
        self.input_name = self._data(input_name)
        self.output_name = (
            self._data(output_name)
            if output_name
            else self._output(self.input_name, solution)
        )
        self.timeout = timeout

    def _run_solution(self) -> RunResult:
        return self._run_program(
            [], stdin=self.input_name, stdout=self.output_name, timeout=self.timeout
        )

    def _run(self) -> Optional[RunResult]:
        result = self._run_solution()
        if result is None:
            return None
        return result
