import configparser
import os

CONFIG_FILENAME = "config"


class TaskConfig:
    def __init__(self, task_dir):
        try:
            config = configparser.ConfigParser()
            config.read(os.path.join(task_dir, CONFIG_FILENAME))

            self.solutions = config["task"]["solutions"].split()
        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e
