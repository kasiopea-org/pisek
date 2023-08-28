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
from importlib.resources import files

import subprocess
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager

class ToolsManager(TaskJobManager):
    def __init__(self):
        super().__init__("Preparing tools")

    def _get_jobs(self) -> list[Job]:
        jobs = [PrepareMinibox(self._env).init()]
        return jobs


class PrepareMinibox(TaskJob):
    """Copies samples into data so we can treat them as inputs."""
    def _init(self) -> None:
        super()._init("Prepare Minibox")

    def _run(self):
        source = files('pisek').joinpath('tools/minibox.c')
        executable = self._executable('minibox')
        self._access_file(executable)
        os.makedirs(self._executable("."), exist_ok=True)
        gcc = subprocess.run([
            "gcc", source, "-o", executable,
            "-std=gnu11", "-D_GNU_SOURCE", "-O2", "-Wall", "-Wextra", "-Wno-parentheses", "-Wno-sign-compare"
        ])
        if gcc.returncode != 0:
            self._fail("Minibox compilation failed.")
