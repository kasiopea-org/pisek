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

import os
from typing import Any

from pisek.jobs.jobs import Job
from pisek.env import Env
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager


class SampleManager(TaskJobManager):
    def __init__(self):
        self._inputs = []
        self._outputs = []
        self._all = []
        super().__init__("Checking samples")

    def _get_jobs(self) -> list[Job]:
        self._inputs = self.globs_to_files(
            self._env.config.subtasks[0].all_globs,
            self._sample("."),
        )
        self._outputs = list(
            map(lambda inp: os.path.splitext(inp)[0] + ".out", self._inputs)
        )

        self._all = self._inputs + self._outputs
        if len(self._all) <= 0:
            self._fail(
                f"In subfolder {self._env.config.samples_subdir} of task folder are no samples "
                "(files sample*.in with according sample*.out)",
            )
            return []

        jobs: list[Job] = []
        for fname in self._all:
            jobs += [
                existence := SampleExists(self._env, fname),
                non_empty := SampleNotEmpty(self._env, fname),
                copy := CopySample(self._env, fname),
            ]
            non_empty.add_prerequisite(existence)
            copy.add_prerequisite(existence)

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        return {
            "inputs": self._inputs,
            "outputs": self._outputs,
            "all": self._all,
        }


class SampleJob(TaskJob):
    def __init__(self, env: Env, name: str, sample: str) -> None:
        super().__init__(env, name)
        self.sample = self._sample(sample)


class SampleExists(SampleJob):
    def __init__(self, env: Env, sample: str) -> None:
        super().__init__(env, f"Sample {sample} exists", sample)

    def _run(self):
        if not self._file_exists(self.sample):
            return self._fail(f"Sample does not exists or is not file: {self.sample}")


class SampleNotEmpty(SampleJob):
    def __init__(self, env: Env, sample: str) -> None:
        super().__init__(env, f"Sample {sample} is not empty", sample)

    def _run(self):
        if not self._file_not_empty(self.sample):
            return self._fail(f"Sample is empty: {self.sample}")


class CopySample(SampleJob):
    """Copies samples into data so we can treat them as inputs."""

    def __init__(self, env: Env, sample: str) -> None:
        data_subdir = env.config.data_subdir.rstrip("/") + "/"
        super().__init__(env, f"Copy {sample} to {data_subdir}", sample)

    def _run(self):
        self._copy_file(self.sample, self._data(os.path.basename(self.sample)))
