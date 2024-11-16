# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional

from pisek.config.task_config import TaskConfig
from pisek.config.config_types import Scoring
from pisek.task_jobs.solution.solution_result import (
    Verdict,
    SUBTASK_SPEC,
    verdict_always,
)


def evaluate_verdicts(
    config: TaskConfig, verdicts: list[Verdict], expected: str
) -> tuple[bool, bool, Optional[int]]:
    result = True
    definitive = True
    breaker = None

    modes = [Scoring.equal, config.scoring]

    for i, mode in enumerate(modes):
        oks = list(map(SUBTASK_SPEC[expected][i], verdicts))

        if mode == Scoring.equal:
            ok = all(oks)

            result &= ok
            definitive &= not ok or SUBTASK_SPEC[expected][i] == verdict_always

            if not ok:
                breaker = oks.index(False)
                break
        elif mode == Scoring.min:
            ok = any(oks)

            result &= ok
            definitive &= ok

    return result, definitive, breaker
