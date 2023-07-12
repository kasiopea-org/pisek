from collections import namedtuple
import json
from math import ceil
import os
import re
import sys
from ansi.color import fg
from ansi.color.fx import reset
from typing import List, Dict, Optional, Union, Iterable

from pisek import util
from .task_config import TaskConfig, SubtaskConfig

TASK_DIR = '.'

VERDICTS = {
    'ok': '·',
    'timeout': 'T',
    'timeout_limited': 't',
    'wrong_answer': 'W',
    'error' : '!'
}
VERDICTS_ORDER = ['·', 't', 'T', 'W', '!']

# subtask section
TestCaseResult = namedtuple('TestCaseResult', ('name', 'verdict', 'value', 'points'))

def red(msg: str) -> str:
    return f"{fg.red}{msg}{reset}"

def group_by_subtask(results : List[TestCaseResult], config : TaskConfig) -> List[List[TestCaseResult]]:
    subtasks = {num:[] for num in config.subtasks.keys()}
    for result in results:
        for i, subtask in config.subtasks.items():
            if in_subtask(result.name, subtask):
                subtasks[i].append(result)
    return subtasks

def in_subtask(name : str, subtask : SubtaskConfig):
    return re.match(subtask.globs_regex(), name) is not None

def evaluate_solution(results : Dict[int, List[TestCaseResult]], config : TaskConfig) -> float:
    points = 0.0
    for subtask_id, sub_results in results.items():
        points += evaluate_subtask(sub_results, config.subtasks[subtask_id].score)
    return points

def evaluate_subtask(subtask_results : List[TestCaseResult], max_points):
    subtask_success = 1
    for result in subtask_results:
        subtask_success = min(subtask_success, result.points)
    return max_points * subtask_success

# mode section
def slowest(results : List[TestCaseResult]) -> Union[str, List[TestCaseResult]]:
    wa = filter_by_verdict(results, VERDICTS['wrong_answer'])
    err = filter_by_verdict(results, VERDICTS['error'])
    if len(wa) != 0 or len(err) != 0:
        return f"{len(wa)}{VERDICTS['wrong_answer']}, {len(err)}{VERDICTS['error']}"
    slowest = max(results, key=lambda x: x.value)
    return [slowest]

def identity(results : List[TestCaseResult]) -> List[TestCaseResult]:
    return results

MODES_ALIASES = {
    's': slowest,
    'slowest': slowest,

    'a': identity,
    'all': identity,
}

# visualization section
def visualize_command(args):
    visualize(
        args.mode,
        not args.no_subtasks,
        args.solutions,
        args.filename,
        args.measured_stat,
        args.limit,
        args.segments
    )

def visualize(
    mode : str = "slowest",
    by_subtask : bool = True,
    solutions : Union[List[str], str] = 'all',
    filename : str = 'testing_log.json',
    measured_stat : str = 'time',
    limit : Optional[int] = None,
    segments : int = 10,
):
    config = TaskConfig(TASK_DIR)
    with open(os.path.join(TASK_DIR, filename)) as f:
        testing_log = json.load(f)

    if mode not in MODES_ALIASES:
        print(f"Neznámý mód {mode}. Známé mody jsou: {', '.join(set(MODES_ALIASES.values()))}")
        exit(1)
    mode = MODES_ALIASES[mode]

    if solutions == 'all':
        solutions = list(testing_log.keys())
    else:
        for solution_name in solutions:
            if solution_name not in testing_log:
                print(f"Řešení '{solution_name}' není v '{filename}'.", file=sys.stderr)
                exit(1)

    # TODO: Implement here for other values of measured_stat
    if measured_stat != 'time':
        raise NotImplementedError()    

    if limit is None:
        if measured_stat == 'time':
            limit = config.get_timeout(True)

    # Kind of slow, but we will not have hundreds of solutions
    solutions.sort(key=lambda x: config.solutions.index(x))

    unexpected_solutions = []
    for solution_name in solutions:
        if not visualize_solution(
            solution_name,
            testing_log[solution_name],
            config,
            mode,
            by_subtask,
            measured_stat,
            limit,
            segments
        ):
            unexpected_solutions.append(solution_name)
    
    if len(unexpected_solutions):
        print(
            red(f"Řešení {', '.join(unexpected_solutions)} získala špatný počet bodů."),
            file=sys.stderr
        ),


def visualize_solution(
        solution_name: str,
        data,
        config : TaskConfig,
        mode : str,
        by_subtask : bool,
        measured_stat : str,
        limit : int,
        segments : int
):  
    results = data['results']

    # First extract desired stats
    results_extracted = [] 
    for result in results:
        final_verdict = VERDICTS[result['result']]
        points = result['points'] 

        # We are testing at higher limits in cms
        # TODO: Implement here for other values
        if final_verdict == VERDICTS['ok']:
            if result['time'] > limit:
                final_verdict = VERDICTS['timeout_limited']
                points = 0.0

        value = result[measured_stat]
        results_extracted.append(TestCaseResult(result['test'], final_verdict, value, points))

    # Sort and filter
    results_extracted.sort(key=lambda x: x.name)
    results_extracted.sort(key=lambda x: x.value)
    results_extracted.sort(key=lambda x: VERDICTS_ORDER.index(x.verdict))
    results_extracted.sort(key=lambda x: get_subtask(x.name))

    results_evalute = group_by_subtask(results_extracted, config)

    if by_subtask:
        results_filtered = group_by_subtask(results_extracted, config)
        for key in results_filtered:
            results_filtered[key] = mode(results_filtered[key])
    else:
        results_filtered = {'all': mode(results_extracted)}

    # Lastly print
    exp_score = util.get_expected_score(solution_name, config)
    score = evaluate_solution(results_evalute, config)
    as_expected = (exp_score is None) or (exp_score == score) 
    print(f"{solution_name}: ({score}b)")
    if not as_expected:
        print(
            red(f"Řešení {solution_name} mělo získat {exp_score}b, ale získalo {score}b."),
            file=sys.stderr
        ),
    

    segment_length = limit / segments

    results_groups = list(filter(lambda x: isinstance(x, list), results_filtered.values()))
    if len(results_groups):
        max_overflower = max(sum(results_groups, start=[]), key=lambda x: x.value)
        max_overflowed_segments = overflowed_segments(max_overflower.value, limit, segment_length)

    for subtask_num in sorted(results_filtered.keys()):
        if by_subtask:
            subtask_score = evaluate_subtask(results_evalute[subtask_num], config.subtasks[subtask_num].score) 
            print(f"{config.subtasks[subtask_num].name} ({subtask_score}b)")
        
        if isinstance(results_filtered[subtask_num], str):
            print("  " + results_filtered[subtask_num])
            continue

        for result in results_filtered[subtask_num]:
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
    return name[:2]

def strip_suffix(name):
    return name[:name.rfind('.')]

def filter_by_verdict(results : List[TestCaseResult], verdicts : Union[str, Iterable[str]]) -> List[TestCaseResult]:
    if isinstance(verdicts, str):
        verdicts = (verdicts,)
    return list(filter(lambda x: x.verdict.upper() in verdicts, results))

def in_time_segments(value, limit, segment_length):
    return ceil(min(value, limit) / segment_length)

def overflowed_segments(value, limit, segment_length):
    return max(0, ceil((value - limit) / segment_length))


if __name__ == "__main__":
    visualize()
