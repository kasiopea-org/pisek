import argparse
import os
import unittest
import sys

from pisek.tests.util import get_test_suite
from pisek.program import Program, RunResultKind
from pisek import util


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run_tests(args, full=False, all_tests=False):
    cwd = os.getcwd()
    eprint(f"Testuji úlohu {cwd}")

    suite = get_test_suite(
        cwd, timeout=args.timeout, strict=args.strict, all_tests=all_tests
    )

    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=not full)
    result = runner.run(suite)

    return result


def run_solution(args, unknown_args):
    eprint(f"Spouštím program: {args.solution}")

    cwd = os.getcwd()
    sol = Program(cwd, args.solution)
    run_result = sol.run(unknown_args)

    if run_result.kind != RunResultKind.OK:
        eprint(f"Chyba při běhu: {run_result.msg}")
        exit(1)

    return None


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
        only_necessary=True,
    )
    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=True)
    result = runner.run(suite)

    return result


def test_generator(args):
    eprint(f"Testuji generátor")
    cwd = os.getcwd()

    suite = get_test_suite(cwd, solutions=[])

    runner = unittest.TextTestRunner(verbosity=args.verbose, failfast=True)
    result = runner.run(suite)

    return result


def clean_directory(args):
    task_dir = os.getcwd()
    eprint(f"Čistím složku: {task_dir}")
    util.clean_task_dir(task_dir)


def main(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Nástroj na testování úloh do programovacích soutěží. "
            "Plná dokumentace je k dispozici na https://github.com/kasiopea-org/pisek"
        )
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=2, help="zvyš ukecanost výstupů"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="po kolika sekundách ukončit běžící řešení",
    )
    parser.add_argument(
        "--full", action="store_true", help="nezastavit se při první chybě"
    )
    parser.add_argument(
        "--all-tests", action="store_true", help="testovat i další vstupy po chybě"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="pro závěrečnou kontrolu: vynutit, že checker existuje",
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
    parser_test.add_argument(
        "--timeout",
        type=int,
        help="po kolika sekundách ukončit běžící řešení",
    )

    _parser_clean = subparsers.add_parser("clean", help="vyčisti")

    args, unknown_args = parser.parse_known_args(argv)

    result = None

    if args.subcommand == "run":
        result = run_solution(args, unknown_args)
    elif args.subcommand == "test":
        if args.target == "solution":
            result = test_solution(args)
        elif args.target == "generator":
            result = test_generator(args)
        else:
            assert False
    elif args.subcommand == "clean":
        clean_directory(args)
    elif args.subcommand is None:
        result = run_tests(args, full=args.full, all_tests=args.all_tests)
    else:
        raise RuntimeError(f"Neznámý podpříkaz {args.subcommand}")

    return result


def main_wrapped():
    try:
        result = main(sys.argv[1:])

        if result is not None:
            if result.errors or result.failures:
                exit(1)
    except KeyboardInterrupt as e:
        print("Přerušeno uživatelem.")
        exit(1)


if __name__ == "__main__":
    main_wrapped()
