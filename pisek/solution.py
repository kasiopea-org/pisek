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
from typing import Optional, Tuple

from . import util
from . import program
from .program import RunResultKind
from .task_config import TaskConfig, DEFAULT_TIMEOUT


class Solution(program.Program):
    def __init__(self, task_config: TaskConfig, name):
        super().__init__(
            task_config.task_dir,
            name,
            compiler_args={"manager": task_config.solution_manager},
        )

    def run_on_file(
        self, input_file: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Tuple[program.RunResult, Optional[str]]:
        """
        Runs the solution and stores the output in a reasonably named file in the same dir
        """
        data_dir = os.path.dirname(input_file)

        output_filename = util.get_output_name(input_file, solution_name=self.name)
        output_file = os.path.join(data_dir, output_filename)

        assert self.executable is not None

        if (
            output_file
            and util.file_is_newer(output_file, self.executable)
            and util.file_is_newer(output_file, input_file)
            # An empty file might mean the solution was interrupted while running.
            and os.stat(output_file).st_size > 0
        ):
            # The output file is newer than both the executable and the input,
            # so it should be up-to-date.
            return program.RunResult(RunResultKind.OK), output_file

        res = program.run(self.executable, input_file, output_file, timeout)

        if res.kind == program.RunResultKind.OK:
            return res, output_file
        else:
            # Set the modification time of this file to 1970 so that it is not used
            # for caching
            os.utime(output_file, (0, 0))
            return res, None
