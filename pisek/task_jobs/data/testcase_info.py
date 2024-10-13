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
from enum import StrEnum, auto
from typing import Optional
import yaml

from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.utils.yaml_enum import yaml_enum


@yaml_enum
class TestcaseGenerationMode(StrEnum):
    static = auto()
    mixed = auto()
    generated = auto()


@dataclass(frozen=True)
class TestcaseInfo(yaml.YAMLObject):
    yaml_tag = "!TestcaseInfo"

    name: str
    repeat: int
    generation_mode: TestcaseGenerationMode
    seeded: bool

    @staticmethod
    def generated(name: str, repeat: int = 1, seeded: bool = True) -> "TestcaseInfo":
        return TestcaseInfo(name, repeat, TestcaseGenerationMode.generated, seeded)

    @staticmethod
    def mixed(name: str) -> "TestcaseInfo":
        return TestcaseInfo(name, 1, TestcaseGenerationMode.mixed, False)

    @staticmethod
    def static(name: str) -> "TestcaseInfo":
        return TestcaseInfo(name, 1, TestcaseGenerationMode.static, False)

    def input_path(self, env: Env, seed: Optional[int] = None) -> TaskPath:
        filename = self.name
        if self.seeded:
            assert seed is not None
            filename += f"_{seed:x}"
        filename += ".in"

        return TaskPath.input_path(env, filename)
