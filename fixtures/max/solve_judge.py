#!/usr/bin/env python3
import sys
from typing import NoReturn


def accept() -> NoReturn:
    print(1)
    print("OK", file=sys.stderr)
    quit()


def reject() -> NoReturn:
    print(0)
    print("OK", file=sys.stderr)
    quit()


def solve(file) -> int:
    n = int(file.readline())
    vals = list(map(int, file.readline().split()))
    assert n == len(vals)
    return max(vals)


if len(sys.argv) == 1:
    print(solve(sys.stdin))
else:
    with open(sys.argv[3]) as f:
        try:
            res = int(f.read())
        except ValueError:
            reject()

    with open(sys.argv[1]) as f:
        if res == solve(f):
            accept()
        else:
            reject()
