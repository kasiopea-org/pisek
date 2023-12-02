#!/usr/bin/env python3
import os


def main():
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

                contestant = input()

                if contestant.endswith("\r"):
                    # Looks like we didn't handle Windows line-endings correctly!
                    contestant += "oops!"
                contestant = int(contestant)

                assert a + b == c

                if c != contestant:
                    exit(1)

    exit(0)


main()
