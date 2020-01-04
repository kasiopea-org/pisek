import argparse
import os
import unittest
import sys

import pisek.tests
from pisek.solution import Solution


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run_tests(args):
    cwd = os.getcwd()
    eprint(f"Testuji úlohu {cwd}")

    suite = pisek.tests.kasiopea_test_suite(cwd)

    runner = unittest.TextTestRunner(verbosity=args.verbose)
    runner.run(suite)


def run_solution(args):
    eprint(f"Spouštím řešení: {args.solution}")
    cwd = os.getcwd()
    sol = Solution(cwd, args.solution)
    ok = sol.run()
    exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=1)

    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")
    parser_run = subparsers.add_parser("run", help="spusť řešení")
    parser_gen = subparsers.add_parser("gen", help="vygeneruj vstupy")
    parser_run.add_argument("solution", type=str, help="název řešení ke spuštění")

    args = parser.parse_args()
    if args.subcommand == "run":
        run_solution(args)
    elif args.subcommand == "gen":
        print(f"Generuji vstupy: {args}")
    elif args.subcommand is None:
        run_tests(args)
    else:
        raise RuntimeError(f"Neznámý podpříkaz {args.subcommand}")
