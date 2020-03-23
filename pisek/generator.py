import subprocess
import random
import os

from .program import Program
from . import util


class OnlineGenerator(Program):
    """
    A generator which is run "online" - new tests are generated
    on request based on a seed and subtask.

    We assume the generator outputs
    """

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

        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
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


class OfflineGenerator(Program):
    """
    A generator which is run "offline" - before the contest, to generate tests
    which are common to all participants.

    In this type of contests (non-opendata), the solution is run separately
    for individual tests so we generate a separate file for each. We give
    the generator a directory into which to generate outputs.
    """

    def generate(self, test_dir):
        self.compile_if_needed()
        os.makedirs(test_dir, exist_ok=True)

        result = subprocess.run([self.executable, test_dir])

        return result.returncode == 0
