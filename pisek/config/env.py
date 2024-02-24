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

from enum import StrEnum, auto
from pydantic import Field
from typing import Any, TYPE_CHECKING, Optional

from pisek.config.base_env import BaseEnv
from pisek.config.task_config import TaskConfig
from pisek.config.config_hierarchy import ConfigHierarchy


class TestingTarget(StrEnum):
    all = auto()
    generator = auto()
    solution = auto()


class Env(BaseEnv):
    """
    Collection of environment variables for task testing

    Attributes:
        task_dir: Directory of the task being tested
        target: What is being tested
        config: environment variables defined by task config
        full: Whether to stop after the first failure
        no_colors: If not to use ansi colors
        no_jumps: If not to use ansi control sequences
        strict: Whether to interpret warnings as failures
        testing_log: Whether to produce testing_log.json after running
        solutions: List of all solutions to be tested
        timeout: Timeout for (overrides config)
        skip_on_timeout: If to skip testing after solutions fails on one output (Useful only if fail_mode=all)
        all_inputs: Finish testing all inputs of a solution
        inputs: Number of inputs generated (Only for task_type=kasiopea)
    """

    task_dir: str
    target: TestingTarget
    config: TaskConfig
    full: bool
    no_colors: bool
    no_jumps: bool
    strict: bool
    testing_log: bool
    solutions: list[str]
    timeout: Optional[float] = Field(ge=0)
    skip_on_timeout: bool
    all_inputs: bool
    inputs: int = Field(ge=1)

    @staticmethod
    def load(
        task_dir: str,
        target: str,
        full: bool,
        all_inputs: bool,
        skip_on_timeout: bool,
        plain: bool,
        no_jumps: bool,
        no_colors: bool,
        strict: bool,
        testing_log: bool,
        solutions: Optional[list[str]],
        timeout: Optional[float],
        inputs: int,
        **_
    ) -> "Env":
        config = TaskConfig.load(ConfigHierarchy(task_dir))

        if solutions is None:
            expanded_solutions = list(config.solutions)
        else:
            expanded_solutions = solutions[:]
            if config.primary_solution not in expanded_solutions:
                expanded_solutions.append(config.primary_solution)

        # TODO: Expand solutions
        return Env(
            task_dir=task_dir,
            target=TestingTarget(target),
            config=config,
            full=full,
            no_jumps=plain or no_jumps,
            no_colors=plain or no_colors,
            strict=strict,
            testing_log=testing_log,
            solutions=expanded_solutions,
            timeout=timeout,
            skip_on_timeout=skip_on_timeout,
            all_inputs=all_inputs,
            inputs=inputs,
        )
