# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from decimal import Decimal
from typing import Any, Optional

from pisek.jobs.jobs import State, Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.config.config_types import TaskType, Scoring
from pisek.utils.text import pad, pad_left, tab
from pisek.utils.colors import ColorSettings
from pisek.utils.terminal import MSG_LEN, right_aligned_text
from pisek.task_jobs.solution.verdicts_eval import evaluate_verdicts
from pisek.task_jobs.task_job import TaskHelper
from pisek.task_jobs.task_manager import TaskJobManager
from pisek.task_jobs.compile import Compile
from pisek.task_jobs.generator.input_info import InputInfo
from pisek.task_jobs.generator.manager import InputsInfoMixin
from pisek.task_jobs.solution.solution_result import Verdict, SolutionResult
from pisek.task_jobs.judge import judge_job, RunJudge, RunCMSJudge, RunBatchJudge
from pisek.task_jobs.solution.solution import (
    RunSolution,
    RunBatchSolution,
    RunCommunication,
)


class SolutionManager(TaskJobManager, InputsInfoMixin):
    """Runs a solution and checks if it works as expected."""

    def __init__(self, solution_label: str, generate_inputs: bool) -> None:
        self.solution_label: str = solution_label
        self._generate_inputs = generate_inputs
        self.solution_points: Optional[Decimal] = None
        self.subtasks: list[SubtaskJobGroup] = []
        self._subtasks_results: dict[int, Verdict] = {}
        super().__init__(f"Run {solution_label}")

    def _get_jobs(self) -> list[Job]:
        self.is_primary: bool = self._env.config.solutions[self.solution_label].primary
        self._solution = self._env.config.solutions[self.solution_label].source

        jobs: list[Job] = []

        jobs.append(compile_ := Compile(self._env, self._solution, True))
        self._compile_job = compile_

        self._judges: dict[TaskPath, RunJudge] = {}

        for sub_num, inputs in self._all_inputs().items():
            self.subtasks.append(SubtaskJobGroup(self._env, sub_num))
            for inp in inputs:
                jobs += self._input_info_jobs(inp, sub_num)

        return jobs

    def _skip_input(self, input_info: InputInfo, seed: int, subtask: int) -> bool:
        input_path = input_info.task_path(self._env, seed)
        if input_path in self._judges:
            self.subtasks[-1].previous_jobs.append(self._judges[input_path])
        return super()._skip_input(input_info, seed, subtask)

    def _generate_input_jobs(
        self, input_info: InputInfo, seed: int, subtask: int, test_determinism: bool
    ) -> list[Job]:
        if not self._generate_inputs:
            return []
        return super()._generate_input_jobs(input_info, seed, subtask, test_determinism)

    def _respects_seed_jobs(
        self, input_info: InputInfo, seeds: list[int], subtask: int
    ) -> list[Job]:
        if not self._generate_inputs:
            return []
        return super()._respects_seed_jobs(input_info, seeds, subtask)

    def _solution_jobs(
        self, input_info: InputInfo, seed: int, subtask: int
    ) -> list[Job]:
        input_path = input_info.task_path(self._env, seed)

        jobs: list[Job] = []

        run_sol: RunSolution
        run_judge: RunJudge
        if self._env.config.task_type == TaskType.batch:
            if not input_info.is_generated and self._generate_inputs:
                jobs += self._check_output_jobs(
                    self._get_reference_output(input_info, seed), None
                )

            run_batch_sol, run_judge = self._create_batch_jobs(
                input_info, seed, subtask
            )
            run_sol = run_batch_sol
            jobs += [run_batch_sol, run_judge]
            jobs += self._check_output_jobs(run_batch_sol.output, run_batch_sol)

        elif self._env.config.task_type == TaskType.communication:
            run_sol = run_judge = self._create_communication_jobs(input_path, subtask)
            jobs.append(run_sol)

        self._judges[input_path] = run_judge
        self.subtasks[-1].new_jobs.append(run_judge)
        self.subtasks[-1].new_run_jobs.append(run_sol)

        return jobs

    def _create_batch_jobs(
        self, input_info: InputInfo, seed: int, subtask: int
    ) -> tuple[RunBatchSolution, RunBatchJudge]:
        """Create RunSolution and RunBatchJudge jobs for batch task type."""
        input_path = input_info.task_path(self._env, seed)
        run_solution = RunBatchSolution(
            self._env,
            self._solution,
            self.is_primary,
            input_path,
        )
        run_solution.add_prerequisite(self._compile_job)

        out = TaskPath.output_file(self._env, input_path.name, self._solution.name)
        run_judge = judge_job(
            input_path,
            out,
            self._get_reference_output(input_info, seed),
            subtask,
            lambda: f"{seed:x}",
            None,
            self._env,
        )
        run_judge.add_prerequisite(run_solution, name="run_solution")

        return (run_solution, run_judge)

    def _create_communication_jobs(
        self, inp: TaskPath, subtask: int
    ) -> RunCommunication:
        """Create RunCommunication job for communication task type."""
        if self._env.config.out_judge is None:
            raise RuntimeError("Unset judge for communication.")

        return RunCommunication(
            self._env,
            self._solution,
            self.is_primary,
            self._env.config.out_judge,
            subtask,
            inp,
        )

    def _update(self):
        """Cancel running on inputs that can't change anything."""
        expected = self._env.config.solutions[self.solution_label].subtasks

        for subtask in self.subtasks:
            if subtask.definitive(expected[subtask.num]):
                subtask.cancel()

    def _get_status(self) -> str:
        msg = f"Testing {self.solution_label}"
        if self.state == State.cancelled:
            return self._job_bar(msg)

        points_places = len(self._format_points(self._env.config.total_points))
        points = self._format_points(self.solution_points)

        max_time = max((s.slowest_time for s in self.subtasks), default=0)

        if not self.state.finished() or self._env.verbosity == 0:
            points = pad_left(points, points_places)
            header = f"{pad(msg, MSG_LEN-1)} {points}  {max_time:.2f}s  "
            subtasks_text = "|".join(sub.status_verbosity0() for sub in self.subtasks)
        else:
            header = (
                right_aligned_text(f"{msg}: {points}", f"slowest {max_time:.2f}s")
                + "\n"
            )
            header = self._colored(header, "cyan")
            subtasks_text = tab(
                "\n".join(
                    sub.status(self.subtasks, self._env.verbosity)
                    for sub in self.subtasks
                )
            )
            if self._env.verbosity == 1:
                subtasks_text += "\n"

        return header + subtasks_text

    def _evaluate(self) -> None:
        """Evaluates whether solution preformed as expected."""
        self.solution_points = Decimal(0)
        for sub_job in self.subtasks:
            self.solution_points += sub_job.points
            self._subtasks_results[sub_job.num] = sub_job.verdict

        solution_conf = self._env.config.solutions[self.solution_label]
        for sub_job in self.subtasks:
            sub_job.as_expected(solution_conf.subtasks[sub_job.num])

        points = solution_conf.points
        above = solution_conf.points_above
        below = solution_conf.points_below

        if points is not None and self.solution_points != points:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten {points} but got {self.solution_points} points."
            )
        elif above is not None and self.solution_points < above:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten at least {above} but got {self.solution_points} points."
            )
        elif below is not None and self.solution_points > below:
            raise PipelineItemFailure(
                f"Solution {self.solution_label} should have gotten at most {below} but got {self.solution_points} points."
            )

    def _compute_result(self) -> dict[str, Any]:
        result: dict[str, Any] = super()._compute_result()

        result["results"] = {}
        result["judge_outs"] = set()
        for inp, judge_job in self._judges.items():
            result["results"][inp] = judge_job.result

            if judge_job.result is None or judge_job.result.verdict not in (
                Verdict.ok,
                Verdict.partial_ok,
                Verdict.wrong_answer,
            ):
                continue

            if isinstance(judge_job, RunCMSJudge):
                result["judge_outs"].add(judge_job.points_file)
            result["judge_outs"].add(judge_job.judge_log_file)

        result["subtasks"] = self._subtasks_results

        return result


class SubtaskJobGroup(TaskHelper):
    """Groups jobs of a single subtask."""

    def __init__(self, env: Env, num: int) -> None:
        self._env = env
        self.num = num
        self.subtask = env.config.subtasks[num]
        self.new_run_jobs: list[RunSolution] = []
        self.previous_jobs: list[RunJudge] = []
        self.new_jobs: list[RunJudge] = []

    @property
    def all_jobs(self) -> list[RunJudge]:
        return self.previous_jobs + self.new_jobs

    @property
    def points(self) -> Decimal:
        results = self._results(self.all_jobs)
        points = map(lambda r: r.points(self._env, self.subtask.points), results)
        return min(points, default=Decimal(self.subtask.points))

    @property
    def verdict(self) -> Verdict:
        return max(
            self._verdicts(self.all_jobs), default=Verdict.ok, key=lambda v: v.value
        )

    @property
    def slowest_time(self) -> float:
        results = self._results(self.all_jobs)
        times = map(lambda r: r.solution_rr.time, results)
        return max(times, default=0.0)

    def _job_results(self, jobs: list[RunJudge]) -> list[Optional[SolutionResult]]:
        return list(map(lambda j: j.result, jobs))

    def _finished_jobs(self, jobs: list[RunJudge]) -> list[RunJudge]:
        return list(filter(lambda j: j.result is not None, jobs))

    def _results(self, jobs: list[RunJudge]) -> list[SolutionResult]:
        filtered = []
        for res in self._job_results(jobs):
            if res is not None:
                filtered.append(res)
        return filtered

    def _verdicts(self, jobs: list[RunJudge]) -> list[Verdict]:
        return list(map(lambda r: r.verdict, self._results(jobs)))

    def _jobs_points(self) -> list[Decimal]:
        return list(
            map(
                lambda r: r.points(self._env, self.subtask.points),
                self._results(self.new_jobs + self.previous_jobs),
            )
        )

    def status(
        self, all_subtasks: list["SubtaskJobGroup"], verbosity: Optional[int] = None
    ) -> str:
        verbosity = self._env.verbosity if verbosity is None else verbosity

        if verbosity <= 0:
            return self.status_verbosity0()
        elif verbosity == 1:
            return self.status_verbosity1()
        elif verbosity >= 2:
            return self.status_verbosity2(all_subtasks)

        raise RuntimeError(f"Unknown verbosity {verbosity}")

    def _verdict_summary(self, jobs: list[RunJudge]) -> str:
        text = ""
        verdicts = self._verdicts(jobs)
        for verdict in Verdict:
            count = verdicts.count(verdict)
            if count > 0:
                text += f"{count}{verdict.mark()}"
        return text

    def _verdict_marks(self, jobs: list[RunJudge]) -> str:
        return "".join(job.verdict_mark() for job in jobs)

    def _predecessor_summary(self) -> str:
        predecessor_summary = self._verdict_summary(self.previous_jobs)
        if predecessor_summary:
            return f"({predecessor_summary}) "
        return ""

    def status_verbosity0(self) -> str:
        return f"{self._predecessor_summary()}{self._verdict_marks(self.new_jobs)}"

    def status_verbosity1(self) -> str:
        max_sub_name_len = max(
            len(subtask.name) for subtask in self._env.config.subtasks.values()
        )
        max_sub_points_len = max(
            len(self._format_points(sub.points))
            for sub in self._env.config.subtasks.values()
        )

        return right_aligned_text(
            f"{self.subtask.name:<{max_sub_name_len}}  "
            f"{self._format_points(self.points):<{max_sub_points_len}}  "
            f"{self._predecessor_summary()}{self._verdict_marks(self.new_jobs)}",
            f"slowest {self.slowest_time:.2f}s",
            offset=-2,
        )

    def status_verbosity2(self, all_subtasks: list["SubtaskJobGroup"]):
        def subtask_name(num: int) -> str:
            return self._env.config.subtasks[num].name

        text = ""
        max_inp_name_len = max(len(j.input.name) for j in self.new_jobs)
        subtask_info = (
            right_aligned_text(
                f"{self.subtask.name}: {self._format_points(self.points)}/{self._format_points(self.subtask.points)}",
                f"slowest {self.slowest_time:.2f}s",
                offset=-2,
            )
            + "\n"
        )
        text += self._env.colored(subtask_info, "magenta")

        max_pred_name_len = max(
            (len(subtask_name(pred)) for pred in self.subtask.all_predecessors),
            default=0,
        )
        for pred in self.subtask.all_predecessors:
            pred_group = all_subtasks[pred]
            text += right_aligned_text(
                tab(
                    f"Predecessor {pad(subtask_name(pred) + ':', max_pred_name_len + 1)}  "
                    f"{pred_group.status_verbosity0()}"
                ),
                f"slowest {pred_group.slowest_time:.2f}s",
                offset=-2,
            )
            text += "\n"

        if len(self.subtask.all_predecessors) and any(
            map(lambda j: j.result, self.new_jobs)
        ):
            text += "\n"

        for job in self.new_jobs:
            if job.result is not None:
                input_verdict = tab(
                    f"{job.input.name:<{max_inp_name_len}} "
                    f"({self._format_points(job.result.points(self._env, self.subtask.points))}): "
                    f"{job.verdict_text()}"
                )
                text += right_aligned_text(
                    input_verdict, f"{job.result.solution_rr.time:.2f}s", offset=-2
                )
                text += "\n"

        return text

    def definitive(self, expected_str: str) -> bool:
        """Checks whether subtask jobs have resulted in outcome that cannot be changed."""
        if self._env.all_inputs:
            return False

        if self._env.skip_on_timeout and Verdict.timeout in self._verdicts(
            self.new_jobs
        ):
            return True

        if expected_str == "X" and not self.verdict.is_zero_point():
            return False  # Cause X is very very special

        return self._as_expected(expected_str)[1]

    def as_expected(self, expected_str: str) -> None:
        """Checks this subtask resulted as expected. Raises PipelineItemFailure otherwise."""
        ok, _, breaker = self._as_expected(expected_str)
        if not ok:
            msg = f"{self.subtask.name} did not result as expected: '{expected_str}'"
            if breaker is not None:
                msg += f"\n{tab(breaker.message())}"
            raise PipelineItemFailure(msg)

    def _as_expected(self, expected_str: str) -> tuple[bool, bool, Optional[RunJudge]]:
        """
        Returns tuple:
            - whether subtask jobs have resulted as expected
            - whether the result is definitive (cannot be changed)
            - a job that makes the result different than expected (if there is one particular)
        """

        jobs = self.new_jobs + (
            [] if self._env.config.scoring == Scoring.equal else self.previous_jobs
        )

        finished_jobs = self._finished_jobs(jobs)
        verdicts = self._results(jobs)

        result, definitive, breaker = evaluate_verdicts(
            self._env.config, list(map(lambda r: r.verdict, verdicts)), expected_str
        )

        breaker_job = None if breaker is None else finished_jobs[breaker]

        return result, definitive, breaker_job

    def cancel(self):
        for job in self.new_run_jobs:
            job.cancel()
