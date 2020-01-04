import argparse
import pisek.tests
import os
import unittest


def run_tests(args):
    cwd = os.getcwd()
    print(f"Testuji úlohu {cwd}")

    suite = pisek.tests.kasiopea_test_suite(cwd)

    runner = unittest.TextTestRunner(verbosity=args.verbose)
    runner.run(suite)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=1)

    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")
    parser_run = subparsers.add_parser("run", help="spusť řešení a ulož výstup")
    parser_gen = subparsers.add_parser("gen", help="vygeneruj vstupy")
    parser_gen = subparsers.add_parser("None", help="default")
    parser_run.add_argument("command", type=str)
    parser_run.add_argument(
        "--input",
        type=str,
        help="vstupní soubor (default: spustit na všech vstupech v ./data/)",
    )

    parser_gen.add_argument("bar", type=int, help="bar help 1")

    args = parser.parse_args()
    if args.subcommand == "run":
        print(f"Spouštím řešení: {args}")
    elif args.subcommand == "gen":
        print(f"Generuji vstupy: {args}")
    elif args.subcommand is None:
        run_tests(args)
    else:
        raise RuntimeError(f"Neznámý podpříkaz {args.subcommand}")
    print(args)
