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

import os
from typing import Optional

from pisek.utils.text import tab
from pisek.env.config_errors import TaskConfigError
from pisek.env.task_config import TaskConfig, SolutionConfig


class UnknownSolutions(TaskConfigError):
    def __init__(
        self, unknown: list[str], solutions: dict[str, "SolutionConfig"]
    ) -> None:
        def format_solution(s: SolutionConfig) -> str:
            if s.name == s.source:
                return s.name
            else:
                return f"{s.name} (source: {s.source})"

        unknown_text = f"', '".join(unknown)
        sols_text = "\n".join(map(format_solution, solutions.values()))
        super().__init__(
            f"Unknown solution{'s' if len(unknown) > 1 else ''} '{unknown_text}'. "
            f"Known are:\n{tab(sols_text)}"
        )


def select_solution(config: TaskConfig, solution: str) -> Optional[str]:
    """Tries to find solution by its name/source."""
    if solution in config.solutions:
        return solution

    if (name := config.get_solution_by_source(solution)) is not None:
        return name

    return config.get_solution_by_source(os.path.splitext(solution)[0])


def expand_solutions(config: TaskConfig, solutions: Optional[list[str]]) -> list[str]:
    if solutions is None:
        return list(config.solutions)

    expanded = []
    unknown = []
    for sol in solutions:
        exp = select_solution(config, sol)
        if exp is not None:
            expanded.append(exp)
        else:
            unknown.append(sol)

    if unknown:
        raise UnknownSolutions(unknown, config.solutions)

    return expanded
