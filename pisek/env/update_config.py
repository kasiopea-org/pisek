# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from configparser import ConfigParser
from copy import copy
import glob
from itertools import product
import os
import re

from pisek.utils.text import eprint, colored
from pisek.env.config_errors import TaskConfigError


def rename_key(config: ConfigParser, section: str, key_from: str, key_to: str):
    if key_from in config[section]:
        config[section][key_to] = config[section][key_from]
        del config[section][key_from]


def update_to_v2(config: ConfigParser, task_path: str) -> None:
    config["task"]["version"] = "v2"

    rename_key(config, "task", "samples_subdir", "static_subdir")
    rename_key(config, "tests", "solution_manager", "stub")

    subtask_points = []
    for section in sorted(config.sections()):
        if re.fullmatch(r"test[0-9]{2}", section):
            if "points" not in config[section]:
                raise TaskConfigError(f"Missing key 'points' in section [{section}]")
            subtask_points.append(int(config[section]["points"]))
    if "test00" not in config.sections():
        subtask_points = [0] + subtask_points

    if "solutions" not in config["task"]:
        raise TaskConfigError(f"Missing key 'solutions' in section [task]")
    solutions = config["task"]["solutions"].split()
    del config["task"]["solutions"]

    for i, solution in enumerate(solutions):
        if match := re.fullmatch(r"(.*?)_([0-9]{1,3}|X)b", solution):
            points = None if match[2] == "X" else int(match[2])
            if len(
                glob.glob(
                    os.path.join(
                        task_path,
                        config["task"].get("solutions_subdir", ""),
                        f"{solution}.*",
                    )
                )
            ):
                source = solution
            else:
                source = match[1]
        else:
            source = solution
            points = sum(subtask_points)

        if points is None:
            subtasks = "X" * len(subtask_points)
        else:
            subtasks = get_subtask_mask(points, subtask_points)

        solution = f"solution_{solution}"
        config.add_section(solution)
        if i == 0:
            config[solution]["primary"] = "yes"
            subtasks = "1" * len(subtask_points)
        config[solution]["source"] = source
        config[solution]["points"] = "X" if points is None else str(points)
        config[solution]["subtasks"] = subtasks

    subtask_inputs = {}
    in_globs_used = False
    for section in config.sections():
        if not (mat := re.fullmatch(r"test([0-9]{2})", section)):
            continue

        num = int(mat[1])
        if "in_globs" not in config[section]:
            if num == 0:
                subtask_inputs[num] = {"sample*.in"}
            else:
                subtask_inputs[num] = {f"{i:02}*.in" for i in range(1, num + 1)}
        else:
            in_globs_used = True
            subtask_inputs[num] = set(
                map(lambda x: x.replace("_*", "*"), config[section]["in_globs"].split())
            )

    last_subtask = max(subtask_inputs.keys())
    for subtask, inputs in subtask_inputs.items():
        if "0*.in" in inputs or "*.in" in inputs:
            subtask_inputs[subtask] = {
                f"{i:02}*.in" for i in range(1, last_subtask + 1)
            }

    # Now we construct ordering of subtask difficulty but without redundant edges

    # First construct edges
    subtask_includes: dict[int, set[int]] = {i: set([]) for i in subtask_inputs}
    for succ_subtask in subtask_inputs:
        for pred_subtask in subtask_inputs:
            if succ_subtask == pred_subtask:
                continue
            if subtask_inputs[succ_subtask] >= subtask_inputs[pred_subtask]:
                subtask_includes[succ_subtask].add(pred_subtask)

    # Then remove redundant edges
    for succ_subtask in subtask_includes:
        for pred_subtask in subtask_includes:
            if succ_subtask == pred_subtask:
                continue
            if pred_subtask in subtask_includes[succ_subtask]:
                subtask_includes[succ_subtask] -= subtask_includes[pred_subtask]

    if in_globs_used:
        for subtask in subtask_includes:
            subtask_section = config[f"test{subtask:02}"]
            subtask_section["predecessors"] = " ".join(
                map(str, subtask_includes[subtask])
            )

            in_globs = copy(subtask_inputs[subtask])
            for pred in subtask_includes[subtask]:
                in_globs -= subtask_inputs[pred]
            subtask_section["in_globs"] = " ".join(sorted(in_globs))


def get_subtask_mask(points, subtasks):
    all_valid = [0] * len(subtasks)

    valid = 0
    for comb in product([0, 1], repeat=len(subtasks)):
        p = sum([comb[i] * subtasks[i] for i in range(len(subtasks))])
        if p == points:
            valid += 1
            for i in range(len(subtasks)):
                all_valid[i] += comb[i]

    if valid == 0:
        return "X" * len(subtasks)

    sub_mask = ""
    for x in all_valid:
        if x == valid:
            sub_mask += "1"
        elif x == 0:
            sub_mask += "0"
        else:
            sub_mask += "X"
    return sub_mask


UPDATERS = {"v1": ("v2", update_to_v2)}
NEWEST_VERSION = "v2"


def update_config(
    config: ConfigParser, task_path: str, no_colors: bool = False
) -> None:
    version = config.get("task", "version", fallback="v1")
    if version == NEWEST_VERSION:
        return

    eprint(colored(f"Updating config to version {NEWEST_VERSION}", "yellow", no_colors))

    if version not in UPDATERS:
        raise TaskConfigError(f"Unknown version of config: {version}")

    while version in UPDATERS:
        version, updater = UPDATERS[version]
        updater(config, task_path)

    if version != NEWEST_VERSION:
        raise RuntimeError("Config updating failed.")
