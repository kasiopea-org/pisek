import configparser
import glob
from itertools import product
import os
import re
import shutil
from typing import Optional

from pisek.task_config import CONFIG_FILENAME


def update(path) -> Optional[str]:
    config_path = os.path.join(path, CONFIG_FILENAME)
    if not os.path.exists(config_path):
        return f"Config {config_path} does not exist."

    shutil.copy(config_path, os.path.join(path, f"original_{CONFIG_FILENAME}"))

    config = configparser.ConfigParser()
    read_files = config.read(config_path)

    config["task"]["version"] = "v2"

    subtask_points = []
    for section in sorted(config.sections()):
        if re.fullmatch(r'test[0-9]{2}', section):
            if 'points' not in config[section]:
                return f"Missing key 'points' in section [{section}]"
            subtask_points.append(int(config[section]['points']))
    if "test00" not in config.sections():
        subtask_points = [0] + subtask_points

    if 'solutions' not in config["task"]:
        return f"Missing key 'solutions' in section [task]"
    solutions = config["task"]["solutions"].split()
    del config["task"]["solutions"]

    for i, solution in enumerate(solutions):
        if match := re.fullmatch(r'(.*?)_([0-9]{1,3}|X)b', solution):
            points = None if match[2] == 'X' else int(match[2])
            if len(glob.glob(os.path.join(path, config["task"].get("solutions_subdir", ""), f"{solution}.*"))):
                source = solution
            else:
                source = match[1]
        else:
            source = solution
            points = sum(subtask_points)

        if points is None:
            subtasks = 'X'*len(subtask_points)
        else:
            subtasks = get_subtask_mask(points, subtask_points)

        solution = f"solution_{solution}"
        config.add_section(solution)
        if i == 0:
            config[solution]["primary"] = "yes"
        config[solution]["source"] = source
        config[solution]["points"] = 'X' if points is None else str(points)
        config[solution]["subtasks"] = subtasks

    with open(config_path, "w") as f:
        config.write(f, space_around_delimiters=False)

    return None

def get_subtask_mask(points, subtasks):
    all_valid = [0]*len(subtasks)

    valid = 0
    for comb in product([0, 1], repeat=len(subtasks)):
        p = sum([comb[i] * subtasks[i] for i in range(len(subtasks))])
        if p == points:
            valid += 1
            for i in range(len(subtasks)):
                all_valid[i] += comb[i]

    if valid == 0:
        return 'X'*len(subtasks)

    sub_mask = ""
    for x in all_valid:
        if x == valid:
            sub_mask += '1'
        elif x == 0:
            sub_mask += '0'
        else:
            sub_mask += 'X'
    return sub_mask
