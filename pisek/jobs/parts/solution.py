import os
from typing import List, Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.status import pad, tab, MSG_LEN
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, ProgramJob, Compile
from pisek.jobs.parts.judge import judge_job, RunJudge

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks = []
        super().__init__(f"Solution {solution} Manager")
        self.primary = False

    def _get_jobs(self) -> List[Job]:
        # WATCH OUT: To avoid unnecessary dependencies there are multiple env in this section.
        # If you use the wrong one caching bugs will arise.
        solution_env = self._env.fork()
        solution = self._solution(self._env.config.solutions[self.solution].name)

        judge_env = self._env.fork()
        judge = self._executable(judge_env.config.judge)
        
        jobs = []
        
        compile_args = {}
        if self._env.config.solution_manager:
            compile_args["manager"] = self._resolve_path(self._env.config.solution_manager)
        jobs.append(compile := Compile(solution, self._env.fork(), compile_args))

        timeout = None
        if not self.primary and solution_env.config.timeout_other_solutions:
            timeout = solution_env.config.timeout_other_solutions
        elif solution_env.config.timeout_model_solution:
            timeout = solution_env.config.timeout_model_solution

        testcases = {}
        used_inp = set()
        subtasks = list(zip(
            solution_env.iterate("config.subtasks", self._env),
            judge_env.iterate("config.subtasks", judge_env)
        ))  # Yes we really need to do it like this.

        for (sub_num, sub, sol_env), (_, sub2, jud_env) in subtasks:
            self.subtasks.append(SubtaskJobGroup(sub_num))
            for inp in self._subtask_inputs(sub):
                self._subtask_inputs(sub2) # Yes it also depends on this
                if inp not in used_inp:
                    jobs.append(run_solution := RunSolution(solution, inp, timeout, sol_env.fork()))
                    run_solution.add_prerequisite(compile)

                    if sub_num == "0":
                        c_out = inp.replace(".in", ".out")
                    else:
                        primary_sol = jud_env.config.solutions[jud_env.config.primary_solution].name
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
                            jud_env.fork()
                        )
                    )
 
                    run_judge.add_prerequisite(run_solution, name="run_solution")
                    testcases[inp] = run_judge
                    
                    used_inp.add(inp)
                    self.subtasks[-1].new_jobs.append(testcases[inp])
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp])

        return jobs

    def _get_status(self) -> str:
        msg = f"Testing {self.solution} "
        if self.state == State.canceled:
            return self._job_bar(msg)
        return pad(msg, MSG_LEN) + "|".join(map(str, self.subtasks))

    def _evaluate(self) -> Any:
        total_points = 0
        solution_conf = self._env.config.solutions[self.solution]
        expected = solution_conf.subtasks
        for sub_job in self.subtasks:
            subtask = self._env.config.subtasks[sub_job.num]
            exp_sub = expected[sub_job.num]
            (points, err), results = sub_job.result(self._env.config.fail_mode)
            if points is None:
                return self.fail(
                    f"Scoring on subtask {sub_job.num} failed:\n" +
                    tab(f"{err}:\n{tab(results[0 if exp_sub is None else exp_sub])}")
                )

            if exp_sub == 1 and points != 1:
                return self.fail(
                    f"Solution {self.solution} should have succeeded on subtask {sub_job.num}:\n" +
                    tab(results[1])
                )
            elif exp_sub == 0 and points != 0:
                return self.fail(
                    f"Solution {self.solution} should have failed on subtask {sub_job.num}:\n" +
                    tab(results[0])
                )

            total_points += subtask.score * points

        points = solution_conf.points
        above = solution_conf.points_above
        below = solution_conf.points_below

        if points is not None and total_points != points:
            return self.fail(f"Solution {self.solution} should have gotten {points} but got {total_points} points.")
        elif above is not None and total_points < above:
            return self.fail(f"Solution {self.solution} should have gotten at least {above} but got {total_points} points.")
        elif below is not None and total_points > below:
            return self.fail(f"Solution {self.solution} should have gotten at most {above} but got {total_points} points.")


class PrimarySolutionManager(SolutionManager):
    def __init__(self, solution: str):
        super().__init__(solution)
        self.primary = True

class SubtaskJobGroup:
    def __init__(self, num) -> None:
        self.num = int(num)
        self.previous_jobs = []
        self.new_jobs = []

    def _job_results(self, jobs: List[Job]) -> List[Optional[Verdict]]:
        return list(map(lambda j: j.result, jobs))

    def __str__(self) -> str:
        s = "("
        previous = list(map(
            lambda x: x.verdict if x else None,
            self._job_results(self.previous_jobs)
        ))
        for result in Verdict:
            count = previous.count(result)
            if count > 0:
                s += f"{count}{RESULT_MARK[result]}"
        s += ") "
        if s == "() ":
            s = ""

        for result in self._job_results(self.new_jobs):
            if result is None:
                s += ' '
            else:
                s += str(result)

        return s

    def result(self, fail_mode) -> tuple[tuple[Optional[int], str], tuple[str]]:
        prev_points = list(map(lambda x: x.points, self._job_results(self.previous_jobs)))
        new_points = list(map(lambda x: x.points, self._job_results(self.new_jobs)))
        
        all_jobs = self.previous_jobs + self.new_jobs
        all_points = prev_points + new_points
        result_msg = tuple(self._job_msg(all_jobs[all_points.index(fn(all_points))]) for fn in (max, min))

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

    def _job_msg(self, job: RunJudge) -> str:
        res = job.result
        inp = os.path.basename(job.input_name)
        out = os.path.basename(job.output_name)
        if res.verdict == Verdict.ok:
            head = f"Judge accepted {out}"
        elif res.verdict == Verdict.wrong_answer:
            head = f"Judge rejected {out}"
        elif res.verdict == Verdict.partial:
            head = f"Judge partially accepted {out}"
        elif res.verdict == Verdict.error:
            head = f"Solution ended with errors on input {inp}"
        elif res.verdict == Verdict.timeout:
            head = f"Solution did timeout on input {inp}"

        return f"{head}:\n{tab(res.message)}"

class RunSolution(ProgramJob):
    def __init__(self, solution: str, input_name: str, timeout: Optional[float], env: Env) -> None:
        super().__init__(
            name=f"Run {solution} on input {input_name}",
            program=solution,
            env=env
        )
        self.input_name = self._data(input_name)
        self.timeout = timeout

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
            return
        return result
