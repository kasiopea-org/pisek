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

from abc import abstractmethod
from dataclasses import dataclass
import random
from typing import Optional, Union, Callable
import yaml
import subprocess

from pisek.env import Env
from pisek.jobs.jobs import State, Job
from pisek.terminal import tab
from pisek.jobs.parts.task_job import TaskJobManager, RESULT_MARK, Verdict
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob
from pisek.jobs.parts.compile import Compile
from pisek.jobs.parts.chaos_monkey import Incomplete, ChaosMonkey
from pisek.jobs.parts.tools import Sanitize

DIFF_NAME = "diff.sh"

@dataclass
class SolutionResult():
    """Class representing result of a solution on given input."""
    verdict: Verdict
    points: float
    judge_stderr: str
    output: str = ""
    err_msg: str = ""

    def __str__(self):
        if self.verdict == Verdict.partial:
            return f"[{self.points:.2f}]"
        else:
            return RESULT_MARK[self.verdict]

def sol_result_representer(dumper, sol_result: SolutionResult):
    return dumper.represent_sequence(
        u'!SolutionResult', [sol_result.verdict.name, sol_result.points, sol_result.judge_stderr, sol_result.output, sol_result.err_msg]
    )

def sol_result_constructor(loader, value) -> SolutionResult:
    verdict, points, stderr, output, err_msg = loader.construct_sequence(value)
    return SolutionResult(Verdict[verdict], points, stderr, output, err_msg)

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
            
            JOBS = [(Incomplete, 5), (ChaosMonkey, 20)]

            total = sum(map(lambda x: x[1], JOBS))
            random.seed(4)  # Reproducibility!
            seeds = random.sample(range(0, 16**4), total)

            for job, times in JOBS:
                for i in range(times):
                    seed = seeds.pop()
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

class RunKasiopeaJudgeMan(TaskJobManager):
    def __init__(self, subtask: int, seed: int, input_: str, output: str, correct_output: str):
        self._subtask = subtask
        self._seed = seed
        self._input = input_
        self._output = output
        self._correct_output = correct_output
        super().__init__("Running judge")

    def _get_jobs(self) -> list[Job]:
        judge_program = self._resolve_path(self._env.config.judge)
        clean_output = self._output + ".clean"

        jobs : list[Job] = [
            sanitize := Sanitize(self._env).init(self._output, clean_output),
            judge := judge_job(
                judge_program,
                self._input,
                clean_output,
                self._correct_output,
                self._subtask,
                lambda: f"{self._seed:x}",
                None,
                self._env
            )
        ]
        judge.add_prerequisite(sanitize)
        if self._env.config.judge_type != "diff":
            jobs.insert(0, compile := Compile(self._env).init(judge_program))
            judge.add_prerequisite(compile)

        self._judge_job = judge

        return jobs

    def judge_result(self) -> SolutionResult:
        if self.state != State.succeeded:
            raise RuntimeError(f"Judging hasn't successfully finished.")
        elif not isinstance(self._judge_job.result, SolutionResult):
            raise RuntimeError(f"Judging result invalid.")
        return self._judge_job.result
    

JUDGE_JOB_NAME = r'Judge (\w+)'
class RunJudge(ProgramJob):
    """Runs judge on single input. (Abstract class)"""
    def _init(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 expected_points: Optional[float]) -> None:
        self.input_name = self._data(input_name)
        self.output_name = self._data(output_name)
        self.correct_output_name = self._data(correct_output)
        self.expected_points = expected_points
        super()._init(JUDGE_JOB_NAME.replace(r'(\w+)', output_name, 1), judge)

    @abstractmethod
    def _judge(self) -> Optional[SolutionResult]:
        pass

    def _run(self) -> Optional[SolutionResult]:
        if "run_solution" in self.prerequisites_results:
            solution_res: RunResult = self.prerequisites_results["run_solution"]
            if solution_res.kind == RunResultKind.OK:
                result = self._judge()
            elif solution_res.kind == RunResultKind.RUNTIME_ERROR:
                result = SolutionResult(Verdict.error, 0.0, "", self._quote_program(solution_res), solution_res.err_msg)
            elif solution_res.kind == RunResultKind.TIMEOUT:
                result = SolutionResult(Verdict.timeout, 0.0, "", self._quote_program(solution_res))
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
        self._access_file(self.output_name)
        self._access_file(self.correct_output_name)
        diff = subprocess.run(
            ["diff", "-Bpq", self.output_name, self.correct_output_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # XXX: Okay, it didn't finish in no time, but this is not meant to be used
        rr = RunResult(RunResultKind.OK, diff.returncode, 0, 0, stderr_text=diff.stderr)
        if diff.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0, "", self._quote_program(rr))
        elif diff.returncode == 1:
            return SolutionResult(Verdict.wrong_answer, 0.0, "", self._quote_program(rr))
        else:
            return self._fail(f"Diff failed:\n{tab(diff.stderr)}")

class RunKasiopeaJudge(RunJudge):
    def _init(self, judge: str, input_name: str, output_name: str, correct_output: str,
                 subtask: int, seed: str, expected_points: Optional[float]) -> None:
        self.subtask = subtask
        self.seed = seed
        super()._init(judge, input_name, output_name, correct_output, expected_points)

    def _judge(self) -> Optional[SolutionResult]:
        envs = {}
        if self._env.config.judge_needs_in:
            envs["TEST_INPUT"] = self.input_name
            self._access_file(self.input_name)
        if self._env.config.judge_needs_out:
            envs["TEST_OUTPUT"] = self.correct_output_name
            self._access_file(self.correct_output_name)

        result = self._run_program(
            [str(self.subtask), self.seed],
            stdin=self.output_name,
            env=envs,
        )
        if result is None:
            return None
        if result.returncode == 0:
            return SolutionResult(Verdict.ok, 1.0, result.raw_stderr(), self._quote_program(result))
        elif result.returncode == 1:
            return SolutionResult(Verdict.wrong_answer, 0.0, result.raw_stderr(), self._quote_program(result))
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
                return SolutionResult(Verdict.wrong_answer, 0.0, result.raw_stderr(), msg)
            elif points == 1:
                return SolutionResult(Verdict.ok, 1.0, result.raw_stderr(), msg)
            else:
                return SolutionResult(Verdict.partial, points, result.raw_stderr(), msg)
        else:
            return self._program_fail(f"Judge failed on output {self.output_name}:", result)


def judge_job(judge: str, input_name: str, output_name: str, correct_ouput: str, subtask: int, get_seed: Callable[[], str],
              expected_points : Optional[float], env: Env) -> Union[RunDiffJudge, RunKasiopeaJudge, RunCMSJudge]:
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
