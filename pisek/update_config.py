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

import configparser
from copy import copy
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
        if re.fullmatch(r"test[0-9]{2}", section):
            if "points" not in config[section]:
                return f"Missing key 'points' in section [{section}]"
            subtask_points.append(int(config[section]["points"]))
    if "test00" not in config.sections():
        subtask_points = [0] + subtask_points

    if "solutions" not in config["task"]:
        return f"Missing key 'solutions' in section [task]"
    solutions = config["task"]["solutions"].split()
    del config["task"]["solutions"]

    for i, solution in enumerate(solutions):
        if match := re.fullmatch(r"(.*?)_([0-9]{1,3}|X)b", solution):
            points = None if match[2] == "X" else int(match[2])
            if len(
                glob.glob(
                    os.path.join(
                        path,
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
    subtask_includes = {i: set([]) for i in subtask_inputs}
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
            section = config[f"test{subtask:02}"]
            section["predecessors"] = " ".join(map(str, subtask_includes[subtask]))

            in_globs = copy(subtask_inputs[subtask])
            for pred in subtask_includes[subtask]:
                in_globs -= subtask_inputs[pred]
            section["in_globs"] = " ".join(sorted(in_globs))

    with open(config_path, "w") as f:
        config.write(f, space_around_delimiters=False)

    return None


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
