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

from enum import Enum
from typing import Any, TYPE_CHECKING
from pydantic import BaseModel, Field


class TestingTarget(Enum):
    all = 1
    generator = 2
    solution = 3


class BaseEnv(BaseModel):
    """
    Collection of enviroment variables which logs whether each variable was accessed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._locked: bool = False
        self._accessed: set[str] = set([])

    if not TYPE_CHECKING:
        def __getattr__(self, item: str) -> Any:
            self._accessed.add(item)
            return super().__getattr__(item)

    def fork(self):
        """
        Make copy of this env overriding variables specified in **kwargs.

        Accesses to env's variables (to this point) are logged in forked env as well.
        Subsequent accesses are logged only to respective BaseEnv.
        """
        if self._locked:
            raise RuntimeError("Locked BaseEnv cannot be forked.")

        model = self.model_copy(deep=True)
        model._clear_accesses()
        return model

    def _clear_accesses(self):
        """Removes all logged accesses."""
        self._accessed = set([])
        for key in self.model_fields():
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                item._clear_accesses()

    def lock(self) -> "BaseEnv":
        """Lock this BaseEnv and all subenvs so they cannot be forked."""
        self._locked = True
        for key in self.model_fields():
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                item.lock()

        return self

    def get_accessed(self) -> list[tuple[str, Any]]:
        """Get all accessed variables in this env and all subenvs with their values."""
        accessed = []
        for key in self._accessed:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                accessed += [(f"{key}.{subkey}", val) for subkey, val in item.get_accessed()]
            else:
                accessed.append((key, item))

        return accessed


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
    # TODO config: Config
    full: bool
    no_colors: bool
    no_jumps: bool
    strict: bool
    testing_log: bool
    solutions: list[str]
    timeout: float = Field(ge=0)
    skip_on_timeout: bool
    all_inputs: bool
    inputs: int = Field(ge=1)


    pass
