import os
from typing import List, Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.status import pad, MSG_LEN
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, ProgramJob, Compile
from pisek.jobs.parts.judge import judge_job

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks = []
        super().__init__(f"Solution {solution} Manager")
        self.primary = False

    def _get_jobs(self) -> List[Job]:
        solution = self._solution(self.solution)

        judge_env = self._env.fork()
        judge = self._executable(judge_env.config.judge)
        
        timeout = None
        if not self.primary and self._env.config.timeout_other_solutions:
            timeout = self._env.config.timeout_other_solutions
        elif self._env.config.timeout_model_solution:
            timeout = self._env.config.timeout_model_solution

        jobs = []
        
        compile_args = {}
        if self._env.config.solution_manager:
            compile_args["manager"] = self._resolve_path(self._env.config.solution_manager)
        jobs.append(compile := Compile(solution, self._env.fork(), compile_args))

        testcases = {}
        used_inp = set()
        judge_env.config.subtasks  # We need to access it
        for sub_num, sub in sorted(self._env.config.subtasks.items()):

            self.subtasks.append(SubtaskJobGroup(sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    jobs.append(run_solution := RunSolution(solution, inp, timeout, self._env.fork()))
                    run_solution.add_prerequisite(compile)

                    if sub_num == 0:
                        c_out = inp.replace(".in", ".out")
                    else:
                        c_out =  util.get_output_name(inp, judge_env.config.primary_solution)
                    jobs.append(
                        run_judge := judge_job(
                            judge,
                            inp,
                            os.path.basename(self._output(inp, solution)),
                            c_out,
                            sub_num,
                            lambda: self._get_seed(inp),
                            None,
                            judge_env.fork()
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
        return  pad(msg, MSG_LEN) + "|".join(map(str, self.subtasks))

    def _evaluate(self) -> Any:
        total_points = 0
        expected = util.get_expected_score(self.solution, self._env.config)
        for sub_job in self.subtasks:
            subtask = self._env.config.subtasks[sub_job.num]
            points, err = sub_job.result(self._env.config.solution_fail_mode)
            if points is None:
                return self.fail(f"Scoring on subtask {sub_job.num} failed:\n  " + err)
            elif sub_job.num == 0 and points == 0 and expected == self._env.config.get_maximum_score():
                return self.fail(f"Solution {self.solution} should have passed all inputs but failed on samples.")
            total_points += subtask.score * points

        if expected is not None and total_points != expected:
            return self.fail(f"Solution {self.solution} should have gotten {expected} but got {total_points} points.")


class PrimarySolutionManager(SolutionManager):
    def __init__(self, solution: str):
        super().__init__(solution)
        self.primary = True

class SubtaskJobGroup:
    def __init__(self, num) -> None:
        self.num = num
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

    def result(self, solution_fail_mode) -> tuple[Optional[int], str]:
        prev_points = list(map(lambda x: x.points, self._job_results(self.previous_jobs)))
        new_points = list(map(lambda x: x.points, self._job_results(self.new_jobs)))
        
        if len(new_points) == 0 and len(prev_points) == 0:
            return (1.0, "")
        elif len(new_points) == 0:
            return (min(prev_points), "")

        if solution_fail_mode == "all" and self.num > 0:  # Don't check this on samples 
            if max(new_points) != min(new_points):
                return (None, "Only some inputs were not correct.")
            if len(prev_points) > 0 and min(new_points) > min(prev_points):
                return (None, "Previous subtask failed but this did not.")

        return (min(prev_points + new_points), "")

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
