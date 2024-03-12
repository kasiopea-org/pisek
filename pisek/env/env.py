# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
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
from typing import Optional

from pisek.utils.text import eprint, colored
from pisek.env.base_env import BaseEnv
from pisek.env.task_config import load_config, TaskConfig
from pisek.env.select_solutions import expand_solutions, UnknownSolutions


class TestingTarget(StrEnum):
    all = auto()
    generator = auto()
    solution = auto()


class Env(BaseEnv):
    """
    Collection of environment variables for task testing.

    Attributes:
        target: What is being tested
        config: Environment variables defined by task config
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
        target: str = TestingTarget.all,
        full: bool = False,
        all_inputs: bool = False,
        skip_on_timeout: bool = False,
        plain: bool = False,
        no_jumps: bool = False,
        no_colors: bool = False,
        strict: bool = False,
        testing_log: bool = False,
        solutions: Optional[list[str]] = None,
        timeout: Optional[float] = None,
        inputs: int = 5,
        **_,
    ) -> Optional["Env"]:
        no_jumps |= plain
        no_colors |= plain

        config = load_config(".", strict, no_colors)
        if config is None:
            return None

        try:
            expanded_solutions = expand_solutions(config, solutions)
        except UnknownSolutions as err:
            eprint(colored(str(err), "red", no_colors))
            return None

        return Env(
            target=TestingTarget(target),
            config=config,
            full=full,
            no_jumps=no_jumps,
            no_colors=no_colors,
            strict=strict,
            testing_log=testing_log,
            solutions=expanded_solutions,
            timeout=timeout,
            skip_on_timeout=skip_on_timeout,
            all_inputs=all_inputs,
            inputs=inputs,
        )
