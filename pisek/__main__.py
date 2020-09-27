import argparse
import os
import unittest
import sys

from pisek.tests.util import get_test_suite
from pisek.program import Program, RunResult
from pisek import util


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run_tests(args, full=False):
    cwd = os.getcwd()
    eprint(f"Testuji úlohu {cwd}")

    suite = get_test_suite(cwd, timeout=args.timeout)

    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=not full)
    runner.run(suite)


def run_solution(args, unknown_args):
    eprint(f"Spouštím program: {args.solution}")

    cwd = os.getcwd()
    sol = Program(cwd, args.solution)
    result = sol.run(unknown_args)

    if result != RunResult.OK:
        eprint("Chyba při běhu.")
        exit(1)
    else:
        exit(0)


def test_solution(args):
    if args.solution is None:
        eprint(f"Zadejte název řešení, které chcete testovat!")
        eprint(f"Příklad:   pisek test solution solve_slow_4b")
        exit(1)

    eprint(f"Testuji řešení: {args.solution}")
    cwd = os.getcwd()

    suite = get_test_suite(
        cwd,
        solutions=[args.solution],
        n_seeds=args.number_of_tests,
        timeout=args.timeout,
    )
    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=True)
    runner.run(suite)


def test_generator(args):
    eprint(f"Testuji generátor")
    cwd = os.getcwd()

    suite = get_test_suite(cwd, solutions=[])

    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=True)
    runner.run(suite)


def clean_directory(args):
    task_dir = os.getcwd()
    eprint(f"Čistím složku: {task_dir}")
    util.clean_task_dir(task_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=2)
    parser.add_argument(
        "--timeout",
        type=int,
        help="po kolika sekundách ukončit běžící řešení",
    )

    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")
    parser_run = subparsers.add_parser("run", help="spusť řešení")
    parser_run.add_argument("solution", type=str, help="název řešení ke spuštění")

    parser_test = subparsers.add_parser("test", help="otestuj")
    parser_test.add_argument(
        "target",
        choices=["solution", "generator", "all"],
        default="all",
        help="volba řešení/generátor",
    )
    parser_test.add_argument(
        "solution", type=str, help="název řešení ke spuštění", nargs="?"
    )
    parser_test.add_argument(
        "--number-of-tests", "-n", type=int, default=10, help="počet testů"
    )

    parser_clean = subparsers.add_parser("clean", help="vyčisti")

    args, unknown_args = parser.parse_known_args()
    if args.subcommand == "run":
        run_solution(args, unknown_args)
    elif args.subcommand == "test":
        if args.target == "all":
            # Runs full tests
            run_tests(args, full=True)
        elif args.target == "solution":
            test_solution(args)
        elif args.target == "generator":
            test_generator(args)
        else:
            assert False
    elif args.subcommand == "clean":
        clean_directory(args)
    elif args.subcommand is None:
        run_tests(args, full=False)
    else:
        raise RuntimeError(f"Neznámý podpříkaz {args.subcommand}")


if __name__ == "__main__":
    main()
