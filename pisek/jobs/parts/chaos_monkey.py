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

import random
import string

from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.jobs.parts.task_job import TaskJob


def randword(length: int):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


NUMER_MODIFIERS = [
    lambda _: 0,
    lambda x: int(x) + 1,
    lambda x: int(x) - 1,
    lambda x: -int(x),
    lambda x: int(x) + random.randint(1, 9) / 10,
]
ANY_MODIFIERS = [
    lambda x: f"{x} {x}",
    lambda _: "",
    lambda x: randword(len(x)),
    lambda x: randword(len(x) + 1),
    lambda x: randword(len(x) - 1),
    lambda _: random.randint(-10000, 10000),
]


class Invalidate(TaskJob):
    """Abstract Job for Invalidating an output."""

    def __init__(
        self, env: Env, name: str, from_file: TaskPath, to_file: TaskPath, seed: int
    ) -> None:
        super().__init__(env, name)
        self.seed = seed
        self.from_file = from_file
        self.to_file = to_file


class Incomplete(Invalidate):
    """Makes an incomplete output."""

    def __init__(
        self, env: Env, from_file: TaskPath, to_file: TaskPath, seed: int
    ) -> None:
        super().__init__(
            env,
            f"Incomplete {from_file:n} -> {to_file:n} (seed {seed:x})",
            from_file,
            to_file,
            seed,
        )

    def _run(self):
        with self._open_file(self.from_file) as f:
            lines = f.readlines()

        random.seed(self.seed)
        lines = lines[: random.randint(0, len(lines) - 1)]

        with self._open_file(self.to_file, "w") as f:
            f.write("".join(lines))


class ChaosMonkey(Invalidate):
    """Tries to break judge by generating nasty output."""

    def __init__(self, env, from_file: TaskPath, to_file: TaskPath, seed: int) -> None:
        super().__init__(
            env,
            f"ChaosMonkey {from_file:n} -> {to_file:n} (seed {seed:x})",
            from_file,
            to_file,
            seed,
        )

    def _run(self):
        lines = []
        with self._open_file(self.from_file) as f:
            for line in f.readlines():
                lines.append(line.rstrip("\n").split(" "))

        random.seed(self.seed)
        line = random.randint(0, min(2, len(lines) - 1))
        if line == 2:
            line = random.randint(2, len(lines) - 1)
        token = random.randint(0, len(lines[line]) - 1)

        modifiers = ANY_MODIFIERS[:]
        try:
            int(lines[line][token])
            modifiers += NUMER_MODIFIERS
        except ValueError:
            pass

        lines[line][token] = str(random.choice(modifiers)(lines[line][token]))

        with self._open_file(self.to_file, "w") as f:
            for line in lines:
                f.write(" ".join(line) + "\n")
