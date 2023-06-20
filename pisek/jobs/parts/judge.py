from dataclasses import dataclass
import random
from typing import Optional, Union, Callable
import yaml

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.jobs.status import tab
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob, Compile
from pisek.jobs.parts.chaos_monkey import Incomplete, ChaosMonkey

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
        super().__init__("Preparing judge")

    def _get_jobs(self) -> list[Job]:
        jobs = []
        if self._env.config.judge_type == "diff":
            jobs = []
            
            if self._env.config.contest_type == "cms":
                jobs.append(build := BuildCMSDiff(self._env.fork()))
            else:
                jobs.append(build := BuildKasiopeaDiff(self._env.fork()))
            
            jobs.append(comp := Compile(self._executable(DIFF_NAME), self._env.fork())) 
            comp.add_prerequisite(build)
        else:
            jobs = [
                Compile(self._resolve_path(self._env.config.judge), self._env.fork()) 
            ]

        samples = self._get_samples()
        if samples is None:
            return []

        for inp, out in samples:
            jobs.append(judge_job(self._env.config.judge, inp, out, out, 0, lambda: "0", 1.0, self._env.fork()))

            for job, times in [(Incomplete, 2), (ChaosMonkey, 20)]:
                random.seed(4)  # Reproducibility!
                seeds = random.sample(range(0, 16**4), times)
                for seed in seeds:
                    inv_out = out.replace(".out", f".{seed:x}.invalid")
                    jobs += [
                        invalidate := job(out, inv_out, seed, self._env.fork()),
                        run_judge := judge_job(self._env.config.judge, inp, inv_out, out,
                                               0, lambda: "0", None, self._env.fork())
                    ]
                    run_judge.add_prerequisite(invalidate)
        return jobs


class BuildDiffJudge(TaskJob):
    def __init__(self, env: Env) -> None:
        super().__init__("Build WhiteDiffJudge", env)

class BuildKasiopeaDiff(BuildDiffJudge):
    def _run(self):
        with self._open_file(self._executable(DIFF_NAME), "w") as f:
            f.write(
                '#!/bin/bash\n'
                'if [ "$(diff -Bbq "$TEST_OUTPUT" -)" ]; then\n'
                '   exit 1\n'
                'fi\n'
            )

class BuildCMSDiff(BuildDiffJudge):
    def _run(self):
        with self._open_file(self._executable(DIFF_NAME), "w") as f:
            f.write(
                '#!/bin/bash\n'
                'if [ "$(diff -Bbq "$2" "$3")" ]; then\n'
                '   echo 0\n'
                'else\n'
                '   echo 1\n'
                'fi\n'
            )

class RunJudge(ProgramJob):
    def __init__(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 expected_points: Optional[float], env: Env) -> None:
        super().__init__(
            name=f"Judge {output_name}",
            program=judge,
            env=env
        )
        self.input_name = self._data(input_name)
        self.output_name = self._data(output_name)
        self.correct_output_name = self._data(correct_output)
        self.expected_points = expected_points

    def _run(self) -> Optional[SolutionResult]:
        if "run_solution" in self.prerequisites_results:
            solution_res = self.prerequisites_results["run_solution"]
            if solution_res.kind == RunResultKind.OK:
                result = self._judge()
            elif solution_res.kind == RunResultKind.RUNTIME_ERROR:
                result = SolutionResult(Verdict.error, 0.0)
            elif solution_res.kind == RunResultKind.TIMEOUT:
                result = SolutionResult(Verdict.timeout, 0.0)
        else:
            result = self._judge()

        if self.expected_points is not None and result is not None and \
                result.points != self.expected_points:
            return self.fail(
                f"Output {self.output_name} for input {self.input_name} "
                f"should have got {self.expected_points} points but got {result.points} points."
            )
        return result


class RunKasiopeaJudge(RunJudge):
    def __init__(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 subtask: int, seed: str, expected_points: Optional[float], env: Env) -> None:
        self.subtask = subtask
        self.seed = seed
        super().__init__(judge, input_name, output_name, correct_output, expected_points, env)

    def _judge(self) -> Optional[RunResult]:
        self._access_file(self.input_name)
        self._access_file(self.correct_output_name)
        result = self._run_program(
            [str(self.subtask), self.seed],
            stdin=self.output_name,
            env={"TEST_INPUT": self.input_name, "TEST_OUTPUT": self.correct_output_name},
        )
        if result is None:
            return
        if result.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0)
        elif result.returncode == 1:
            return SolutionResult(Verdict.wrong_answer, 0.0)
        else:
            return self._program_fail(f"Judge failed on output {self.output_name}:", result)


class RunCMSJudge(RunJudge):
    def __init__(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 expected_points: Optional[float], env: Env) -> None:
        super().__init__(judge, input_name, output_name, correct_output, expected_points, env)

    def _judge(self) -> Optional[RunResult]:
        self._access_file(self.input_name)
        self._access_file(self.output_name)
        self._access_file(self.correct_output_name)
        result = self._run_program(
            [self.input_name, self.correct_output_name, self.output_name]
        )
        if result is None:
            return
        if result.returncode == 0:
            points = result.stdout.split('\n')[0]
            msg = result.stderr.split('\n')[0]
            try:
                points = float(points)
            except ValueError:
                return self._program_fail("Judge wrote didn't write points on stdout:", result)

            if not 0 <= points <= 1:
                return self._program_fail("Judge must give between 0 and 1 points:", result)

            if points == 0:
                return SolutionResult(Verdict.wrong_answer, 0.0, msg)
            elif points == 1:
                return SolutionResult(Verdict.ok, 1.0, msg)
            else:
                return SolutionResult(Verdict.partial, points, msg)
        else:
            return self._program_fail(f"Judge failed on output {self.output_name}:", result)


def judge_job(judge: str, input_name: str, output_name: str, correct_ouput: str, subtask: int, get_seed: Callable[[], str],
              expected_points : Optional[float], env: Env) -> Union[RunKasiopeaJudge, RunCMSJudge]:
    if env.config.contest_type == "cms":
        return RunCMSJudge(
            judge,
            input_name,
            output_name,
            correct_ouput,
            expected_points,
            env
        )
    else:
        return RunKasiopeaJudge(
            judge,
            input_name,
            output_name,
            correct_ouput,
            str(subtask),
            get_seed(),
            expected_points,
            env
        )
