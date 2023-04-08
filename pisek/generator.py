# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import subprocess
import random
import os
import sys

from .program import Program
from . import util
from .task_config import TaskConfig, DEFAULT_TIMEOUT


class OnlineGenerator(Program):
    """
    A generator which is run "online" - new tests are generated
    on request based on a seed and subtask.

    We assume the generator outputs
    """

    def __init__(self, task_dir: str, name: str):
        super().__init__(task_dir, name)
        self.cache_used = False  # Used to notify the user that cached data was used.

    def generate(
        self,
        output_file: str,
        seed: int,
        subtask: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        assert seed >= 0
        self.compile_if_needed()
        assert self.executable is not None

        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        if util.file_is_newer(output_file, self.executable):
            # No need to re-generate
            self.cache_used = True
            return True
        else:
            with open(output_file, "w") as outp:

                difficulty = str(subtask)
                hexa_seed = f"{seed:x}"

                result = subprocess.run(
                    [self.executable, difficulty, hexa_seed],
                    stdout=outp,
                    timeout=timeout,
                )

                # TODO: return a CompletedProcess to be consistent with OfflineGenerator
                return result.returncode == 0

    def generate_random(
        self, output_file: str, subtask: int, timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        seed = random.randint(0, 16**4 - 1)
        return self.generate(output_file, seed, subtask, timeout=timeout)


class OfflineGenerator(Program):
    """
    A generator which is run "offline" - before the contest, to generate tests
    which are common to all participants.

    In this type of contests (non-opendata), the solution is run separately
    for individual tests, so we generate a separate file for each. We give
    the generator a directory into which to generate outputs.
    """

    def __init__(self, task_config: TaskConfig, name: str):
        super().__init__(task_config.task_dir, name)
        self.cache_used = False  # Used to notify the user that cached data was used.
        self.task_config = task_config

    def generate(self, test_dir: str) -> int:
        self.compile_if_needed()
        os.makedirs(test_dir, exist_ok=True)

        assert self.executable is not None

        inp = get_any_nonsample_input(self.task_config)
        if inp and util.file_is_newer(inp, self.executable):
            # The inputs appear to be newer - do not rerun.
            self.cache_used = True
            return 0

        # Get rid of old inputs/outputs that would be invalidated now
        util.clean_data_dir(self.task_config)

        popen = subprocess.Popen(
            [self.executable, test_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        assert popen.stdout is not None  # To make MyPy happy

        for i, stdout_line in enumerate(popen.stdout):
            if i == 0:
                print(file=sys.stderr)
            print(
                util.quote_output(stdout_line, max_length=1e9, max_lines=1e9),
                file=sys.stderr,
            )

        popen.stdout.close()
        return_code = popen.wait()

        return return_code


def get_any_nonsample_input(task_config):
    """Returns an arbitrary `.in` file in the data dir that is not a sample."""
    samples = util.get_samples(task_config.task_dir)
    data_dir = task_config.get_data_dir()

    for file in os.listdir(data_dir):
        if file.endswith(".in") and file not in samples:
            return os.path.join(data_dir, file)

    return None
