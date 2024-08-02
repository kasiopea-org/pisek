# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from typing import Any

from pisek.utils.paths import TaskPath
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.config.config_types import DataFormat
from pisek.task_jobs.task_manager import TaskJobManager, GENERATOR_MAN_CODE
from pisek.task_jobs.generator.input_info import InputInfo
from pisek.task_jobs.tools import IsClean
from pisek.task_jobs.checker import CheckerJob

from .data import LinkInput, LinkOutput, InputSmall, OutputSmall


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
            InputInfo.static(inp.name.removesuffix(".in")) for inp in static_inputs
        ] + self.prerequisites_results[GENERATOR_MAN_CODE]["inputs"]
        all_input_infos.sort(key=lambda info: info.name)

        self._input_infos: dict[int, list[InputInfo]] = {}
        for num, sub in self._env.config.subtasks.items():
            self._input_infos[sub.num] = []
            for input_info in all_input_infos:
                if sub.in_subtask(input_info.task_path(self._env, 25265).name):
                    self._input_infos[sub.num].append(input_info)
            if len(self._input_infos[sub.num]) == 0:
                raise PipelineItemFailure(
                    f"No inputs for subtask {num} with globs {sub.all_globs}."
                )

        used_inputs = set(sum(self._input_infos.values(), start=[]))
        unused_inputs = list(set(all_input_infos) - used_inputs)
        if len(unused_inputs):
            if self._env.verbosity <= 0:
                CUTOFF = 3
                unused_inputs_text = ", ".join(
                    map(lambda inp: inp.name, unused_inputs[:CUTOFF])
                )
                if len(unused_inputs) > CUTOFF:
                    unused_inputs_text += ",..."
                self._warn(
                    f"{len(unused_inputs)} unused inputs. ({unused_inputs_text})"
                )
            else:
                for inp in unused_inputs:
                    self._warn(f"Unused input: '{inp.name}'")

        jobs: list[Job] = []
        for path in static_inputs:
            jobs.append(LinkInput(self._env, path))
            if self._env.config.in_format == DataFormat.text:
                jobs.append(IsClean(self._env, path))
            if self._env.config.limits.input_max_size != 0:
                jobs.append(InputSmall(self._env, path))

        for path in static_outputs:
            jobs.append(LinkOutput(self._env, path))
            if self._env.config.out_format == DataFormat.text:
                jobs.append(IsClean(self._env, path))
            if self._env.config.limits.output_max_size != 0:
                jobs.append(OutputSmall(self._env, path))

        for subtask, inputs in self._input_infos.items():
            for inp in inputs:
                if inp.is_generated:
                    continue

                if subtask > 0 and self._env.config.checker is not None:
                    jobs.append(
                        CheckerJob(
                            self._env,
                            self._env.config.checker,
                            TaskPath.static_path(
                                self._env, inp.task_path(self._env).name
                            ),
                            subtask,
                        )
                    )

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        res = {"input_info": self._input_infos}
        return res
