#!/usr/bin/env python3
import os
import sys


def main():
    # Check that the command line arguments are passed as expected,
    # even though we do not need them here otherwise.
    assert len(sys.argv) == 3, "Expected two arguments: $difficulty $seed"

    diff = int(sys.argv[1])
    assert diff in [0, 1, 2]

    # Check that the seed is a hex string
    _seed = int(sys.argv[2], 16)

    test_input_file = os.getenv("TEST_INPUT")
    test_output_file = os.getenv("TEST_OUTPUT")

    if test_input_file is None or test_output_file is None:
        exit(2)

    with open(test_input_file, "r") as fin:
        with open(test_output_file, "r") as fcorrect:
            t = int(fin.readline())

            for _ in range(t):
                a, b = [int(x) for x in fin.readline().split()]
                c = int(fcorrect.readline())

                # Normally we would not need to do this in the judge, but here we want
                # to verify that the command line arguments are passed as expected.
                if diff <= 1:
                    assert abs(a) <= 1e9, "Input out of bounds for the easy version"
                    assert abs(b) <= 1e9, "Input out of bounds for the easy version"

                contestant = int(input())

                assert a + b == c

                if c != contestant:
                    exit(1)

    exit(0)


main()
