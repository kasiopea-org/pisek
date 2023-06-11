from dataclasses import dataclass
from typing import List
import yaml

from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, RunResult, Verdict
from pisek.jobs.parts.program import ProgramJob, Compile

from pisek.generator import OnlineGenerator

DIFF_NAME = "diff.sh"

@dataclass
class SolutionResult(yaml.YAMLObject):
    yaml_tag = u'!SolutionResult'
    verdict: str
    points: float
    message: str = ""

    def __str__(self):
        if self.verdict == Verdict.partial:
            return f"[{self.points:.2f}]"
        else:
            return RESULT_MARK[self.verdict]


class JudgeManager(TaskJobManager):
    def __init__(self):
        super().__init__("Judge Manager")

    def _get_jobs(self) -> List[Job]:
        jobs = []
        if self._env.config.judge_type == "diff":
            jobs = [
                build := BuildDiffJudge(self._env.fork()),
                comp := Compile(self._executable(DIFF_NAME), self._env.fork()) 
            ]
            comp.add_prerequisite(build)
        else:
            jobs = [
                Compile(self._resolve_path(self._env.config.judge), self._env.fork()) 
            ]

        return jobs

class BuildDiffJudge(TaskJob):
    def __init__(self, env: Env) -> None:
        super().__init__("Build WhiteDiffJudge", env)

    def _run(self):
        with self._open_file(self._executable(DIFF_NAME), "w") as f:
            f.write(
                '#!/bin/bash\n'
                'if [ "$(diff -Bbq $TEST_OUTPUT -)" ]; then\n'
                '   exit 1\n'
                'fi\n'
            )

class RunJudge(ProgramJob):
    def __init__(self, input_name: str, output_name: str, env: Env):
        super().__init__(
            name=f"Judge {output_name}",
            program=env.config.judge,
            env=env
        )
        self.input_name = self._data(input_name)
        self.output_name = self._data(output_name)
        self.correct_output_name = self._output(input_name, env.config.first_solution)

    def _judge(self):
        self._access_file(self.input_name)
        self._access_file(self.correct_output_name)
        return self._run_program(
            [],
            stdin=self.output_name,
            env={"TEST_INPUT": self.input_name, "TEST_OUTPUT": self.correct_output_name},
        )

    def _run(self):
        solution_res = self.prerequisites_results["run_solution"]
        if solution_res == RunResult.ok:
            judge_result = self._judge()
            if judge_result.returncode == 0:
                return SolutionResult(Verdict.ok, 1.0)
            elif judge_result.returncode == 1:
                return SolutionResult(Verdict.wrong_answer, 0.0)
            else:
                return self.fail(
                    f"Judge {self.program} failed on output {self.output_name} "
                    f"with code {judge_result.returncode}."
                )
        elif solution_res == RunResult.error:
            return SolutionResult(Verdict.error, 0.0)
        elif solution_res == RunResult.timeout:
            return SolutionResult(Verdict.timeout, 0.0)
