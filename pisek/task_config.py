import configparser
import os
import re
from typing import List, Dict, Optional, TypeVar, Callable

CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"


class TaskConfig:
    def __init__(self, task_dir: str) -> None:
        config = configparser.ConfigParser()
        config_path = os.path.join(task_dir, CONFIG_FILENAME)
        read_files = config.read(config_path)
        self.task_dir = task_dir

        if not read_files:
            raise FileNotFoundError(
                f"Chybí konfigurační soubor {config_path}, je toto složka s úlohou?"
            )

        try:
            self.solutions: List[str] = config["task"]["solutions"].split()
            self.contest_type = config["task"].get("contest_type", "kasiopea")
            self.generator: str = config["tests"]["in_gen"]
            self.checker: Optional[str] = config["tests"].get("checker")
            self.judge_type: str = config["tests"].get("out_check", "diff")
            self.judge_name: Optional[str] = None
            if self.judge_type == "judge":
                self.judge_name = config["tests"]["out_judge"]

            # Relevant for CMS interactive tasks. The file to be linked with
            # the contestant's solution (primarily for C++)
            self.solution_manager: str = config["tests"].get("solution_manager")
            if self.solution_manager:
                self.solution_manager = os.path.join(
                    self.task_dir, self.solution_manager
                )

            # Warning: these timeouts are currently ignored in Kasiopea!
            self.timeout_model_solution: Optional[float] = apply_to_optional(
                config.get("limits", "solve_time_limit", fallback=None), float
            )
            self.timeout_other_solutions: Optional[float] = apply_to_optional(
                config.get("limits", "sec_solve_time_limit", fallback=None), float
            )

            # Support for different directory structures
            self.samples_subdir: str = config["task"].get("samples_subdir", ".")
            self.data_subdir: str = config["task"].get("data_subdir", DATA_SUBDIR)

            if "solutions_subdir" in config["task"]:
                # Prefix each solution name with solutions_subdir/
                subdir = config["task"].get("solutions_subdir", ".")
                self.solutions = [os.path.join(subdir, sol) for sol in self.solutions]

            self.subtasks: Dict[int, SubtaskConfig] = {}
            for section_name in config.sections():
                m = re.match(r"test([0-9]{2})", section_name)

                if not m:
                    # One of the other sections ([task], [tests]...)
                    continue

                n = int(m.groups()[0])
                if n in self.subtasks:
                    raise ValueError("Duplicate subtask number {}".format(n))

                self.subtasks[n] = SubtaskConfig(
                    self.contest_type, config[section_name]
                )

        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e

    def get_maximum_score(self) -> int:
        return sum([subtask.score for subtask in self.subtasks.values()])

    def get_data_dir(self):
        return os.path.join(self.task_dir, self.data_subdir)

    def get_samples_dir(self):
        return os.path.join(self.task_dir, self.samples_subdir)


class SubtaskConfig:
    def __init__(
        self, contest_type: str, config_section: configparser.SectionProxy
    ) -> None:
        self.name: Optional[str] = config_section.get("name", None)
        self.score: int = int(config_section["points"])

        if contest_type == "cms":
            self.in_globs: List[str] = config_section["in_globs"].split()


T = TypeVar("T")
U = TypeVar("U")


def apply_to_optional(value: Optional[T], f: Callable[[T], U]) -> Optional[U]:
    return None if value is None else f(value)
