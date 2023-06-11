import os
from typing import List, Any

from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, RunResult, Verdict
from pisek.jobs.parts.program import ProgramJob, Compile
from pisek.jobs.parts.judge import RunJudge

class SolutionManager(TaskJobManager):
    def __init__(self, solution: str):
        self.solution = solution
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
        self.subtasks = []
        for _, sub in sorted(self._env.config.subtasks.items()):
            self.subtasks.append(SubtaskJobGroup())
            for inp in self._subtask_inputs(sub):
                if inp not in used_inp:
                    used_inp.add(inp)
                    self.subtasks[-1].new_jobs.append(testcases[inp])
                else:
                    self.subtasks[-1].previous_jobs.append(testcases[inp])

        return jobs

    def _get_status(self) -> str:
        return f"Testing {self.solution} " + "|".join(map(str, self.subtasks))


class SubtaskJobGroup:
    def __init__(self):
        self.previous_jobs = []
        self.new_jobs = []
    
    def _job_results(self, jobs: List[Job]) -> List[Any]:
        return list(map(lambda j: j.result, jobs))
    
    def __str__(self):
        s = "("
        previous = self._job_results(self.previous_jobs)
        for result in Verdict:
            count = previous.count(result)
            if count > 0:
                s += f"{count}{RESULT_MARK[result]}"
        s += ")"
        if s == "()":
            s = ""
 
        for result in self._job_results(self.new_jobs):
            if result is None:
                s += ' '
            else:
                s += str(result)

        return s


class RunSolution(ProgramJob):
    def __init__(self, solution: str, input_name: str, env: Env):
        super().__init__(
            name=f"Run {solution} on input {input_name}",
            program=solution,
            env=env
        )
        self.input_name = self._data(input_name)

    def _run_solution(self) -> RunResult:
        # TODO: timeout
        return self._run_program(
            [],
            stdin=self.input_name,
            stdout=self._output(self.input_name, self.program)
        ).returncode == 0

    def _run(self) -> str:
        if self._run_solution():
            return RunResult.ok
        else:
            return RunResult.error
