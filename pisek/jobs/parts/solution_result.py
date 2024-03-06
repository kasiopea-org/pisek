# pisek  - Tool for developing tasks for programming competitions.
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

from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from typing import Optional, Callable
import yaml


class Verdict(Enum):
    ok = auto()
    partial = auto()
    timeout = auto()
    wrong_answer = auto()
    error = auto()

    def mark(self) -> str:
        return {
            Verdict.ok: "·",
            Verdict.partial: "P",
            Verdict.timeout: "T",
            Verdict.wrong_answer: "W",
            Verdict.error: "!",
        }[self]


@dataclass
class SolutionResult:
    """Class representing result of a solution on given input."""

    verdict: Verdict
    points: float
    time: float
    wall_time: float
    judge_stderr: str
    output: str = ""
    diff: str = ""

    def __str__(self):
        if self.verdict == Verdict.partial:
            return f"[{self.points:.2f}]"
        else:
            return self.verdict.mark()


def sol_result_representer(dumper, sol_result: SolutionResult):
    return dumper.represent_sequence(
        "!SolutionResult",
        [
            sol_result.verdict.name,
            sol_result.points,
            sol_result.time,
            sol_result.wall_time,
            sol_result.judge_stderr,
            sol_result.output,
            sol_result.diff,
        ],
    )


def sol_result_constructor(loader, value) -> SolutionResult:
    verdict, points, time, wall_time, stderr, output, diff = loader.construct_sequence(
        value
    )
    return SolutionResult(
        Verdict[verdict], points, time, wall_time, stderr, output, diff
    )


yaml.add_representer(SolutionResult, sol_result_representer)
yaml.add_constructor("!SolutionResult", sol_result_constructor)


def verdict_true(res: Verdict) -> bool:
    return True


def verdict_ok(res: Verdict, ok: bool) -> bool:
    if ok:
        return res == Verdict.ok
    else:
        return res in (Verdict.wrong_answer, Verdict.timeout, Verdict.error)


def specific_verdict(res: Verdict, verdict: Verdict) -> bool:
    return res == verdict


# Specifies how expected str should be interpreted
# First function must be true for all
# Second function must be true for any/all according to fail_mode
SUBTASK_SPEC: dict[str, tuple[Callable[[Verdict], bool], Callable[[Verdict], bool]]] = {
    "1": (partial(verdict_ok, ok=True), verdict_true),
    "0": (verdict_true, partial(verdict_ok, ok=False)),
    "X": (verdict_true, verdict_true),
    "P": (
        lambda r: not verdict_ok(r, ok=False),
        partial(specific_verdict, verdict=Verdict.partial),
    ),
    "W": (
        verdict_true,
        partial(specific_verdict, verdict=Verdict.wrong_answer),
    ),
    "!": (verdict_true, partial(specific_verdict, verdict=Verdict.error)),
    "T": (verdict_true, partial(specific_verdict, verdict=Verdict.timeout)),
}
