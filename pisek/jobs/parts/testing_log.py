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
from typing import Any

from pisek.jobs.jobs import Job
from pisek.jobs.parts.task_job import (
    TaskJobManager,
    SOLUTION_MAN_CODE,
)
from pisek.jobs.parts.solution_result import SolutionResult

TESTING_LOG = "testing_log.json"


class CreateTestingLog(TaskJobManager):
    def __init__(self):
        super().__init__(f"Creating testing log")

    def _get_jobs(self) -> list[Job]:
        return []

    def _evaluate(self) -> None:
        log: dict[str, Any] = {"source": "pisek"}
        for name, data in self.prerequisites_results.items():
            if not name.startswith(SOLUTION_MAN_CODE):
                continue

            solution = name[len(SOLUTION_MAN_CODE) :]
            log[solution] = {"results": []}

            inp: str
            sol_res: SolutionResult
            for inp, sol_res in data["results"].items():
                if sol_res is None:
                    raise ValueError(
                        f"Job of running solution {solution} on {inp} should not be None."
                    )
                log[solution]["results"].append(
                    {
                        "time": sol_res.time,
                        "wall_clock_time": sol_res.wall_time,
                        "test": inp,
                        "points": sol_res.points,
                        "result": sol_res.verdict.name,
                    }
                )

        with open(self._resolve_path(TESTING_LOG), "w") as f:
            json.dump(log, f, indent=4)
