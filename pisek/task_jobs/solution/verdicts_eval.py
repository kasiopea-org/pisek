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
from pisek.task_jobs.solution.solution_result import (
    Verdict,
    TEST_SPEC,
    verdict_always,
)


def evaluate_verdicts(
    config: TaskConfig, verdicts: list[Verdict], expected: str
) -> tuple[bool, bool, Optional[int]]:
    result = True
    definitive = True
    breaker = None

    for i, mode in enumerate((all, any)):
        oks = list(map(TEST_SPEC[expected][i], verdicts))
        ok = mode(oks)
        result &= ok

        if mode == all:
            definitive &= not ok or TEST_SPEC[expected][i] == verdict_always
            if not ok:
                breaker = oks.index(False)
                break
        elif mode == any:
            definitive &= ok

    return result, definitive, breaker
