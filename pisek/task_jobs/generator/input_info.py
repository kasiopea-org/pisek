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

from dataclasses import dataclass
from typing import Optional
import yaml

from pisek.env.env import Env
from pisek.utils.paths import TaskPath


@dataclass(frozen=True)
class InputInfo(yaml.YAMLObject):
    yaml_tag = "!InputInfo"

    name: str
    repeat: int = 1
    is_generated: bool = True
    seeded: bool = True

    @staticmethod
    def generated(name: str, repeat: int = 1, seeded: bool = True) -> "InputInfo":
        return InputInfo(name, repeat, True, seeded)

    @staticmethod
    def static(name: str) -> "InputInfo":
        return InputInfo(name, 1, False, False)

    def task_path(self, env: Env, seed: Optional[int] = None) -> TaskPath:
        filename = self.name
        if self.seeded:
            assert seed is not None
            filename += f"_{seed:x}"
        filename += ".in"

        return TaskPath.input_path(env, filename)
