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

from pisek.utils.text import eprint
from pisek.utils.colors import ColorSettings
from pisek.config.config_errors import TaskConfigError
from pisek.config.config_types import ProgramType


def maybe_rename_key(
    config: ConfigParser, section_from: str, section_to: str, key_from: str, key_to: str
):
    if section_from in config and key_from in config[section_from]:
        if section_to not in config:
            config.add_section(section_to)

        config[section_to][key_to] = config[section_from][key_from]
        del config[section_from][key_from]


def maybe_move_key(config: ConfigParser, key: str, section_from: str, section_to: str):
    maybe_rename_key(config, section_from, section_to, key, key)


def maybe_delete_key(config: ConfigParser, section: str, key: str):
    if section in config and key in config[section]:
        del config[section][key]


def update_to_v2(config: ConfigParser, task_path: str) -> None:
    maybe_rename_key(config, "task", "task", "samples_subdir", "static_subdir")
    maybe_rename_key(config, "tests", "tests", "solution_manager", "stub")

    subtask_points = []
    for section in sorted(config.sections()):
        if re.fullmatch(r"test[0-9]{2}", section):
            if "points" not in config[section]:
                raise TaskConfigError(f"Missing key 'points' in section [{section}]")
            subtask_points.append(int(config[section]["points"]))
    if "test00" not in config.sections():
        subtask_points = [0] + subtask_points

    if "solutions" not in config["task"]:
        raise TaskConfigError("Missing key 'solutions' in section [task]")
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


def update_to_v3(config: ConfigParser, task_path: str) -> None:
    contest_type = config.get("task", "contest_type", fallback="kasiopea")
    if contest_type not in ["kasiopea", "cms"]:
        raise TaskConfigError(f"Invalid contest_type: '{contest_type}'")
    config["task"]["use"] = f"@{contest_type}"
    maybe_delete_key(config, "task", "contest_type")

    maybe_delete_key(config, "task", "data_subdir")

    task_type = config.get("task", "task_type", fallback="batch")
    out_check = config.get("tests", "out_check")
    if contest_type == "cms" and out_check == "judge":
        if task_type == "batch":
            config["tests"]["judge_type"] = "cms-batch"
        elif task_type == "communication":
            config["tests"]["judge_type"] = "cms-communication"

    if task_type == "communication":
        config["task"]["task_type"] = "interactive"

    maybe_rename_key(config, "tests", "tests", "checker", "validator")

    OLD_NAME = {
        ProgramType.gen: "in_gen",
        ProgramType.validator: "checker",
        ProgramType.primary_solution: "solve",
        ProgramType.secondary_solution: "sec_solve",
        ProgramType.judge: "judge",
    }

    for new_program_type in ProgramType:
        old_program_type = OLD_NAME[new_program_type]
        if new_program_type == ProgramType.primary_solution:
            section = "run_solution"
        else:
            section = f"run_{new_program_type}"

        config.add_section(section)
        config[section]["clock_mul"] = "0"
        config[section]["clock_min"] = config.get(
            "limits", f"{old_program_type}_clock_limit", fallback="360"
        )
        maybe_delete_key(config, "limits", f"{old_program_type}_clock_limit")

        for limit in ("time", "mem", "process"):
            maybe_rename_key(
                config,
                "limits",
                section,
                f"{old_program_type}_{limit}_limit",
                f"{limit}_limit",
            )

    maybe_move_key(config, "stub", "tests", "cms")
    maybe_move_key(config, "headers", "tests", "cms")
    maybe_move_key(config, "static_subdir", "task", "tests")

    if contest_type == "cms":
        maybe_move_key(config, "name", "task", "cms")
    elif contest_type == "kasiopea":
        maybe_delete_key(config, "task", "name")

    IGNORED_KEYS = [
        ("task", "tests"),
        ("tests", "in_mode"),
        ("tests", "out_mode"),
        ("tests", "online_validity"),
    ]
    for section, key in IGNORED_KEYS:
        maybe_delete_key(config, section, key)

    maybe_rename_key(
        config,
        "checks",
        "checks",
        "solution_for_each_subtask",
        "solution_for_each_test",
    )
    maybe_rename_key(
        config,
        "checks",
        "checks",
        "all_inputs_in_last_subtask",
        "all_inputs_in_last_test",
    )

    for section in config.sections():
        if re.match(r"test\d{2}", section):
            maybe_delete_key(config, section, "file_name")
        if re.match(r"solution_(.+)", section):
            maybe_rename_key(config, section, section, "subtasks", "tests")
            maybe_rename_key(config, section, section, "source", "run")
            maybe_rename_key(config, section, section, "points_above", "points_min")
            maybe_rename_key(config, section, section, "points_below", "points_max")

    maybe_rename_key(config, "task", "run_solution", "solutions_subdir", "subdir")

    maybe_move_key(config, "name", "all_tests", "tests")
    maybe_move_key(config, "in_globs", "all_tests", "tests")
    maybe_move_key(config, "predecessors", "all_tests", "tests")


OUTDATED_VERSIONS = {"v1": ("v2", update_to_v2)}
CURRENT_VERSIONS = {"v2": ("v3", update_to_v3)}

NEWEST_VERSION = "v3"
NEWEST_IS_EXPERIMENTAL = True


def update_config(config: ConfigParser, task_path: str, infos: bool = True) -> None:
    def inform(msg: str):
        if infos:
            eprint(ColorSettings.colored(msg, "yellow"))

    version = config.get("task", "version", fallback="v1")
    if version == NEWEST_VERSION:
        if NEWEST_IS_EXPERIMENTAL:
            inform(
                f"Config format for version {NEWEST_VERSION} is experimental and can be changed"
            )
        return

    if version in OUTDATED_VERSIONS:
        inform(f"Updating config")

    updaters = OUTDATED_VERSIONS | CURRENT_VERSIONS
    if version not in updaters:
        raise TaskConfigError(f"Unknown version of config: {version}")

    while version in updaters:
        version, updater = updaters[version]
        updater(config, task_path)

    if version != NEWEST_VERSION:
        raise RuntimeError("Config updating failed.")

    config["task"]["version"] = NEWEST_VERSION
