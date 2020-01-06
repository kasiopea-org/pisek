import configparser
import os
from typing import List

CONFIG_FILENAME = "config"


class TaskConfig:
    def __init__(self, task_dir: str) -> None:
        try:
            config = configparser.ConfigParser()
            config.read(os.path.join(task_dir, CONFIG_FILENAME))

            self.solutions: List[str] = config["task"]["solutions"].split()
            self.generator: str = config["tests"]["in_gen"]
        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e
