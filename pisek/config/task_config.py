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
from functools import cached_property
from pydantic import (
    Field,
    computed_field,
    field_validator,
    BeforeValidator,
    ValidationError,
    ValidationInfo,
    model_validator,
)
import re
from typing import Optional, Any, Annotated, Iterator

from pisek.utils.text import tab
from pisek.config.base_env import BaseEnv
from pisek.config.config_errors import TaskConfigError
from pisek.config.config_hierarchy import ConfigHierarchy
from pisek.config.context import init_context
from pisek.jobs.parts.solution_result import SUBTASK_SPEC


DEFAULT_TIMEOUT: float = 360.0
CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"


MaybeInt = Annotated[
    Optional[int], BeforeValidator(lambda i: (None if i == "X" else i))
]
ListStr = Annotated[list[str], BeforeValidator(lambda s: s.split())]


class ProgramType(StrEnum):
    tool = auto()
    in_gen = auto()
    checker = auto()
    solve = auto()
    sec_solve = auto()
    judge = auto()


class JudgeType(StrEnum):
    diff = auto()
    judge = auto()


class FailMode(StrEnum):
    all = auto()
    any = auto()


class TaskConfig(BaseEnv):
    name: str
    contest_type: str
    task_type: str
    fail_mode: FailMode

    solutions_subdir: str
    static_subdir: str
    data_subdir: str

    in_gen: str
    checker: str
    out_check: JudgeType
    out_judge: Optional[str]
    judge_needs_in: bool
    judge_needs_out: bool

    stub: Optional[str]
    headers: ListStr

    subtasks: dict[int, "SubtaskConfig"]

    solutions: dict[str, "SolutionConfig"]

    limits: "LimitsConfig"

    @computed_field  # type: ignore[misc]
    @cached_property
    def total_points(self) -> int:
        return sum(sub.points for sub in self.subtasks.values())

    @computed_field  # type: ignore[misc]
    @property
    def subtasks_count(self) -> int:
        return len(self.subtasks)

    @computed_field  # type: ignore[misc]
    @cached_property
    def input_globs(self) -> list[str]:
        return sum((sub.all_globs for sub in self.subtasks.values()), start=[])

    @computed_field  # type: ignore[misc]
    @property
    def primary_solution(self) -> str:
        if len(self.solutions) == 0:
            raise RuntimeError("No solutions exist.")
        else:
            return [name for name, sol in self.solutions.items() if sol.primary][0]

    @staticmethod
    def load(configs: ConfigHierarchy) -> "TaskConfig":
        KEYS = [
            ("task", "name"),
            ("task", "contest_type"),
            ("task", "task_type"),
            ("task", "solutions_subdir"),
            ("task", "static_subdir"),
            ("task", "data_subdir"),
            ("tests", "in_gen"),
            ("tests", "checker"),
            ("tests", "out_check"),
            ("tests", "stub"),
            ("tests", "headers"),
        ]
        args: dict[str, Any] = {key: configs.get(section, key) for section, key in KEYS}

        args["fail_mode"] = "any" if args["contest_type"] == "cms" else "all"

        # Load judge specific keys
        JUDGE_KEYS = [
            ("out_judge", None),
            ("judge_needs_in", "0"),
            ("judge_needs_out", "1"),
        ]
        for key, default in JUDGE_KEYS:
            if args["out_check"] == "judge":
                args[key] = configs.get("tests", key)
            else:
                args[key] = default

        section_names = configs.sections()

        # Load subtasks
        args["subtasks"] = subtasks = {}
        for section_name in sorted(section_names):
            if m := re.match(r"test(\d{2})", section_name):
                num = int(m[1])
                subtasks[num] = SubtaskConfig.load(num, configs)

        args["solutions"] = solutions = {}
        for section_name in section_names:
            if m := re.match(r"solution_(.+)", section_name):
                solutions[m[1]] = SolutionConfig.load(m[1], max(subtasks) + 1, configs)

        args["limits"] = LimitsConfig.load(configs)

        return TaskConfig(**args)

    @model_validator(mode="after")
    def validate_model(self):
        if self.task_type == "communication" and self.judge_type != JudgeType.judge:
            raise TaskConfigError(
                f"For communication task 'out_check' must be 'judge'."
            )

        primary = [name for name, sol in self.solutions.items() if sol.primary]
        if len(primary) > 2:
            primary_sols_list = tab("\n".join(primary))
            raise TaskConfigError(f"Multiple primary solutions:\n{primary_sols_list}")
        if len(self.solutions) > 0 and len(primary) == 0:
            raise TaskConfigError("No primary solution set.")

        for i in range(len(self.subtasks)):
            if i not in self.subtasks:
                raise TaskConfigError(f"Missing section for subtask {i}.")

        self._compute_all_globs()

        return self

    def _compute_all_globs(self) -> None:
        visited = set()
        computed = set()

        def compute_subtask(num: int) -> list[str]:
            subtask = self.subtasks[num]
            if num in computed:
                return subtask.all_globs
            elif num in visited:
                raise TaskConfigError("Cyclic predecessors subtasks.")

            visited.add(num)
            all_globs = sum(
                (compute_subtask(p) for p in subtask.predecessors),
                start=subtask.in_globs,
            )
            subtask.all_globs = list(sorted(set(all_globs)))
            computed.add(num)

            return subtask.all_globs

        for i in range(self.subtasks_count):
            compute_subtask(i)


class SubtaskConfig(BaseEnv):
    num: int
    name: str
    points: int = Field(ge=0)
    in_globs: ListStr
    all_globs: list[str] = []
    predecessors: list[int]

    @staticmethod
    def load(number: int, configs: ConfigHierarchy) -> "SubtaskConfig":
        KEYS = ["name", "points", "in_globs", "predecessors"]
        section = f"test{number:02}"
        args: dict[str, Any]
        if number == 0:
            args = {key: configs.get(section, key) for key in KEYS}
        else:
            args = {
                key: configs.get_from_candidates([(section, key), ("all_tests", key)])
                for key in KEYS
            }
        return SubtaskConfig(num=number, **args)

    @field_validator("in_globs", mode="after")
    @classmethod
    def validate_globs(cls, value: list[str], info: ValidationInfo) -> list[str]:
        globs = []
        for glob in value:
            if glob == "@ith":
                glob = f"{info.data['num']:02}*.in"
            if not glob.endswith(".in"):
                raise TaskConfigError(f"In_globs must end with '.in': {glob}")
            globs.append(glob)

        return globs

    @field_validator("predecessors", mode="before")
    @classmethod
    def expand_predecessors(cls, value: str, info: ValidationInfo) -> list[str]:
        number = info.data["num"]

        predecessors = []
        for pred in value.split():
            if pred == "@previous":
                if number <= 1:
                    continue
                predecessors.append(number - 1)
            else:
                predecessors.append(int(pred))

        return list(sorted(set(predecessors)))


class SolutionConfig(BaseEnv):
    name: str
    primary: bool
    source: str  # TODO: Change this to TaskPath
    points: MaybeInt
    points_above: MaybeInt
    points_below: MaybeInt
    subtasks: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def load(
        cls, name: str, subtask_count: int, configs: ConfigHierarchy
    ) -> "SolutionConfig":
        KEYS = [
            "primary",
            "source",
            "points",
            "points_above",
            "points_below",
            "subtasks",
        ]
        args = {
            key: configs.get_from_candidates(
                [(f"solution_{name}", key), ("all_solutions", key)]
            )
            for key in KEYS
        }
        with init_context({"subtask_count": subtask_count}):
            return SolutionConfig(name=name, **args)

    @field_validator("primary", mode="before")
    @classmethod
    def convert_yesno(cls, value: str, info: ValidationInfo) -> bool:
        if value == "yes":
            return True
        elif value == "no":
            return False
        raise TaskConfigError(
            f"Key 'primary' of solution {info.data['name']} should be one of (yes, no): {value}"
        )

    @field_validator("source", mode="before")
    @classmethod
    def convert_auto(cls, value: str, info: ValidationInfo) -> str:
        if value == "@auto":
            return info.data["name"]
        return value

    @field_validator("subtasks", mode="after")
    def validate_subtasks(cls, value, info: ValidationInfo):
        if info.context is None:
            raise RuntimeError("Missing validation context.")
        subtask_cnt = info.context.get("subtask_count")
        primary = info.data.get("primary")
        if value == "@auto":
            value = ("1" if primary else "0") * subtask_cnt
        elif value == "@all":
            value = "1" * subtask_cnt
        elif value == "@any":
            value = "0" * subtask_cnt

        if len(value) != subtask_cnt:
            raise TaskConfigError(
                f"There are {subtask_cnt} subtasks but subtask string has {len(value)} characters: '{value}'"
            )

        for char in value:
            if char not in SUBTASK_SPEC:
                raise TaskConfigError(
                    f"Not allowed char in subtask string: {char}\nRecognized are {''.join(SUBTASK_SPEC.keys())}"
                )

        if primary and value != "1" * subtask_cnt:
            raise TaskConfigError(
                f"Primary solution must have: subtasks={'1'*subtask_cnt}"
            )

        return value

    @model_validator(mode="after")
    def validate_model(self):
        for points_limit in ["points_above", "points_below"]:
            if self.points is not None and getattr(self, points_limit) is not None:
                raise TaskConfigError(
                    f"Both 'points' and '{points_limit}' are set at once."
                )

        return self


class ProgramLimits(BaseEnv):
    time_limit: float = Field(ge=0)
    clock_limit: float = Field(ge=0)
    mem_limit: int = Field(ge=0)
    process_limit: int = Field(ge=0)

    @classmethod
    def load(cls, part: ProgramType, configs: ConfigHierarchy) -> "ProgramLimits":
        def get_limit(limit: str) -> str:
            if part == ProgramType.sec_solve:
                return configs.get_from_candidates(
                    [("limits", f"{part.name}_{limit}"), ("limits", f"solve_{limit}")]
                )
            else:
                return configs.get("limits", f"{part.name}_{limit}")

        args: dict[str, Any] = {limit: get_limit(limit) for limit in cls.model_fields}

        return ProgramLimits(**args)


class LimitsConfig(BaseEnv):
    tool: ProgramLimits
    in_gen: ProgramLimits
    checker: ProgramLimits
    solve: ProgramLimits
    sec_solve: ProgramLimits
    judge: ProgramLimits
    input_max_size: int
    output_max_size: int

    @classmethod
    def load(cls, configs: ConfigHierarchy) -> "LimitsConfig":
        args: dict[str, Any] = {}
        for part in ProgramType:
            args[part.name] = ProgramLimits.load(part, configs)

        for file_type in ("input", "output"):
            key = f"{file_type}_max_size"
            args[key] = configs.get("limits", key)

        return LimitsConfig(**args)


def load_config(path: str) -> Optional[TaskConfig]:
    # TODO: Check unused keys and env
    return TaskConfig.load(ConfigHierarchy(path))
