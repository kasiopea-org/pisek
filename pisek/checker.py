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

import os
import subprocess

from . import program
from .task_config import TaskConfig


class Checker(program.Program):
    def __init__(self, task_config: TaskConfig):
        assert task_config.checker
        super().__init__(task_config.task_dir, task_config.checker)
        self.task_config = task_config

    def run_on_file(
        self, input_file: str, subtask_num: int
    ) -> subprocess.CompletedProcess:
        """
        Runs the checker on the given file, assuming it is from a specific subtask.
        """

        with open(os.path.join(self.task_config.get_data_dir(), input_file)) as f:
            res = self.run_raw(
                [str(subtask_num)],
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        return res
