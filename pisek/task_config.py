import configparser
import os
from typing import List

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

        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e
