# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from functools import partial, cache
from typing import Callable, Optional, TYPE_CHECKING
import yaml

from pisek.task_jobs.run_result import RunResult

if TYPE_CHECKING:
    from pisek.env.env import Env


class Verdict(Enum):
    # Higher value means more unsuccessful verdict.
    ok = 1
    partial_ok = 2
    timeout = 3
    wrong_answer = 4
    error = 5

    def is_zero_point(self) -> bool:
        return self in (Verdict.timeout, Verdict.wrong_answer, Verdict.error)

    def mark(self) -> str:
        return {
            Verdict.ok: "·",
            Verdict.partial_ok: "P",
            Verdict.timeout: "T",
            Verdict.wrong_answer: "W",
            Verdict.error: "!",
        }[self]

    @staticmethod
    @cache
    def pad_length() -> int:
        return max(len(v.name) for v in Verdict)


@dataclass(init=False)
class SolutionResult(ABC):
    """Class representing result of a solution on given input."""

    verdict: Verdict
    message: Optional[str]
    solution_rr: RunResult
    judge_rr: Optional[RunResult]

    @abstractmethod
    def points(self, env: "Env", subtask_points: int) -> Decimal:
        pass

    def mark(self) -> str:
        return self.verdict.mark()


@dataclass
class RelativeSolutionResult(SolutionResult):
    verdict: Verdict
    message: Optional[str]
    solution_rr: RunResult
    judge_rr: Optional[RunResult]
    relative_points: Decimal

    def points(self, env: "Env", subtask_points: int) -> Decimal:
        return (self.relative_points * subtask_points).quantize(
            Decimal("0.1") ** env.config.score_precision
        )

    def mark(self) -> str:
        if self.verdict == Verdict.partial_ok:
            return f"[{self.relative_points:.2f}]"
        return super().mark()


@dataclass
class AbsoluteSolutionResult(SolutionResult):
    verdict: Verdict
    message: Optional[str]
    solution_rr: RunResult
    judge_rr: Optional[RunResult]
    absolute_points: Decimal

    def points(self, env: "Env", subtask_points: int) -> Decimal:
        return self.absolute_points

    def mark(self) -> str:
        if self.verdict == Verdict.partial_ok:
            return f"[={self.absolute_points}]"
        return super().mark()


def abs_sol_result_representer(dumper, sol_result: AbsoluteSolutionResult):
    return dumper.represent_sequence(
        "!AbsoluteSolutionResult",
        [
            sol_result.verdict.name,
            sol_result.message,
            sol_result.solution_rr,
            sol_result.judge_rr,
            str(sol_result.absolute_points),
        ],
    )


def abs_sol_result_constructor(loader, value) -> AbsoluteSolutionResult:
    verdict, message, points, sol_rr, judge_rr = loader.construct_sequence(value)
    return AbsoluteSolutionResult(
        Verdict[verdict], message, sol_rr, judge_rr, Decimal(points)
    )


yaml.add_representer(AbsoluteSolutionResult, abs_sol_result_representer)
yaml.add_constructor("!AbsoluteSolutionResult", abs_sol_result_constructor)


def rel_sol_result_representer(dumper, sol_result: RelativeSolutionResult):
    return dumper.represent_sequence(
        "!RelativeSolutionResult",
        [
            sol_result.verdict.name,
            sol_result.message,
            sol_result.solution_rr,
            sol_result.judge_rr,
            str(sol_result.relative_points),
        ],
    )


def rel_sol_result_constructor(loader, value) -> RelativeSolutionResult:
    verdict, message, sol_rr, judge_rr, points = loader.construct_sequence(value)
    return RelativeSolutionResult(
        Verdict[verdict], message, sol_rr, judge_rr, Decimal(points)
    )


yaml.add_representer(RelativeSolutionResult, rel_sol_result_representer)
yaml.add_constructor("!RelativeSolutionResult", rel_sol_result_constructor)


def verdict_always(res: Verdict) -> bool:
    return True


def verdict_1point(res: Verdict) -> bool:
    return res == Verdict.ok


def verdict_0points(res: Verdict) -> bool:
    return res in (Verdict.wrong_answer, Verdict.timeout, Verdict.error)


def specific_verdict(res: Verdict, verdict: Verdict) -> bool:
    return res == verdict


# Specifies how expected str should be interpreted
# First function must be true for all
# Second function must be true for any/all according to scoring (min/equal)
SUBTASK_SPEC: dict[str, tuple[Callable[[Verdict], bool], Callable[[Verdict], bool]]] = {
    "1": (verdict_1point, verdict_always),
    "0": (verdict_always, verdict_0points),
    "X": (verdict_always, verdict_always),
    "P": (
        lambda r: not verdict_0points(r),
        partial(specific_verdict, verdict=Verdict.partial_ok),
    ),
    "W": (
        verdict_always,
        partial(specific_verdict, verdict=Verdict.wrong_answer),
    ),
    "!": (verdict_always, partial(specific_verdict, verdict=Verdict.error)),
    "T": (verdict_always, partial(specific_verdict, verdict=Verdict.timeout)),
}
