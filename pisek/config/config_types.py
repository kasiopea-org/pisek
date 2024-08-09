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
    communication = auto()


class OutCheck(StrEnum):
    diff = auto()
    tokens = auto()
    judge = auto()


class GenType(StrEnum):
    opendata_v1 = "opendata-v1"
    cms_old = "cms-old"
    pisek_v1 = "pisek-v1"


class JudgeType(StrEnum):
    cms_batch = "cms-batch"
    cms_communication = "cms-communication"
    opendata_v1 = "opendata-v1"


class DataFormat(StrEnum):
    text = auto()
    binary = auto()


class Scoring(StrEnum):
    equal = auto()
    min = auto()


class ProgramType(StrEnum):
    tool = auto()
    in_gen = auto()
    checker = auto()
    solve = auto()
    sec_solve = auto()
    judge = auto()


class CMSFeedbackLevel(StrEnum):
    full = auto()
    restricted = auto()


class CMSScoreMode(StrEnum):
    max = auto()
    max_subtask = auto()
    max_tokened_last = auto()
