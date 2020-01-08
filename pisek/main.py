import argparse
import os
import unittest
import sys

import pisek.tests
from pisek.program import Program


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run_tests(args):
    cwd = os.getcwd()
    eprint(f"Testuji úlohu {cwd}")

    suite = pisek.tests.kasiopea_test_suite(cwd)

    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=True)
    runner.run(suite)


def run_solution(args, unknown_args):
    eprint(f"Spouštím program: {args.solution}")

    cwd = os.getcwd()
    sol = Program(cwd, args.solution)
    ok = sol.run(unknown_args)

    if not ok:
        eprint("Chyba při běhu.")
    exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=1)

    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")
    parser_run = subparsers.add_parser("run", help="spusť řešení")
    parser_run.add_argument("solution", type=str, help="název řešení ke spuštění")

    args, unknown_args = parser.parse_known_args()
    if args.subcommand == "run":
        run_solution(args, unknown_args)
    elif args.subcommand is None:
        run_tests(args)
    else:
        raise RuntimeError(f"Neznámý podpříkaz {args.subcommand}")
