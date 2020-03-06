import subprocess
import random

from .program import Program
from . import util


class Generator(Program):
    def generate(
        self,
        output_file: str,
        seed: int,
        subtask: int,
        timeout: int = util.DEFAULT_TIMEOUT,
    ) -> bool:
        assert seed >= 0
        self.compile_if_needed()
        assert self.executable is not None

        with open(output_file, "w") as outp:
            difficulty = str(subtask)
            hexa_seed = f"{seed:x}"

            result = subprocess.run(
                [self.executable, difficulty, hexa_seed],
                stdout=outp,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )

            return result.returncode == 0

    def generate_random(
        self, output_file: str, subtask: int, timeout: int = util.DEFAULT_TIMEOUT
    ) -> bool:
        seed = random.randint(0, 16 ** 4 - 1)
        return self.generate(output_file, seed, subtask, timeout=timeout)
