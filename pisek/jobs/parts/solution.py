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

import os
from typing import Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.terminal import pad, tab, MSG_LEN
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, ProgramJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.judge import SolutionResult, judge_job, RunJudge

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks : list[SubtaskJobGroup] = []
        super().__init__(f"Solution {solution} Manager")

    def _get_jobs(self) -> list[Job]:
        solution = self._solution(self._env.config.solutions[self.solution].source)
        judge = self._executable(self._env.config.judge)

        jobs : list[Job] = []

        compile_args = {}
        if self._env.config.solution_manager:
            compile_args["manager"] = self._resolve_path(self._env.config.solution_manager)
        jobs.append(compile := Compile(self._env).init(solution, True, compile_args))

        timeout = None
        if self._env.timeout is not None:
            timeout = self._env.timeout
        elif not self._env.config.solutions[self.solution].primary and self._env.config.timeout_other_solutions:
            timeout = self._env.config.timeout_other_solutions
        elif self._env.config.timeout_model_solution:
            timeout = self._env.config.timeout_model_solution

        testcases = {}
        used_inp = set()
        for sub_num, sub in self._env.config.subtasks.items():
            self.subtasks.append(SubtaskJobGroup(sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    jobs.append(run_solution := RunSolution(self._env).init(solution, inp, timeout))
                    run_solution.add_prerequisite(compile)

                    if sub_num == "0":
                        c_out = inp.replace(".in", ".out")
                    else:
                        primary_sol = self._env.config.solutions[self._env.config.primary_solution].source
                        c_out = util.get_output_name(inp, primary_sol)
                    jobs.append(
                        run_judge := judge_job(
                            judge,
                            inp,
                            util.get_output_name(inp, solution),
                            c_out,
                            sub_num,
                            lambda: self._get_seed(inp),
                            None,
                            self._env
                        )
                    )

                    run_judge.add_prerequisite(run_solution, name="run_solution")
                    testcases[inp] = (run_solution, run_judge)

                    used_inp.add(inp)
                    self.subtasks[-1].new_jobs.append(testcases[inp][1])
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp][1])
                self.subtasks[-1].run_jobs.append(testcases[inp][0])

        return jobs

    def _update(self):
        for subtask in self.subtasks:
            if subtask.definitive(self._env.config.fail_mode):
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
                return self._fail(
                    f"Scoring on subtask {sub_job.num} failed:\n" +
                    tab(f"{err}:\n{tab(results[0 if exp_sub is None else exp_sub])}")
                )

            if exp_sub == 1 and points != 1:
                return self._fail(
                    f"Solution {self.solution} should have succeeded on subtask {sub_job.num}:\n" +
                    tab(results[1])
                )
            elif exp_sub == 0 and points != 0:
                return self._fail(
                    f"Solution {self.solution} should have failed on subtask {sub_job.num}:\n" +
                    tab(results[0])
                )

            total_points += subtask.score * points

        points = solution_conf.points
        above = solution_conf.points_above
        below = solution_conf.points_below

        if points is not None and total_points != points:
            return self._fail(f"Solution {self.solution} should have gotten {points} but got {total_points} points.")
        elif above is not None and total_points < above:
            return self._fail(f"Solution {self.solution} should have gotten at least {above} but got {total_points} points.")
        elif below is not None and total_points > below:
            return self._fail(f"Solution {self.solution} should have gotten at most {below} but got {total_points} points.")


class SubtaskJobGroup:
    """Groups jobs of a single subtask."""
    def __init__(self, num) -> None:
        self.num = int(num)
        self.run_jobs : list[RunSolution] = []
        self.previous_jobs : list[RunJudge] = []
        self.new_jobs : list[RunJudge] = []

    def _job_results(self, jobs: list[RunJudge]) -> list[Optional[SolutionResult]]:
        return list(map(lambda j: j.result, jobs))

    def __str__(self) -> str:
        s = "("
        previous = list(map(
            lambda x: x.verdict if x else None,
            self._job_results(self.previous_jobs)
        ))
        for verdict in Verdict:
            count = previous.count(verdict)
            if count > 0:
                s += f"{count}{RESULT_MARK[verdict]}"
        s += ") "
        if s == "() ":
            s = ""

        for job, result in zip(self.new_jobs, self._job_results(self.new_jobs)):
            if job.state == State.canceled:
                s += '-'
            elif result is None:
                s += ' '
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
    def _finished(jobs: list[Job]) -> list[Job]:
        return filter(lambda j: j.state == State.succeeded, jobs)

    @staticmethod
    def _convert_to_points(jobs: list[RunJudge]) -> list[float]:
        return list(map(SubtaskJobGroup._to_points, SubtaskJobGroup._finished(jobs)))

    def definitive(self, fail_mode: str) -> bool:
        """
        Checks whether subtask jobs have resulted in outcome that cannot be changed. 
        """
        old_points = self._convert_to_points(self.previous_jobs)
        new_points = self._convert_to_points(self.new_jobs)
        all_points = old_points + new_points
        if fail_mode == "all":
            if len(new_points) and min(new_points) != max(new_points):
                return True
        else:
            if len(all_points) and min(all_points) == 0:
                return True
        return False

    def result(self, fail_mode: str) -> tuple[tuple[Optional[float], str], tuple[str, str]]:
        """
        Checks whether subtask jobs have resulted as expected and computes points.
        Returns (points, error msg), (best program output, worst program output)
        """
        prev_points = self._convert_to_points(self.previous_jobs)
        new_points = self._convert_to_points(self.new_jobs)

        all_jobs = self.previous_jobs + self.new_jobs
        all_points = prev_points + new_points
        result_msg = (
            self._job_msg(all_jobs[all_points.index(max(all_points))]),
            self._job_msg(all_jobs[all_points.index(min(all_points))])
        )

        if len(new_points) == 0 and len(prev_points) == 0:
            return (1.0, ""), result_msg
        elif len(new_points) == 0:
            return (min(prev_points), ""), result_msg

        if fail_mode == "all" and self.num > 0:  # Don't check this on samples
            if max(new_points) != min(new_points):
                return (None, "Only some inputs were incorrect"), result_msg
            if len(prev_points) > 0 and min(new_points) > min(prev_points):
                return (None, "Previous subtask failed but this did not"), result_msg

        return (min(prev_points + new_points), ""), result_msg

    def cancel(self):
        for job in self.run_jobs:
            job.cancel()

    def _job_msg(self, job: RunJudge) -> str:
        res = job.result
        inp = os.path.basename(job.input_name)
        out = os.path.basename(job.output_name)
        if res is None:
            raise RuntimeError(f"Job {job.name} has not finished yet.")
        if res.verdict == Verdict.ok:
            head = f"Judge accepted {out}"
        elif res.verdict == Verdict.wrong_answer:
            head = f"Judge rejected {out}"
        elif res.verdict == Verdict.partial:
            head = f"Judge partially accepted {out}"
        elif res.verdict == Verdict.error:
            head = f"Solution {res.err_msg.lower()} on input {inp}"
        elif res.verdict == Verdict.timeout:
            head = f"Solution did timeout on input {inp}"

        return f"{head}:\n{tab(res.message)}"


RUN_JOB_NAME = r'Run (\w+) on input (\w+)'
class RunSolution(ProgramJob):
    """Runs solution on given input."""
    def _init(self, solution: str, input_name: str, timeout: Optional[float]) -> None:
        self.input_name = self._data(input_name)
        self.timeout = timeout
        name = RUN_JOB_NAME.replace(r'(\w+)', solution, 1).replace(r'(\w+)', input_name, 1)
        super()._init(name, solution)

    def _run_solution(self) -> Optional[RunResult]:
        return self._run_program(
            [],
            stdin=self.input_name,
            stdout=self._output(self.input_name, self.program),
            timeout=self.timeout
        )

    def _run(self) -> Optional[RunResult]:
        result = self._run_solution()
        if result is None:
            return None
        return result
