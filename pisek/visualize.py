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

from collections import namedtuple
import fnmatch
import json
from math import ceil
import os
import re
import sys
from colorama import Fore
from typing import Optional, Union, Iterable, Callable

from .config.task_config import load_config, TaskConfig, SubtaskConfig
from pisek.jobs.parts.task_job import TaskHelper

VERDICTS = {
    "ok": "·",
    "partial": "P",
    "timeout": "T",
    "timeout_limited": "t",
    "wrong_answer": "W",
    "error": "!",
}
VERDICTS_ORDER = ["·", "P", "t", "T", "W", "!"]

# subtask section
TestCaseResult = namedtuple("TestCaseResult", ("name", "verdict", "value", "points"))


def red(msg: str) -> str:
    return f"{Fore.RED}{msg}{Fore.RESET}"


def group_by_subtask(
    results: list[TestCaseResult], config: TaskConfig
) -> dict[str, list[TestCaseResult]]:
    subtasks: dict[str, list[TestCaseResult]] = {
        num: [] for num, _ in config.subtasks.subenvs()
    }
    for result in results:
        for i, subtask in config.subtasks.subenvs():
            if in_subtask(result.name, subtask):
                subtasks[i].append(result)
    return subtasks


def in_subtask(name: str, subtask: SubtaskConfig):
    return any(fnmatch.fnmatch(f"{name}.in", g) for g in subtask.all_globs)


def evaluate_solution(
    results: dict[str, list[TestCaseResult]], config: TaskConfig
) -> float:
    points = 0.0
    for subtask_id, sub_results in results.items():
        points += evaluate_subtask(sub_results, config.subtasks[subtask_id].score)
    return points


def evaluate_subtask(subtask_results: list[TestCaseResult], max_points):
    return max_points * min(map(lambda r: r.points, subtask_results), default=0)


# mode section
def slowest(results: list[TestCaseResult]) -> Union[str, list[TestCaseResult]]:
    wa = filter_by_verdict(results, VERDICTS["wrong_answer"])
    err = filter_by_verdict(results, VERDICTS["error"])
    if len(wa) != 0 or len(err) != 0:
        return f"{len(wa)}{VERDICTS['wrong_answer']}, {len(err)}{VERDICTS['error']}"
    slowest = max(results, key=lambda x: x.value)
    return [slowest]


def identity(results: list[TestCaseResult]) -> list[TestCaseResult]:
    return results


MODES_ALIASES = {
    "s": slowest,
    "slowest": slowest,
    "a": identity,
    "all": identity,
}


# visualization section
def visualize_command(path, args):
    visualize(
        path,
        args.mode,
        not args.no_subtasks,
        args.solutions,
        args.filename,
        args.measured_stat,
        args.limit,
        args.segments,
    )


def visualize(
    path: str = ".",
    mode: str = "slowest",
    by_subtask: bool = True,
    solutions: list[str] = [],
    filename: str = "testing_log.json",
    measured_stat: str = "time",
    limit: Optional[float] = None,
    segments: int = 10,
):
    config = load_config(path)
    if config is None:
        return exit(1)

    with open(os.path.join(path, filename)) as f:
        testing_log = json.load(f)

    if mode not in MODES_ALIASES:
        print(
            f"Neznámý mód {mode}. Známé mody jsou: {', '.join(set(MODES_ALIASES.keys()))}"
        )
        exit(1)
    mode_func = MODES_ALIASES[mode]

    if solutions == []:
        solutions = list(testing_log.keys() - {"source"})
    else:
        for solution_name in solutions:
            if solution_name not in testing_log:
                print(f"Řešení '{solution_name}' není v '{filename}'.", file=sys.stderr)
                exit(1)

    # TODO: Implement here for other values of measured_stat
    if measured_stat != "time":
        raise NotImplementedError()

    if limit is None:
        if measured_stat == "time":
            limit = config.get_timeout(True)
        else:  # TODO: Fix when implementing additional stats
            limit = 1

    # Kind of slow, but we will not have hundreds of solutions
    def solution_index(name) -> int:
        for i, (_, sol) in enumerate(config.solutions.items()):
            if sol.source == name:
                return i
        raise ValueError(f"Unknown solution {name}")

    solutions.sort(key=solution_index)

    unexpected_solutions = []
    for solution_name in solutions:
        if not visualize_solution(
            solution_name,
            testing_log[solution_name],
            config,
            mode_func,
            by_subtask,
            measured_stat,
            limit,
            segments,
        ):
            unexpected_solutions.append(solution_name)

    if len(unexpected_solutions):
        print(
            red(f"Řešení {', '.join(unexpected_solutions)} získala špatný počet bodů."),
            file=sys.stderr,
        ),


def visualize_solution(
    solution_name: str,
    data,
    config: TaskConfig,
    mode_func: Callable[[list[TestCaseResult]], Union[list[TestCaseResult], str]],
    by_subtask: bool,
    measured_stat: str,
    limit: float,
    segments: int,
):
    results = data["results"]

    # First extract desired stats
    results_extracted = []
    for result in results:
        final_verdict = VERDICTS[result["result"]]
        points = result["points"]

        # We are testing at higher limits in cms
        # TODO: Implement here for other values
        if final_verdict == VERDICTS["ok"] or final_verdict == VERDICTS["partial"]:
            if result["time"] > limit:
                final_verdict = VERDICTS["timeout_limited"]
                points = 0.0

        value = result[measured_stat]
        results_extracted.append(
            TestCaseResult(result["test"], final_verdict, value, points)
        )

    # Sort and filter
    results_extracted.sort(key=lambda x: x.name)
    results_extracted.sort(key=lambda x: x.value)
    results_extracted.sort(key=lambda x: VERDICTS_ORDER.index(x.verdict))
    results_extracted.sort(key=lambda x: get_subtask(x.name))

    results_evaluate = group_by_subtask(results_extracted, config)

    if by_subtask:
        results_filtered: dict[str, Union[str, list[TestCaseResult]]] = {}
        for key in results_evaluate:
            results_filtered[key] = mode_func(results_evaluate[key])
    else:
        results_filtered = {"all": mode_func(results_extracted)}

    def get_points(name):
        for _, sol in config.solutions.items():
            if sol.source == name:
                return sol.points

    # Lastly print
    exp_score = get_points(solution_name)
    score = evaluate_solution(results_evaluate, config)
    as_expected = (exp_score is None) or (exp_score == score)
    print(f"{solution_name}: ({score}b)")
    if not as_expected:
        print(
            red(
                f"Řešení {solution_name} mělo získat {exp_score}b, ale získalo {score}b."
            ),
            file=sys.stderr,
        ),

    segment_length = limit / segments

    results_groups: list[list[TestCaseResult]] = []
    for group in results_filtered.values():
        if isinstance(group, list):
            results_groups.append(group)

    if len(results_groups):
        max_overflower = max(sum(results_groups, start=[]), key=lambda x: x.value)
        max_overflowed_segments = overflowed_segments(
            max_overflower.value, limit, segment_length
        )

    for subtask_num in sorted(results_filtered.keys()):
        if by_subtask:
            subtask_score = evaluate_subtask(
                results_evaluate[subtask_num], config.subtasks[subtask_num].score
            )
            print(f"{config.subtasks[subtask_num].name} ({subtask_score}b)")

        subtask_results = results_filtered[subtask_num]
        if isinstance(subtask_results, str):
            print("  " + subtask_results)
            continue

        for result in subtask_results:
            in_segments = in_time_segments(result.value, limit, segment_length)
            overflow_segments = overflowed_segments(result.value, limit, segment_length)

            print(
                f"  {result.name} ({result.verdict}): "
                f"|{'·'*in_segments}{' '*(segments-in_segments)}"
                f"|{'·'*overflow_segments}{' '*(max_overflowed_segments-overflow_segments)}"
                f" ({result.value}/{limit})"
            )
    print()
    return as_expected


def get_subtask(name):
    if name.startswith("sample"):
        return "00"
    return name[:2]


def strip_suffix(name):
    return name[: name.rfind(".")]


def filter_by_verdict(
    results: list[TestCaseResult], verdicts: Union[str, Iterable[str]]
) -> list[TestCaseResult]:
    if isinstance(verdicts, str):
        verdicts = (verdicts,)
    return list(filter(lambda x: x.verdict.upper() in verdicts, results))


def in_time_segments(value, limit, segment_length):
    return ceil(min(value, limit) / segment_length)


def overflowed_segments(value, limit, segment_length):
    return max(0, ceil((value - limit) / segment_length))


if __name__ == "__main__":
    visualize()
