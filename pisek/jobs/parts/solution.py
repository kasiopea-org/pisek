import os
from typing import List, Any, Optional

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.status import pad, MSG_LEN
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, ProgramJob, Compile
from pisek.jobs.parts.judge import SolutionResult, RunKasiopeaJudge, RunCMSJudge

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
        self.subtasks = []
        super().__init__(f"Solution {solution} Manager")

    def _get_jobs(self) -> List[Job]:
        solution = self._resolve_path(self.solution)

        jobs = [compile := Compile(solution, self._env.fork())]

        testcases = {}
        used_inp = set()
        for sub_num, sub in sorted(self._env.config.subtasks.items()):
            self.subtasks.append(SubtaskJobGroup(sub_num))
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    jobs.append(run_solution := RunSolution(solution, inp, self._env.fork()))
                    run_solution.add_prerequisite(compile)

                    env = self._env.fork()
                    if env.config.contest_type == "cms":
                        jobs.append(
                            run_judge := RunCMSJudge(
                                inp,
                                os.path.basename(self._output(inp, solution)),
                                env
                        ))
                    else:
                        jobs.append(
                            run_judge := RunKasiopeaJudge(
                                inp,
                                os.path.basename(self._output(inp, solution)),
                                sub_num,
                                self._get_seed(inp),
                                env
                        ))
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
            points, err = sub_job.result(self._env.config.fail_mode)
            if points is None:
                return self.fail(f"Scoring on subtask {sub_job.num} failed:\n  " + err)
            elif sub_job.num == 0 and points == 0 and expected == self._env.config.get_maximum_score():
                return self.fail(f"Solution {self.solution} should have passed all inputs but failed on samples.")
            total_points += subtask.score * points

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
        
        if len(new_points) == 0 and len(prev_points) == 0:
            return (1.0, "")
        elif len(new_points) == 0:
            return (min(prev_points), "")

        if fail_mode == "all" and self.num > 0:  # Don't check this on samples 
            if max(new_points) != min(new_points):
                return (None, "Only some inputs were not correct.")
            if len(prev_points) > 0 and min(new_points) > min(prev_points):
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
