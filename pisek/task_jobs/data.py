# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from typing import Any, Callable

from pisek.config.config_types import DataFormat
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.task_jobs.task_job import (
    TaskJob,
    TaskJobManager,
    GENERATOR_MAN_CODE,
    INPUTS_MAN_CODE,
    SOLUTION_MAN_CODE,
)
from pisek.task_jobs.generator import InputInfo
from pisek.task_jobs.solution_result import Verdict
from pisek.task_jobs.tools import IsClean


class DataManager(TaskJobManager):
    """Moves data to correct folders."""

    def __init__(self) -> None:
        super().__init__("Processing data")

    def _get_jobs(self) -> list[Job]:
        static_inputs = self.globs_to_files(
            self._env.config.input_globs, TaskPath.static_path(self._env, ".")
        )
        static_outputs = self.globs_to_files(
            map(
                lambda g: re.sub(r"\.in$", ".out", g),
                self._env.config.input_globs,
            ),
            TaskPath.static_path(self._env, "."),
        )

        if self._env.config.task_type != "communication":
            for static_inp in static_inputs:
                static_out = static_inp.replace_suffix(".out")
                if static_out not in static_outputs:
                    raise PipelineItemFailure(
                        f"Missing matching output '{static_out:p}' for static input '{static_inp:p}'."
                    )

        all_input_infos: list[InputInfo] = [
            InputInfo.static(inp.name) for inp in static_inputs
        ] + self.prerequisites_results[GENERATOR_MAN_CODE]["inputs"]
        all_input_infos.sort(key=lambda info: info.name)

        self._input_infos = {}
        for num, sub in self._env.config.subtasks.items():
            self._input_infos[sub.num] = []
            for input_info in all_input_infos:
                if sub.in_subtask(input_info.task_path(self._env, 25265)):
                    self._input_infos[sub.num].append(input_info)
            if len(self._input_infos[sub.num]) == 0:
                raise PipelineItemFailure(
                    f"No inputs for subtask {num} with globs {sub.all_globs}."
                )

        jobs: list[Job] = []
        for fname in static_inputs:
            jobs.append(LinkInput(self._env, fname))
        for fname in static_outputs:
            jobs.append(LinkOutput(self._env, fname))

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        res = {"input_info": self._input_infos}
        return res


class DataJob(TaskJob):
    def __init__(self, env: Env, name: str, data: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=name,
            **kwargs,
        )
        self.data = data


class LinkData(DataJob):
    """Copy data to into dest folder."""

    def __init__(self, env: Env, data: TaskPath, dest: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, name=f"Link {data:p} to {dest:p}/", data=data, **kwargs
        )
        self.dest = TaskPath(dest.path, self.data.name)

    def _run(self):
        self._link_file(self.data, self.dest, overwrite=True)


class LinkInput(LinkData):
    """Copy input to its place."""

    def __init__(self, env: Env, input_: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, data=input_, dest=TaskPath.input_path(self._env, "."), **kwargs
        )


class LinkOutput(LinkData):
    """Copy output to its place."""

    def __init__(self, env: Env, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, data=output, dest=TaskPath.output_path(self._env, "."), **kwargs
        )


MB = 1024 * 1024


class DataCheckingManager(TaskJobManager):
    def __init__(self):
        super().__init__("Checking data")

    def _get_jobs(self) -> list[Job]:
        jobs: list[Job] = []

        inputs = []
        outputs = []
        for name, data in self.prerequisites_results.items():
            if name.startswith(INPUTS_MAN_CODE):
                inputs += data["inputs"]
            elif name.startswith(SOLUTION_MAN_CODE):
                outs = data["outputs"]
                outputs += (
                    outs[Verdict.ok]
                    + outs[Verdict.partial_ok]
                    + outs[Verdict.wrong_answer]
                )
        for inp in inputs:
            if self._env.config.in_format == DataFormat.text:
                jobs.append(IsClean(self._env, inp))

            if self._env.config.limits.input_max_size != 0:
                jobs.append(InputSmall(self._env, inp))

        for out in outputs:
            if self._env.config.out_format == DataFormat.text:
                jobs.append(IsClean(self._env, out))

            if self._env.config.limits.output_max_size != 0:
                jobs.append(OutputSmall(self._env, out))

        return jobs


class InputSmall(DataJob):
    """Checks that input is small enough to download."""

    def __init__(self, env: Env, input_: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Input {input_:n} is smaller than {env.config.limits.input_max_size}MB",
            data=input_,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.input_max_size
        if (sz := self._file_size(self.data)) > max_size * MB:
            raise PipelineItemFailure(
                f"Input {self.data:p} is bigger than {max_size}MB: {(sz+MB-1)//MB}MB"
            )


class OutputSmall(DataJob):
    """Checks that output is small enough to upload."""

    def __init__(self, env: Env, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Output {output:n} is smaller than {env.config.limits.output_max_size}MB",
            data=output,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.output_max_size
        if (sz := self._file_size(self.data)) > max_size * MB:
            raise PipelineItemFailure(
                f"Output {self.data} is bigger than {max_size}MB: {(sz+MB-1)//MB}MB"
            )
