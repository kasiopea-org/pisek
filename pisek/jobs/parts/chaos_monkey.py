import random
import string
from pisek.env import Env

from pisek.jobs.parts.task_job import TaskJob

def randword(length: int):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for _ in range(length))


NUMER_MODIFIERS = [
    lambda x: int(x)+1,
    lambda x: int(x)-1,
    lambda x: -int(x),
    lambda x: int(x) + random.randint(1, 9)/10
]
ANY_MODIFIERS = [
    lambda x: f"{x} {x}",
    lambda _: "",
    lambda x: randword(len(x)),
    lambda x: randword(len(x)+1),
    lambda x: randword(len(x)-1),
    lambda _: random.randint(-10000, 10000),
]

class Invalidate(TaskJob):
    """Abstract Job for Invalidating an output."""
    def _init(self, name: str, from_file: str, to_file: str, seed: int) -> None:
        super()._init(name)
        self.seed = seed
        self.from_file = self._data(from_file)
        self.to_file = self._data(to_file)

class Incomplete(Invalidate):
    """Makes an incomplete output."""
    def _init(self, from_file: str, to_file: str, seed: int) -> None:
        super()._init(f"Incomplete {from_file} -> {to_file} (seed {seed:x})",
                         from_file, to_file, seed)

    def _run(self):
        with self._open_file(self.from_file) as f:
            lines = f.readlines()

        lines = lines[:random.randint(0, len(lines))]

        with self._open_file(self.to_file, "w") as f:
            f.write("\n".join(lines))


class ChaosMonkey(Invalidate):
    """Tries to break judge by generating nasty output."""
    def _init(self, from_file: str, to_file: str, seed: int) -> None:
        super()._init(f"ChaosMonkey {from_file} -> {to_file} (seed {seed:x})",
                         from_file, to_file, seed)

    def _run(self):
        lines = []
        with self._open_file(self.from_file) as f:
            for line in f.readlines():
                lines.append(line.rstrip("\n").split(" "))

        random.seed(self.seed)
        line = random.randint(0, min(2, len(lines)-1))
        if line == 2:
            line = random.randint(2, len(lines)-1)
        token = random.randint(0, len(lines[line])-1)

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
