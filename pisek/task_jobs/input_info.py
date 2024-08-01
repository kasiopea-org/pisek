from dataclasses import dataclass
from typing import Optional

from pisek.env.env import Env
from pisek.utils.paths import TaskPath


@dataclass(frozen=True)
class InputInfo:
    name: str
    repeat: int = 1
    is_generated: bool = True
    seeded: bool = True

    @staticmethod
    def generated(name: str, repeat: int = 1, seeded: bool = True) -> "InputInfo":
        return InputInfo(name, repeat, True, seeded)

    @staticmethod
    def static(name: str) -> "InputInfo":
        return InputInfo(name, 1, False, False)

    def task_path(self, env: Env, seed: Optional[int] = None) -> TaskPath:
        filename = self.name
        if self.seeded:
            assert seed is not None
            filename += f"_{seed:x}"
        filename += ".in"

        return TaskPath.input_path(env, filename)
