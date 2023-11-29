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

import json
import os
import sys
import re
from typing import Any

from pisek.util import get_output_name
from pisek.terminal import colored
from pisek.jobs.cache import Cache
from pisek.jobs.parts.solution import RUN_JOB_NAME
from pisek.jobs.parts.judge import JUDGE_JOB_NAME

FILE_NAME = "testing_log.json"


def extract(env) -> None:
    # Extracts testing_log.json from .pisek_cache
    cache = Cache(env)
    if cache.broken_seal is None or not cache.broken_seal.success:
        print(
            colored(
                "This task has not been successfully tested. Data might be incomplete.",
                env,
                "red",
            ),
            file=sys.stderr,
        )
    data: dict[str, Any] = {"source": "pisek"}
    for name in cache.entry_names():
        if m := re.match(RUN_JOB_NAME, name):
            solution, inp = m[1], m[2]
            solution = os.path.relpath(solution, env.config.solutions_subdir)
            run = cache.last_entry(name).result

            if solution not in data:
                data[solution] = {"results": []}
            judge = JUDGE_JOB_NAME.replace(r"(\w+)", get_output_name(inp, solution), 1)
            if judge not in cache:
                continue
            res = cache.last_entry(judge).result
            data[solution]["results"].append(
                {
                    "time": float(run.time),
                    "wall_clock_time": float(run.wall_time),
                    "test": inp.replace(".in", ""),
                    "points": res.points,
                    "result": res.verdict.name,
                }
            )

    with open(os.path.join(env.task_dir, FILE_NAME), "w") as f:
        json.dump(data, f, indent=True)
