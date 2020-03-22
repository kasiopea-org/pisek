import configparser
import os
import re
from typing import List, Dict

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


class SubtaskConfig:
    def __init__(self, contest_type, config_section):
        self.name = config_section.get("name", None)
        self.points = config_section["points"]

        if contest_type == "cms":
            self.in_globs = config_section["in_globs"].split()
