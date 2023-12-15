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

import os
from typing import Any, Callable

from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env import Env
from pisek.jobs.parts.task_job import (
    TaskJob,
    TaskJobManager,
    GENERATED_SUBDIR,
    INPUTS_MAN_CODE,
    SOLUTION_MAN_CODE,
)
from pisek.jobs.parts.solution_result import Verdict
from pisek.jobs.parts.tools import IsClean


class DataManager(TaskJobManager):
    """Moves data to correct folders."""

    def __init__(self):
        self._static_inputs = []
        self._generated_inputs = []
        self._static_outputs = []
        super().__init__("Moving data")

    def _get_jobs(self) -> list[Job]:
        self._static_inputs = list(
            map(
                self._static,
                self.globs_to_files(
                    self._env.config.subtasks[0].all_globs,
                    self._resolve_path(self._env.config.static_subdir),
                ),
            )
        )
        self._static_outputs = list(
            map(
                self._static,
                self.globs_to_files(
                    list(
                        map(
                            lambda x: x.replace(".in", ".out"),
                            self._env.config.subtasks[0].all_globs,
                        )
                    ),
                    self._resolve_path(self._env.config.static_subdir),
                ),
            )
        )
        self._generated_inputs = list(
            map(
                self._generated_input,
                self.globs_to_files(
                    self._env.config.subtasks.all_globs, self._data(GENERATED_SUBDIR)
                ),
            )
        )

        self._all_input_files = self._static_inputs + self._generated_inputs
        self._all_output_files = self._static_outputs
        jobs: list[Job] = []

        if self._env.config.task_type != "communication":
            for static_inp in self._static_inputs:
                if static_inp.replace(".in", ".out") not in self._static_outputs:
                    raise PipelineItemFailure(
                        f"No matching output for static input {os.path.basename(static_inp)}."
                    )

        for fname in self._all_input_files:
            jobs += [
                DataIsNotEmpty(self._env, fname),
                LinkInput(self._env, fname),
            ]
        for fname in self._all_output_files:
            jobs += [
                DataIsNotEmpty(self._env, fname),
                LinkOutput(self._env, fname),
            ]

        for glob in self._env.config.subtasks.all_globs:
            if (
                len(
                    self.filter_by_globs(
                        [glob], map(os.path.basename, self._all_input_files)
                    )
                )
                == 0
            ):
                raise PipelineItemFailure(f"No inputs for glob '{glob}'.")

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        res = {
            "inputs": self._all_input_files,
            "outputs": self._all_output_files,
            "all": self._all_input_files + self._all_output_files,
        }
        for key in ("inputs", "outputs", "all"):
            res[key] = list(map(os.path.basename, res[key]))

        return res


class DataJob(TaskJob):
    def __init__(self, env: Env, name: str, data: str, **kwargs) -> None:
        super().__init__(
            env=env,
            name=name,
            **kwargs,
        )
        self.data = data


class DataIsNotEmpty(DataJob):
    """Check that input file is not empty."""

    def __init__(self, env: Env, data: str, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Input/Output {os.path.basename(data)} is not empty.",
            data=data,
            **kwargs,
        )

    def _run(self):
        if not self._file_not_empty(self.data):
            raise PipelineItemFailure(f"Input/Output {self.data} is empty.")


class LinkData(DataJob):
    """Copy data to into dest folder."""

    def __init__(
        self, env: Env, data: str, dest: Callable[[str], str], **kwargs
    ) -> None:
        super().__init__(
            env=env, name=f"Copy {data} to {dest('.')}", data=data, **kwargs
        )
        self._dest = dest

    def _run(self):
        self._link_file(
            self.data, self._dest(os.path.basename(self.data)), overwrite=True
        )


class LinkInput(LinkData):
    """Copy input to its place."""

    def __init__(self, env: Env, input_: str, **kwargs) -> None:
        super().__init__(env=env, data=input_, dest=self._input, **kwargs)


class LinkOutput(LinkData):
    """Copy output to its place."""

    def __init__(self, env: Env, output: str, **kwargs) -> None:
        super().__init__(env=env, data=output, dest=self._output, **kwargs)


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
                    + outs[Verdict.partial]
                    + outs[Verdict.wrong_answer]
                )
        for inp in map(self._input, inputs):
            jobs.append(IsClean(self._env, inp))
            if self._env.config.contest_type == "kasiopea":
                jobs.append(InputSmall(self._env, inp))

        for out in map(self._output, outputs):
            jobs.append(IsClean(self._env, out))
            if self._env.config.contest_type == "kasiopea":
                jobs.append(OutputSmall(self._env, out))

        return jobs


class InputSmall(DataJob):
    """Checks that input is small enough to download."""

    def __init__(self, env: Env, input_file: str, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Input {os.path.basename(input_file)} is smaller than {env.config.limits.input_max_size}MB",
            data=input_file,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.input_max_size
        if self._file_size(self.data) > max_size * MB:
            raise PipelineItemFailure(f"Input {self.data} is bigger than {max_size}MB.")


class OutputSmall(DataJob):
    """Checks that output is small enough to upload."""

    def __init__(self, env: Env, output_file: str, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Output {os.path.basename(output_file)} is smaller than {env.config.limits.output_max_size}MB",
            data=output_file,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.output_max_size
        if self._file_size(self.data) > max_size * MB:
            raise PipelineItemFailure(
                f"Output {self.data} is bigger than {max_size}MB."
            )
