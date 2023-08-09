from abc import abstractmethod
from dataclasses import dataclass
import random
from typing import Optional, Union, Callable
import yaml
import subprocess

import pisek.util as util
from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.jobs.status import tab
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.chaos_monkey import Incomplete, ChaosMonkey

DIFF_NAME = "diff.sh"

@dataclass
class SolutionResult():
    """Class representing result of a solution on given input."""
    verdict: Verdict
    points: float
    message: str = ""

    def __str__(self):
        if self.verdict == Verdict.partial:
            return f"[{self.points:.2f}]"
        else:
            return RESULT_MARK[self.verdict]

def sol_result_representer(dumper, sol_result: SolutionResult):
    return dumper.represent_sequence(
        u'!SolutionResult', [sol_result.verdict.name, sol_result.points, sol_result.message]
    )

def sol_result_constructor(loader, value) -> SolutionResult:
    verdict, points, message = loader.construct_sequence(value)
    return SolutionResult(Verdict[verdict], points, message)

yaml.add_representer(SolutionResult, sol_result_representer)
yaml.add_constructor(u'!SolutionResult', sol_result_constructor)


class JudgeManager(TaskJobManager):
    def __init__(self):
        super().__init__("Preparing judge")

    def _get_jobs(self) -> list[Job]:
        jobs : list[Job] = []
        if self._env.config.judge_type != "diff":
            jobs.append(comp := Compile(self._env).init(self._resolve_path(self._env.config.judge)))

        samples = self._get_samples()
        if samples is None:
            return []

        for inp, out in samples:
            jobs.append(judge := judge_job(self._env.config.judge, inp, out, out, 0, lambda: "0", 1.0, self._env))
            if self._env.config.judge_type != "diff":
                judge.add_prerequisite(comp)
            for job, times in [(Incomplete, 2), (ChaosMonkey, 20)]:
                random.seed(4)  # Reproducibility!
                seeds = random.sample(range(0, 16**4), times)
                for seed in seeds:
                    inv_out = out.replace(".out", f".{seed:x}.invalid")
                    jobs += [
                        invalidate := job(self._env).init(out, inv_out, seed),
                        run_judge := judge_job(self._env.config.judge, inp, inv_out, out,
                                               0, lambda: "0", None, self._env)
                    ]
                    if self._env.config.judge_type != "diff":
                        run_judge.add_prerequisite(comp)
                    run_judge.add_prerequisite(invalidate)
        return jobs


class RunJudge(ProgramJob):
    """Runs judge on single input. (Abstract class)"""
    def _init(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 expected_points: Optional[float]) -> None:
        self.input_name = self._data(input_name)
        self.output_name = self._data(output_name)
        self.correct_output_name = self._data(correct_output)
        self.expected_points = expected_points
        super()._init(f"Judge {output_name}", judge)

    @abstractmethod
    def _judge(self) -> Optional[SolutionResult]:
        pass

    def _run(self) -> Optional[SolutionResult]:
        if "run_solution" in self.prerequisites_results:
            solution_res = self.prerequisites_results["run_solution"]
            if solution_res.kind == RunResultKind.OK:
                result = self._judge()
            elif solution_res.kind == RunResultKind.RUNTIME_ERROR:
                result = SolutionResult(Verdict.error, 0.0, self._quote_program(solution_res))
            elif solution_res.kind == RunResultKind.TIMEOUT:
                result = SolutionResult(Verdict.timeout, 0.0, self._quote_program(solution_res))
        else:
            result = self._judge()

        if self.expected_points is not None and result is not None and \
                result.points != self.expected_points:
            self._fail(
                f"Output {self.output_name} for input {self.input_name} "
                f"should have got {self.expected_points} points but got {result.points} points."
            )
            return None
        return result


class RunDiffJudge(RunJudge):
    def _init(self, judge: str, input_name: str, output_name: str,
              correct_output: str, expected_points: Optional[float]) -> None:
        super()._init(judge, input_name, output_name, correct_output, expected_points)

    def _judge(self) -> Optional[SolutionResult]:
        diff = subprocess.run(
            ["diff", "-Bpq", self.output_name, self.correct_output_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        rr = RunResult(RunResultKind.OK, diff.returncode, stderr_text=diff.stderr)
        if diff.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0, self._quote_program(rr))
        elif diff.returncode == 1:
            return SolutionResult(Verdict.wrong_answer, 0.0, self._quote_program(rr))
        else:
            return self._fail(f"Diff failed:\n{tab(diff.stderr)}")

class RunKasiopeaJudge(RunJudge):
    def _init(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 subtask: int, seed: str, expected_points: Optional[float]) -> None:
        self.subtask = subtask
        self.seed = seed
        super()._init(judge, input_name, output_name, correct_output, expected_points)

    def _judge(self) -> Optional[SolutionResult]:
        self._access_file(self.input_name)
        self._access_file(self.correct_output_name)
        result = self._run_program(
            [str(self.subtask), self.seed],
            stdin=self.output_name,
            env={"TEST_INPUT": self.input_name, "TEST_OUTPUT": self.correct_output_name},
        )
        if result is None:
            return None
        if result.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0, self._quote_program(result))
        elif result.returncode == 1:
            return SolutionResult(Verdict.wrong_answer, 0.0, self._quote_program(result))
        else:
            return self._program_fail(f"Judge failed on output {self.output_name}:", result)


class RunCMSJudge(RunJudge):
    def _init(self, judge: str, input_name: str, output_name: str,
              correct_output: str, expected_points: Optional[float]) -> None:
        super()._init(judge, input_name, output_name, correct_output, expected_points)

    def _judge(self) -> Optional[SolutionResult]:
        self._access_file(self.input_name)
        self._access_file(self.output_name)
        self._access_file(self.correct_output_name)
        points_file = self.output_name.replace(".out", ".judge")
        self._access_file(points_file)
        result = self._run_program(
            [self.input_name, self.correct_output_name, self.output_name],
            stdout=points_file
        )
        if result is None:
            return None
        if result.returncode == 0:
            points_str = result.raw_stdout().split('\n')[0]
            msg = result.raw_stderr().split('\n')[0]
            try:
                points = float(points_str)
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
    """Returns JudgeJob according to contest type."""
    if env.config.judge_type == "diff":
        return RunDiffJudge(env).init(
            judge,
            input_name,
            output_name,
            correct_ouput,
            expected_points
        )
    elif env.config.contest_type == "cms":
        return RunCMSJudge(env).init(
            judge,
            input_name,
            output_name,
            correct_ouput,
            expected_points
        )
    else:
        return RunKasiopeaJudge(env).init(
            judge,
            input_name,
            output_name,
            correct_ouput,
            subtask,
            get_seed(),
            expected_points
        )
