#!/usr/bin/env python3
import os
import sys

def award(msg, points = None):
    print(f"{msg}", file=sys.stderr)

    if points is not None:
        print(f"POINTS={points}", file=sys.stderr)

    exit(42)

assert len(sys.argv) == 3, "Expected two arguments: $difficulty $seed"

diff = int(sys.argv[1])
assert diff in [0, 1, 2]

# Check that the seed is a hex string
_seed = int(sys.argv[2], 16)

test_input_file = os.getenv("TEST_INPUT")

if test_input_file is None:
    exit(2)

with open(test_input_file, "r") as fin:
        n = int(fin.readline())
        arr = [int(x) for x in fin.readline().split()]
        arr.sort()

        try:
            contestant = int(input())
        except (EOFError, ValueError):
            award("Not a number.", 0)

        if contestant == arr[0]:
            award("Congratulations!")
        elif contestant == arr[1]:
            award("Pretty close!", 0.5)
        else:
            award("Too bad. Try again!", 0)

