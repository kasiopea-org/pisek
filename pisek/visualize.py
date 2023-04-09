from collections import namedtuple
import json
from math import ceil
import os
import re
import sys
from typing import List, Union, Iterable

from task_config import TaskConfig, SubtaskConfig

TASK_DIR = '.'

VERDICTS = {
    'ok': '·',
    'timeout': 'T',
    'wrong_answer': 'W',
    'error' : '!'
}
VERDICTS_ORDER = ['·', 'T', 'W', '!']

TestCaseResult = namedtuple('TestCaseResult', ('name', 'verdict', 'value'))

def group_by_subtask(results : List[TestCaseResult], config : TaskConfig) -> List[List[TestCaseResult]]:
    subtasks = {num:[] for num in config.subtasks.keys()}
    for result in results:
        for i, subtask in config.subtasks.items():
            if in_subtask(result.name, subtask):
                subtasks[i].append(result)
    subtasks = list(subtasks.items())
    subtasks.sort()
    return list(map(lambda x: x[1], subtasks))

def in_subtask(name : str, subtask : SubtaskConfig):
    return re.match(subtask.globs_regex(), name) is not None

def closest(results : List[TestCaseResult]) -> List[TestCaseResult]:
    closest_results = []
    correct = filter_by_verdict(results, VERDICTS['ok'])
    timeouted = filter_by_verdict(results, VERDICTS['timeout'])
    if len(correct):
        closest_results.append(max(correct, key=lambda x: x.value))
    if len(timeouted):
        closest_results.append(min(timeouted, key=lambda x: x.value))
    return closest_results

def slowest(results : List[TestCaseResult]) -> List[TestCaseResult]:
    candidates = filter_by_verdict(results, (VERDICTS['ok'], VERDICTS['timeout']))
    slowest = max(candidates, key=lambda x: x.value)    
    return [slowest]

def identity(results : List[TestCaseResult]) -> List[TestCaseResult]:
    return results

MODES_ALIASES = {
    'c': closest,
    'closest': closest,
    
    's': slowest,
    'slowest': slowest,
    
    'a': identity,
    'all': identity,
}

def visualize(
    mode : str = "closest",
    by_subtask : bool = True,
    solutions : Union[List[str], str] = 'all',
    filename : str = 'testing_log.json',
    measured_stat : str = 'time',
    segments : int = 10,
):
    config = TaskConfig(TASK_DIR)
    with open(os.path.join(TASK_DIR, filename)) as f:
        testing_log = json.load(f)

    testing_log2 = {}
    for sol_name in testing_log:
        testing_log2[strip_suffix(sol_name)] = testing_log[sol_name]
    testing_log = testing_log2

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

    # Kind of slow, but we will not have hundreds of solutions
    solutions.sort(key=lambda x: config.solutions.index(x))
    
    for solution_name in solutions:
        visualize_solution(
            solution_name,
            testing_log[solution_name],
            config,
            mode,
            by_subtask,
            measured_stat,
            segments
        )


def visualize_solution(
        solution_name: str,
        data,
        config : TaskConfig,
        mode : str,
        by_subtask : bool,
        measured_stat : str,
        segments : int
):  
    results = data['results']

    # First extract desired stats
    results_extracted = [] 
    for result in results:
        final_verdict = VERDICTS[result['result']]
        
        if measured_stat != 'time':
            raise NotImplementedError()
        
        # We are testing at higher limits in cms
        # TODO: Implement here for other values
        if result['time'] > config.get_timeout(is_secondary_solution=True):
            final_verdict = VERDICTS['timeout']

        value = result[measured_stat]
        results_extracted.append(TestCaseResult(result['test'], final_verdict, value))

    # Sort and filter
    results_extracted.sort(key=lambda x: x.name)
    results_extracted.sort(key=lambda x: x.value)
    results_extracted.sort(key=lambda x: VERDICTS_ORDER.index(x.verdict))
    results_extracted.sort(key=lambda x: get_subtask(x.name))

    if by_subtask:
        results_filtered = list(map(mode, group_by_subtask(results_extracted, config)))
    else:
        results_filtered = [mode(results_extracted)]

    # Lastly print
    print(f"{solution_name}:")

    # TODO: Implement here for other values of measured_stat
    if measured_stat != 'time':
        raise NotImplementedError()    
    limit = config.get_timeout(is_secondary_solution=True)
    segment_length = limit / segments

    max_overflower = max(sum(results_filtered, start=[]), key=lambda x: x.value)
    max_overflowed_segments = overflowed_segments(max_overflower.value, limit, segment_length)

    for group_i, group in enumerate(results_filtered):
        if by_subtask:
            print(config.subtasks[group_i+1].name)
        for result in group:
            in_segments = in_time_segments(result.value, limit, segment_length)
            overflow_segments = overflowed_segments(result.value, limit, segment_length)
            
            print(
                f"  {result.name} ({result.verdict}): "
                f"|{'.'*in_segments}{' '*(segments-in_segments)}"
                f"|{'.'*overflow_segments}{' '*(max_overflowed_segments-overflow_segments)}"
                f" ({result.value}/{limit})"
            )
    print()

def get_subtask(name):
    return name[:2]

def strip_suffix(name):
    return name[:name.rfind('.')]

def filter_by_verdict(results : List[TestCaseResult], verdicts : Union[str, Iterable[str]]) -> List[TestCaseResult]:
    if isinstance(verdicts, str):
        verdicts = (verdicts,)
    return list(filter(lambda x: x.verdict in verdicts, results))

def in_time_segments(value, limit, segment_length):
    return ceil(min(value, limit) / segment_length)

def overflowed_segments(value, limit, segment_length):
    return max(0, ceil((value - limit) / segment_length))


if __name__ == "__main__":
    visualize()
