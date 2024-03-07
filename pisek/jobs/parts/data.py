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

from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.jobs.parts.task_job import (
    TaskJob,
    TaskJobManager,
    GENERATOR_MAN_CODE,
    INPUTS_MAN_CODE,
    SOLUTION_MAN_CODE,
)
from pisek.jobs.parts.solution_result import Verdict
from pisek.jobs.parts.tools import IsClean


class DataManager(TaskJobManager):
    """Moves data to correct folders."""

    def __init__(self) -> None:
        self._static_inputs: list[TaskPath] = []
        self._generated_inputs: list[TaskPath] = []
        self._static_outputs: list[TaskPath] = []
        super().__init__("Moving data")

    def _get_jobs(self) -> list[Job]:
        self._static_inputs = self.globs_to_files(
            self._env.config.input_globs, TaskPath.static_path(self._env, ".")
        )
        self._static_outputs = self.globs_to_files(
            map(
                lambda g: re.sub(r"\.in$", ".out", g),
                self._env.config.input_globs,
            ),
            TaskPath.static_path(self._env, "."),
        )
        self._generated_inputs = self.prerequisites_results[GENERATOR_MAN_CODE][
            "inputs"
        ]

        all_input_files = self._static_inputs + self._generated_inputs
        all_output_files = self._static_outputs
        jobs: list[Job] = []

        if self._env.config.task_type != "communication":
            for static_inp in self._static_inputs:
                static_out = static_inp.replace_suffix(".out")
                if static_out not in self._static_outputs:
                    raise PipelineItemFailure(
                        f"Missing matching output '{static_out:p}' for static input '{static_inp:p}'."
                    )

        self._inputs: list[TaskPath] = []
        self._outputs: list[TaskPath] = []
        link: LinkData
        for fname in all_input_files:
            jobs += [
                DataIsNotEmpty(self._env, fname),
                link := LinkInput(self._env, fname),
            ]
            self._inputs.append(link.dest)
        for fname in all_output_files:
            jobs += [
                DataIsNotEmpty(self._env, fname),
                link := LinkOutput(self._env, fname),
            ]
            self._outputs.append(link.dest)

        for num, sub in self._env.config.subtasks.items():
            inputs = list(filter(lambda p: sub.in_subtask(p.name), all_input_files))
            if len(inputs) == 0:
                raise PipelineItemFailure(
                    f"No inputs for subtask {num} with globs {sub.all_globs}."
                )

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        res = {
            "inputs": self._inputs,
            "outputs": self._outputs,
            "all": self._inputs + self._outputs,
        }

        return res


class DataJob(TaskJob):
    def __init__(self, env: Env, name: str, data: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=name,
            **kwargs,
        )
        self.data = data


class DataIsNotEmpty(DataJob):
    """Check that input file is not empty."""

    def __init__(self, env: Env, data: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Input/Output {data:n} is not empty.",
            data=data,
            **kwargs,
        )

    def _run(self):
        if not self._file_not_empty(self.data):
            raise PipelineItemFailure(f"Input/Output {self.data} is empty.")


class LinkData(DataJob):
    """Copy data to into dest folder."""

    def __init__(self, env: Env, data: TaskPath, dest: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, name=f"Copy {data:p} to {dest:p}/", data=data, **kwargs
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
        if self._file_size(self.data) > max_size * MB:
            raise PipelineItemFailure(
                f"Input {self.data:p} is bigger than {max_size}MB."
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
        if self._file_size(self.data) > max_size * MB:
            raise PipelineItemFailure(
                f"Output {self.data} is bigger than {max_size}MB."
            )
