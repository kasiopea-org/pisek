# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

from enum import StrEnum, auto


class TaskType(StrEnum):
    batch = auto()
    interactive = auto()


class OutCheck(StrEnum):
    diff = auto()
    tokens = auto()
    shuffle = auto()
    judge = auto()


class GenType(StrEnum):
    opendata_v1 = "opendata-v1"
    cms_old = "cms-old"
    pisek_v1 = "pisek-v1"


class JudgeType(StrEnum):
    cms_batch = "cms-batch"
    cms_communication = "cms-communication"
    opendata_v1 = "opendata-v1"


class ShuffleMode(StrEnum):
    lines = auto()
    words = auto()
    lines_words = auto()
    tokens = auto()


class DataFormat(StrEnum):
    text = auto()
    strict_text = "strict-text"
    binary = auto()


class ProgramType(StrEnum):
    gen = auto()
    validator = auto()
    primary_solution = auto()
    secondary_solution = auto()
    judge = auto()

    def is_solution(self) -> bool:
        return self in (ProgramType.primary_solution, ProgramType.secondary_solution)


class BuildStrategyName(StrEnum):
    python = auto()
    cpp = auto()
    auto = auto()


class CMSFeedbackLevel(StrEnum):
    full = auto()
    restricted = auto()


class CMSScoreMode(StrEnum):
    max = auto()
    max_subtask = auto()
    max_tokened_last = auto()
