# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import StrEnum, auto
import fnmatch
from functools import cached_property
from pydantic_core import PydanticCustomError, ErrorDetails
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
from typing import Optional, Any, Annotated, Union

from pisek.utils.text import tab
from pisek.utils.text import eprint, colored, warn
from pisek.env.base_env import BaseEnv
from pisek.env.config_hierarchy import ConfigValue, TaskConfigError, ConfigHierarchy
from pisek.env.context import init_context
from pisek.jobs.parts.solution_result import SUBTASK_SPEC


MaybeInt = Annotated[
    Optional[int], BeforeValidator(lambda i: (None if i == "X" else i))
]
ListStr = Annotated[list[str], BeforeValidator(lambda s: s.split())]
OptionalStr = Annotated[Optional[str], BeforeValidator(lambda s: s or None)]


class TaskType(StrEnum):
    batch = auto()
    communication = auto()


class JudgeType(StrEnum):
    diff = auto()
    judge = auto()


class FailMode(StrEnum):
    all = auto()
    any = auto()


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


ValuesDict = dict[str, Union[str, "ValuesDict", dict[Any, "ValuesDict"]]]
ConfigValuesDict = dict[
    str, Union[ConfigValue, "ConfigValuesDict", dict[Any, "ConfigValuesDict"]]
]


def _to_values(config_values_dict: ConfigValuesDict) -> ValuesDict:
    def convert(what: ConfigValue | dict) -> str | dict:
        if isinstance(what, ConfigValue):
            return what.value
        else:
            return {key: convert(val) for key, val in what.items()}

    return {key: convert(val) for key, val in config_values_dict.items()}


class TaskConfig(BaseEnv):
    """Configuration of task loaded from config file."""

    name: str
    contest_type: str
    task_type: TaskType
    fail_mode: FailMode

    solutions_subdir: str
    static_subdir: str
    data_subdir: str

    in_gen: str
    checker: OptionalStr
    out_check: JudgeType
    out_judge: Optional[str]
    judge_needs_in: bool
    judge_needs_out: bool

    stub: OptionalStr
    headers: ListStr

    subtasks: dict[int, "SubtaskConfig"]

    solutions: dict[str, "SolutionConfig"]

    limits: "LimitsConfig"

    cms: "CMSConfig"

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

    def get_solution_by_source(self, source: str) -> Optional[str]:
        sources = (name for name, sol in self.solutions.items() if sol.source == source)
        return next(sources, None)

    def __init__(self, **kwargs):
        value = {"subtask_count": max(kwargs["subtasks"]) + 1, "name": kwargs["name"]}

        with init_context(value):
            super().__init__(**kwargs)

    @staticmethod
    def load_dict(configs: ConfigHierarchy) -> ConfigValuesDict:
        GLOBAL_KEYS = [
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
        JUDGE_KEYS = [
            ("out_judge", None),
            ("judge_needs_in", "0"),
            ("judge_needs_out", "1"),
        ]
        args: dict[str, Any] = {
            key: configs.get(section, key) for section, key in GLOBAL_KEYS
        }

        args["fail_mode"] = ConfigValue(
            "any" if args["contest_type"].value == "cms" else "all",
            config="_internal",
            section="task",
            key="fail_mode",
            internal=True,
        )  # TODO: Add fail_mode to config

        # Load judge specific keys
        for key, default in JUDGE_KEYS:
            if args["out_check"].value == "judge":
                args[key] = configs.get("tests", key)
            else:
                args[key] = ConfigValue(default, "_internal", "tests", key, True)

        section_names = configs.sections()

        # Load subtasks
        args["subtasks"] = subtasks = {}
        for section in sorted(section_names, key=lambda cv: cv.value):
            section_name = section.value
            if m := re.match(r"test(\d{2})", section_name):
                num = m[1]
                subtasks[int(num)] = SubtaskConfig.load_dict(
                    ConfigValue(num, section.config, section.section, None), configs
                )

        args["solutions"] = solutions = {}
        for section in section_names:
            if m := re.match(r"solution_(.+)", section.value):
                solutions[m[1]] = SolutionConfig.load_dict(
                    ConfigValue(m[1], section.config, section.section, None), configs
                )

        args["limits"] = LimitsConfig.load_dict(configs)
        args["cms"] = CMSConfig.load_dict(configs)

        return args

    @field_validator("contest_type", mode="after")
    @classmethod
    def validate_contest_type(cls, value: str) -> str:
        # TODO: Redo to general task types
        ALLOWED = ["kasiopea", "cms"]
        if value not in ALLOWED:
            raise PydanticCustomError(
                "contest_type_invalid",
                f"Must be one of ({', '.join(ALLOWED)})",
            )
        return value

    @model_validator(mode="after")
    def validate_model(self):
        if (
            self.task_type == TaskType.communication
            and self.out_check != JudgeType.judge
        ):
            raise PydanticCustomError(
                "communication_must_have_judge",
                f"For communication task 'out_check' must be 'judge'",
                {"task_type": self.task_type, "out_check": self.out_check},
            )

        primary = [name for name, sol in self.solutions.items() if sol.primary]
        if len(primary) > 1:
            raise PydanticCustomError(
                "multiple_primary_solutions",
                "Multiple primary solutions",
                {"primary_solutions": primary},
            )
        if len(self.solutions) > 0 and len(primary) == 0:
            raise PydanticCustomError(
                "no_primary_solution",
                "No primary solution set",
                {},
            )

        for i in range(len(self.subtasks)):
            if i not in self.subtasks:
                raise PydanticCustomError(
                    "missing_subtask",
                    f"Missing section for subtask {i}",
                    {},
                )

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
                raise PydanticCustomError(
                    "cyclic_predecessor_subtasks", "Cyclic predecessor subtasks", {}
                )

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
    """Configuration of one subtask."""

    _section: str
    num: int
    name: str
    points: int = Field(ge=0)
    in_globs: ListStr
    all_globs: list[str] = []
    predecessors: list[int]

    def in_subtask(self, filename: str) -> bool:
        return any(fnmatch.fnmatch(filename, g) for g in self.all_globs)

    def new_in_subtask(self, filename: str) -> bool:
        return any(fnmatch.fnmatch(filename, g) for g in self.in_globs)

    @staticmethod
    def load_dict(number: ConfigValue, configs: ConfigHierarchy) -> ConfigValuesDict:
        KEYS = ["name", "points", "in_globs", "predecessors"]
        num = int(number.value)
        args: dict[str, Any]
        if num == 0:
            args = {key: configs.get(number.section, key) for key in KEYS}
        else:
            args = {
                key: configs.get_from_candidates(
                    [(number.section, key), ("all_tests", key)]
                )
                for key in KEYS
            }
        return {"_section": configs.get(number.section, None), "num": number, **args}

    @field_validator("in_globs", mode="after")
    @classmethod
    def validate_globs(cls, value: list[str], info: ValidationInfo) -> list[str]:
        globs = []
        for glob in value:
            if glob == "@ith":
                glob = f"{info.data['num']:02}*.in"
            if not glob.endswith(".in"):
                raise PydanticCustomError(
                    "in_globs_end_in", "In_globs must end with '.in'"
                )
            globs.append(glob)

        return globs

    @field_validator("predecessors", mode="before")
    @classmethod
    def expand_predecessors(cls, value: str, info: ValidationInfo) -> list[str]:
        if info.context is None:
            raise RuntimeError("Missing validation context.")
        subtask_cnt = info.context.get("subtask_count")
        number = info.data["num"]

        predecessors = []
        for pred in value.split():
            if pred == "@previous":
                if number <= 1:
                    continue
                predecessors.append(number - 1)
            else:
                try:
                    num = int(pred)
                except ValueError:
                    raise PydanticCustomError(
                        "predecessors_must_be_int", "Predecessors must be int"
                    )
                if not 0 <= num < subtask_cnt:
                    raise PydanticCustomError(
                        "predecessors_must_be_in_range",
                        f"Predecessors must be in range 0, {subtask_cnt-1}",
                    )
                predecessors.append(num)

        return list(sorted(set(predecessors)))

    @model_validator(mode="after")
    def validate_model(self):
        if self.name == "@auto":
            self.name = f"Subtask {self.num}"

        return self


class SolutionConfig(BaseEnv):
    """Configuration of one solution."""

    _section: str
    name: str
    primary: bool
    source: str
    points: MaybeInt
    points_above: MaybeInt
    points_below: MaybeInt
    subtasks: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def load_dict(cls, name: ConfigValue, configs: ConfigHierarchy) -> ConfigValuesDict:
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
                [(name.section, key), ("all_solutions", key)]
            )
            for key in KEYS
        }
        return {"_section": configs.get(name.section, None), "name": name, **args}

    @field_validator("name", mode="after")
    @classmethod
    def convert_checker(cls, value: str) -> str:
        for banned_char in ".[]":
            if banned_char in value:
                raise PydanticCustomError(
                    "invalid_solution_name",
                    f"Solution name must not contain '{banned_char}'",
                )
        return value

    @field_validator("primary", mode="before")
    @classmethod
    def convert_yesno(cls, value: str, info: ValidationInfo) -> bool:
        if value == "yes":
            return True
        elif value == "no":
            return False
        raise PydanticCustomError(
            "primary_invalid",
            f"Must be one of (yes, no)",
        )

    @field_validator("source", mode="before")
    @classmethod
    def convert_auto(cls, value: str, info: ValidationInfo) -> str:
        if value == "@auto":
            return info.data.get("name", "")
        return value

    @field_validator("subtasks", mode="after")
    def validate_subtasks(cls, value, info: ValidationInfo):
        if info.context is None:
            raise RuntimeError("Missing validation context.")
        subtask_cnt = info.context.get("subtask_count")
        primary = info.data.get("primary")
        if value == "@auto":
            value = ("1" if primary else "X") * subtask_cnt
        elif value == "@all":
            value = "1" * subtask_cnt
        elif value == "@any":
            value = "X" * subtask_cnt

        if len(value) != subtask_cnt:
            raise PydanticCustomError(
                "subtasks_str_invalid_len",
                f"There are {subtask_cnt} subtasks but subtask string has {len(value)} characters",
            )

        for char in value:
            if char not in SUBTASK_SPEC:
                raise PydanticCustomError(
                    "subtasks_str_invalid_char",
                    f"Not allowed char in subtask string: {char}. Recognized are {''.join(SUBTASK_SPEC.keys())}",
                )

        if primary and value != "1" * subtask_cnt:
            raise PydanticCustomError(
                "primary_sol_must_succeed",
                f"Primary solution must have: subtasks={'1'*subtask_cnt}",
            )

        return value

    @model_validator(mode="after")
    def validate_model(self):
        for points_limit in ["points_above", "points_below"]:
            if self.points is not None and getattr(self, points_limit) is not None:
                raise PydanticCustomError(
                    "points_double_set",
                    f"Both 'points' and '{points_limit}' are set at once",
                    {"points": self.points, points_limit: getattr(self, points_limit)},
                )

        return self


class ProgramLimits(BaseEnv):
    """Configuration of limits of one program type."""

    _section: str = "limits"

    time_limit: float = Field(ge=0)  # [seconds]
    clock_limit: float = Field(ge=0)  # [seconds]
    mem_limit: int = Field(ge=0)  # [KB]
    process_limit: int = Field(ge=0)
    # limit=0 means unlimited

    @classmethod
    def load_dict(cls, part: ProgramType, configs: ConfigHierarchy) -> ConfigValuesDict:
        def get_limit(limit: str) -> ConfigValue:
            if part == ProgramType.sec_solve:
                return configs.get_from_candidates(
                    [("limits", f"{part.name}_{limit}"), ("limits", f"solve_{limit}")]
                )
            else:
                return configs.get("limits", f"{part.name}_{limit}")

        args: dict[str, Any] = {limit: get_limit(limit) for limit in cls.model_fields}

        return args


class LimitsConfig(BaseEnv):
    """Configuration of limits for all program types."""

    _section: str = "limits"

    tool: ProgramLimits
    in_gen: ProgramLimits
    checker: ProgramLimits
    solve: ProgramLimits
    sec_solve: ProgramLimits
    judge: ProgramLimits
    input_max_size: int
    output_max_size: int

    @classmethod
    def load_dict(cls, configs: ConfigHierarchy) -> ConfigValuesDict:
        args: dict[str, Any] = {}
        for part in ProgramType:
            args[part.name] = ProgramLimits.load_dict(part, configs)

        for file_type in ("input", "output"):
            key = f"{file_type}_max_size"
            args[key] = configs.get("limits", key)

        return args


class CMSConfig(BaseEnv):
    _section: str = "cms"

    title: str
    submission_format: ListStr

    time_limit: float = Field(gt=0)  # [seconds]
    mem_limit: int = Field(gt=0)  # [KB]

    max_submissions: MaybeInt = Field(gt=0)
    min_submission_interval: int = Field(ge=0)  # [seconds]

    score_precision: int = Field(ge=0)
    score_mode: CMSScoreMode
    feedback_level: CMSFeedbackLevel

    @classmethod
    def load_dict(cls, configs: ConfigHierarchy) -> ConfigValuesDict:
        KEYS = [
            "title",
            "submission_format",
            "time_limit",
            "mem_limit",
            "max_submissions",
            "min_submission_interval",
            "score_precision",
            "score_mode",
            "feedback_level",
        ]

        return {key: configs.get("cms", key) for key in KEYS}

    @field_validator("title", mode="before")
    @classmethod
    def convert_title(cls, value: str, info: ValidationInfo) -> str:
        if value == "@name":
            if info.context is None:
                raise RuntimeError("Missing validation context.")

            return info.context.get("name")
        else:
            return value

    @field_validator("submission_format", mode="after")
    @classmethod
    def convert_format(cls, value: list[str], info: ValidationInfo) -> list[str]:
        if info.context is None:
            raise RuntimeError("Missing validation context.")

        return [
            (
                CMSConfig.get_default_file_name(info.context.get("name"))
                if n == "@name"
                else n
            )
            for n in value
        ]

    @classmethod
    def get_default_file_name(cls, name: str):
        name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
        return f"{name}.%l"


def _format_message(err: ErrorDetails) -> str:
    inp = err["input"]
    ctx = err["ctx"] if "ctx" in err else None
    if isinstance(inp, dict) and ctx is not None:
        if ctx == {}:
            return f"{err['msg']}."
        return f"{err['msg']}:\n" + tab(
            "\n".join(f"{key}={val}" for key, val in ctx.items())
        )
    return f"{err['msg']}: '{inp}'"


def _convert_errors(e: ValidationError, config_values: ConfigValuesDict) -> list[str]:
    error_msgs: list[str] = []
    for error in e.errors():
        value: Any = config_values
        for loc in error["loc"]:
            value = value[loc]

        if not isinstance(value, ConfigValue):
            location = (
                value["_section"].location()
                if "_section" in value
                else "Global config error:"
            )
        else:
            location = value.location()

        error_msgs.append(f"In {location}:\n" + tab(_format_message(error)))
    return error_msgs


def load_config(
    path: str,
    strict: bool = False,
    no_colors: bool = False,
    suppress_warnings: bool = False,
) -> Optional[TaskConfig]:
    """Loads config from given path."""
    try:
        config_hierarchy = ConfigHierarchy(path, no_colors)
        config_values = TaskConfig.load_dict(config_hierarchy)
        config = TaskConfig(**_to_values(config_values))
        config_hierarchy.check_unused_keys()
        if config_hierarchy.check_todos() and not suppress_warnings:
            warn("Unsolved TODOs in config.", TaskConfigError, strict, no_colors)
        return config
    except TaskConfigError as err:
        eprint(colored(str(err), "red", no_colors))
    except ValidationError as err:
        eprint(
            colored(
                "Invalid config:\n\n"
                + "\n\n".join(_convert_errors(err, config_values)),
                "red",
                no_colors,
            )
        )
    return None
