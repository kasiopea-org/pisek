import os
from typing import List, Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, ProgramJob, Compile
from pisek.jobs.parts.judge import SolutionResult, RunJudge

# TODO: Samples

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks = []
        super().__init__(f"Solution {solution} Manager")

    def _get_jobs(self) -> List[Job]:
        solution = self._resolve_path(self.solution)

        jobs = [compile := Compile(solution, self._env.fork())]

        testcases = {}
        for inp in self._all_inputs():
            jobs.append(run_solution := RunSolution(solution, inp, self._env.fork()))
            run_solution.add_prerequisite(compile)
            
            jobs.append(run_judge := RunJudge(inp, os.path.basename(self._output(inp, solution)), self._env.fork()))
            run_judge.add_prerequisite(run_solution, name="run_solution")
            testcases[inp] = run_judge

        used_inp = set()
        for sub_num, sub in sorted(self._env.config.subtasks.items()):
            self.subtasks.append(SubtaskJobGroup(sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    used_inp.add(inp)
                    self.subtasks[-1].new_jobs.append(testcases[inp])
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp])

        return jobs

    def _get_status(self) -> str:
        return f"Testing {self.solution} " + "|".join(map(str, self.subtasks))

    def _evaluate(self) -> Any:
        total_points = 0
        for sub_jobs in self.subtasks:
            subtask = self._env.config.subtasks[sub_jobs.num]
            points, err = sub_jobs.result(self._env.config.fail_mode)
            if points is None:
                return self.fail(f"Scoring on subtask {subtask.num} failed:\n  " + err)
            total_points += subtask.score * points

        expected = util.get_expected_score(self.solution, self._env.config)
        if expected is not None and total_points != expected:
            return self.fail(f"Solution {self.solution} should have gotten {expected} but got {total_points} points.")

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

    def result(self, fail_mode) -> tuple[Optional[int], str]:
        prev_points = list(map(lambda x: x.points, self._job_results(self.previous_jobs)))
        new_points = list(map(lambda x: x.points, self._job_results(self.new_jobs)))
        if fail_mode == "all":
            if max(new_points) != min(new_points):
                return (None, "Only some inputs were not correct.")
            if len(prev_points) > 0 and min(prev_points) > max(prev_points):
                return (None, "Previous subtask failed but this did not.")

        return (min(prev_points + new_points), "")

class RunSolution(ProgramJob):
    def __init__(self, solution: str, input_name: str, env: Env) -> None:
        super().__init__(
            name=f"Run {solution} on input {input_name}",
            program=solution,
            env=env
        )
        self.input_name = self._data(input_name)

    def _run_solution(self) -> Optional[RunResult]:
        return self._run_program(
            [],
            stdin=self.input_name,
            stdout=self._output(self.input_name, self.program)
        )

    def _run(self) -> Optional[RunResult]:
        result = self._run_solution()
        if result is None:
            return
        return result
