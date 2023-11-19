# pisek  - Tool for developing tasks for programming competitions.
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
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env import Env
from pisek.jobs.parts.task_job import TaskJobManager, TaskJob
from pisek.jobs.parts.solution_result import Verdict
from pisek.jobs.parts.tools import IsClean

MB = 1024 * 1024


class DataManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking data")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = []

        inputs = []
        outputs = []
        for name, data in self.prerequisites_results.items():
            if name.startswith("samples"):
                inputs += data["inputs"]
                outputs += data["outputs"]
            elif name.startswith("generator"):
                inputs += data["inputs"]
            elif name.startswith("solution_"):
                outs = data["outputs"]
                outputs += (
                    outs[Verdict.ok]
                    + outs[Verdict.partial]
                    + outs[Verdict.wrong_answer]
                )
        for inp in inputs:
            jobs.append(IsClean(self._env, inp))
            if self._env.config.contest_type == "kasiopea":
                jobs.append(InputSmall(self._env, inp))

        for out in outputs:
            jobs.append(IsClean(self._env, out))
            if self._env.config.contest_type == "kasiopea":
                jobs.append(OutputSmall(self._env, out))

        return jobs


class CheckData(TaskJob):
    """Abstract class for checking input and output files."""

    def __init__(self, env: Env, name: str, data_file: str) -> None:
        super().__init__(env, name)
        self.data = self._data(data_file)


class InputSmall(CheckData):
    """Checks that input is small enough to download."""

    def __init__(self, env: Env, input_file: str) -> None:
        super().__init__(
            env,
            f"Input {input_file} is smaller than {env.config.input_max_size}MB",
            input_file,
        )

    def _run(self):
        if self._file_size(self.data) > self._env.config.input_max_size * MB:
            raise PipelineItemFailure("Input too big.")


class OutputSmall(CheckData):
    """Checks that output is small enough to upload."""

    def __init__(self, env: Env, output_file: str) -> None:
        super().__init__(
            env,
            f"Output {output_file} is smaller than {env.config.output_max_size}MB",
            output_file,
        )

    def _run(self):
        if self._file_size(self.data) > self._env.config.output_max_size * MB:
            raise PipelineItemFailure("Output too big.")
