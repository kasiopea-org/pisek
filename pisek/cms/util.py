import os
import subprocess
import sys


def run_and_capture(command):
    return (
        subprocess.run(["bash", "-c", command], stdout=subprocess.PIPE)
        .stdout.decode("utf-8")
        .strip()
    )


def warn(*args, **kwargs):
    # TODO: add "if strict => exit"
    print(*args, **kwargs, file=sys.stderr)
