import subprocess
import random


def generate(
    executable: str, output_file: str, seed: int, isHard: bool, timeout: int = 100
) -> None:
    assert seed > 0

    with open(output_file, "w") as outp:
        difficulty = "2" if isHard else "1"
        hexa_seed = f"{seed:x}"

        result = subprocess.run(
            [executable, difficulty, hexa_seed],
            stdout=outp,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )

        # raise an exception if return code != 0
        result.check_returncode()


def generate_random(
    executable: str, output_file: str, isHard: bool, timeout: int = 100
) -> None:
    seed = random.randint(0, 16 ** 4 - 1)
    generate(executable, output_file, seed, isHard, timeout=timeout)
