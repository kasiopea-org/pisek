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
from enum import Enum
from functools import partial
from typing import Callable, Iterable
import yaml

Verdict = Enum(
    "Verdict", ["ok", "partial", "indeterminate", "wrong_answer", "error", "timeout"]
)
RESULT_MARK = {
    Verdict.ok: "·",
    Verdict.partial: "P",
    Verdict.indeterminate: "?",
    Verdict.error: "!",
    Verdict.timeout: "T",
    Verdict.wrong_answer: "W",
}


@dataclass
class SolutionResult:
    """Class representing result of a solution on given input."""

    verdict: Verdict
    points: float
    judge_stderr: str
    output: str = ""
    diff: str = ""

    def __str__(self):
        if self.verdict == Verdict.partial:
            return f"[{self.points:.2f}]"
        else:
            return RESULT_MARK[self.verdict]


def sol_result_representer(dumper, sol_result: SolutionResult):
    return dumper.represent_sequence(
        "!SolutionResult",
        [
            sol_result.verdict.name,
            sol_result.points,
            sol_result.judge_stderr,
            sol_result.output,
            sol_result.diff,
        ],
    )


def sol_result_constructor(loader, value) -> SolutionResult:
    verdict, points, stderr, output, diff = loader.construct_sequence(value)
    return SolutionResult(Verdict[verdict], points, stderr, output, diff)


yaml.add_representer(SolutionResult, sol_result_representer)
yaml.add_constructor("!SolutionResult", sol_result_constructor)


def solution_res_true(sol_res: SolutionResult) -> bool:
    return True


def solution_result_c_points(sol_res: SolutionResult, c: float) -> bool:
    return sol_res.points == c and sol_res.verdict != Verdict.indeterminate


def solution_result_verdict(sol_res: SolutionResult, verdict: Verdict) -> bool:
    return sol_res.verdict == verdict


# Specifies how expected str should be interpreted
# First function must be true for all
# Second function must be true for any/all according to fail_mode
SUBTASK_SPEC: dict[
    str, tuple[Callable[[SolutionResult], bool], Callable[[SolutionResult], bool]]
] = {
    "1": (partial(solution_result_c_points, c=1.0), solution_res_true),
    "0": (solution_res_true, partial(solution_result_c_points, c=0.0)),
    "X": (solution_res_true, solution_res_true),
    "P": (
        lambda r: not solution_result_c_points(r, 0.0),
        partial(solution_result_verdict, verdict=Verdict.partial),
    ),
    "W": (
        solution_res_true,
        partial(solution_result_verdict, verdict=Verdict.wrong_answer),
    ),
    "!": (solution_res_true, partial(solution_result_verdict, verdict=Verdict.error)),
    "T": (solution_res_true, partial(solution_result_verdict, verdict=Verdict.timeout)),
}
