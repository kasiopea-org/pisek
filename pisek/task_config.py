import configparser
import os
import re
from typing import List, Dict, Optional

CONFIG_FILENAME = "config"


class TaskConfig:
    def __init__(self, task_dir: str) -> None:
        config = configparser.ConfigParser()
        config_path = os.path.join(task_dir, CONFIG_FILENAME)
        read_files = config.read(config_path)

        if not read_files:
            raise FileNotFoundError(
                f"Chybí konfigurační soubor {config_path}, je toto složka s úlohou?"
            )

        try:
            self.solutions: List[str] = config["task"]["solutions"].split()
            self.contest_type = config["task"].get("contest_type", "kasiopea")
            self.generator: str = config["tests"]["in_gen"]
            self.judge_type: str = config["tests"].get("out_check", "diff")
            self.judge_name: Optional[str] = None
            if self.judge_type == "judge":
                self.judge_name = config["tests"]["out_judge"]

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


class SubtaskConfig:
    def __init__(
        self, contest_type: str, config_section: configparser.SectionProxy
    ) -> None:
        self.name: Optional[str] = config_section.get("name", None)
        self.score: int = int(config_section["points"])

        if contest_type == "cms":
            self.in_globs: List[str] = config_section["in_globs"].split()
