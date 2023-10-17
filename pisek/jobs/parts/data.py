# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from pisek.jobs.jobs import Job
from pisek.jobs.parts.task_job import TaskJobManager, TaskJob
from pisek.jobs.parts.tools import IsClean

MB = 1024*1024

class DataManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking data")

    def _get_jobs(self) -> list[Job]:
        jobs : list[Job] = []

        files = self._globs_to_files(["*"])
        for file in files:
            inp, out = file.endswith(".in"), file.endswith(".out")
            if inp or out:
                jobs.append(IsClean(self._env).init(file))
            if inp:
                if self._env.config.contest_type == "kasiopea":
                    jobs.append(InputSmall(self._env).init(file))
            if out:
                if self._env.config.contest_type == "kasiopea":
                    jobs.append(OutputSmall(self._env).init(file))

        return jobs


class CheckData(TaskJob):
    """Abstract class for checking input and output files."""
    def _init(self, name: str, data_file: str) -> None:
        self.data = self._data(data_file)
        super()._init(name)

class InputSmall(CheckData):
    """Checks that input is small enough to download."""
    def _init(self, input_file: str) -> None:
        super()._init(f"Input {input_file} is smaller than {self._env.config.input_max_size}MB", input_file)

    def _run(self):
        if self._file_size(self.data) > self._env.config.input_max_size*MB:
            self._fail("Input too big.")

class OutputSmall(CheckData):
    """Checks that output is small enough to upload."""
    def _init(self, output_file: str) -> None:
        super()._init(f"Output {output_file} is smaller than {self._env.config.output_max_size}MB", output_file)

    def _run(self):
        if self._file_size(self.data) > self._env.config.output_max_size*MB:
            self._fail("Output too big.")
