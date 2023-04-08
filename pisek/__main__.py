# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import os
import unittest
import sys

from pisek.tests.util import get_test_suite
from pisek.program import Program, RunResultKind
from pisek import util
from pisek.license import license, license_gnu
import pisek.cms as cms


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class TextTestResultHideTraceback(unittest.TextTestResult):
    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        return f"{value}"


def get_resultclass(args):
    if args.pisek_traceback:
        return None
    return TextTestResultHideTraceback


def run_tests(args, full=False, all_tests=False):
    cwd = os.getcwd()
    eprint(f"Testuji úlohu {cwd}")

    suite = get_test_suite(
        cwd,
        timeout=args.timeout,
        strict=args.strict,
        no_checker=args.no_checker,
        all_tests=all_tests
    )

    runner = unittest.TextTestRunner(
        verbosity=args.verbose, failfast=not full, resultclass=get_resultclass(args)
    )
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
        eprint(f"Příklad:   pisek [--all_tests] test solution solve_slow_4b")
        exit(1)

    eprint(f"Testuji řešení: {args.solution}")
    cwd = os.getcwd()

    suite = get_test_suite(
        cwd,
        solutions=[args.solution],
        n_seeds=args.number_of_tests,
        timeout=args.timeout,
        only_necessary=True,
        all_tests=args.all_tests,
    )
    runner = unittest.TextTestRunner(
        verbosity=args.verbose, failfast=True, resultclass=get_resultclass(args)
    )
    result = runner.run(suite)

    return result


def test_generator(args):
    eprint(f"Testuji generátor")
    cwd = os.getcwd()

    suite = get_test_suite(cwd, solutions=[])

    runner = unittest.TextTestRunner(
        verbosity=args.verbose, failfast=True, resultclass=get_resultclass(args)
    )
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

    def add_argument_verbose(parser):
        parser.add_argument(
            "--verbose", "-v", action="count", default=2, help="zvyš ukecanost výstupů"
        )

    def add_argument_pisek_traceback(parser):
        parser.add_argument(
            "--pisek-traceback",
            action="store_true",
            help="Při chybách vypiš traceback písku",
        )

    def add_argument_timeout(parser):
        parser.add_argument(
            "--timeout",
            type=float,
            help="po kolika sekundách ukončit běžící řešení (pouze CMS)",
        )

    def add_argument_full(parser):
        parser.add_argument(
            "--full", action="store_true", help="nezastavit se při první chybě"
        )

    def add_argument_strict(parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="pro závěrečnou kontrolu: vynutit, že checker existuje",
        )
    
    def add_argument_no_checker(parser):
        parser.add_argument(
            "--no-checker",
            action="store_true",
            help="nepouštět checker",
        )

    def add_argument_all_tests(parser):
        parser.add_argument(
            "--all-tests", action="store_true", help="testovat i další vstupy po chybě"
        )

    def add_argument_clean(parser):
        parser.add_argument(
            "--clean",
            "-c",
            action="store_true",
            help="nejprve vyčisti, pak proveď žádané",
        )

    add_argument_verbose(parser)
    add_argument_pisek_traceback(parser)
    add_argument_timeout(parser)
    add_argument_full(parser)
    add_argument_strict(parser)
    add_argument_no_checker(parser)
    add_argument_all_tests(parser)
    add_argument_clean(parser)

    subparsers = parser.add_subparsers(help="podpříkazy", dest="subcommand")

    parser_run = subparsers.add_parser("run", help="spusť řešení")
    parser_run.add_argument("solution", type=str, help="název řešení ke spuštění")
    parser_run.add_argument(
        "command_args",
        type=str,
        nargs="*",
        help="Argumenty předané spuštěnému programu",
    )
    add_argument_clean(parser_run)

    parser_test = subparsers.add_parser("test", help="otestuj")
    parser_test.add_argument(
        "target",
        choices=["solution", "generator"],
        help="volba řešení/generátor",
    )
    parser_test.add_argument(
        "solution", type=str, help="název řešení ke spuštění", nargs="?"
    )
    parser_test.add_argument(
        "--number-of-tests",
        "-n",
        type=int,
        default=10,
        help="počet testů (pouze pro kasiopeu)",
    )
    add_argument_timeout(parser_test)
    add_argument_full(parser_test)
    add_argument_strict(parser_test)
    add_argument_no_checker(parser_test)
    add_argument_all_tests(parser_test)
    add_argument_pisek_traceback(parser_test)
    add_argument_clean(parser_test)

    _parser_clean = subparsers.add_parser("clean", help="vyčisti")

    parser_license = subparsers.add_parser("license", help="vypiš licenci písku")
    parser_license.add_argument(
        "--print", action="store_true", help="Vypiš celou licenci"
    )

    parser_cms = subparsers.add_parser("cms", help="Nástroj na nahrávání Pískovitých úloh do CMSka")
    subparsers_cms = parser_cms.add_subparsers(help="podpříkazy", dest="cms_subcommand")
    parser_cms_check = subparsers_cms.add_parser("check", help="do a preflight check")
    parser_cms_pack = subparsers_cms.add_parser("pack", help="check and pack")
    parser_cms_submit = subparsers_cms.add_parser("submit", help="submit for testing")
    parser_cms_info = subparsers_cms.add_parser("info", help="print task info without testing")
    parser_cms_samples = subparsers_cms.add_parser("samples", help="pack samples into .zip")
    CHECK_NONE = "none"
    CHECK_INSTANT = "instant"
    CHECK_SANE = "sane"
    CHECK_THOROUGH = "thorough"
    CHECK_MODES = [CHECK_NONE, CHECK_INSTANT, CHECK_SANE, CHECK_THOROUGH]
    parser_cms.add_argument(
        "--check-mode",
        choices=CHECK_MODES,
        default=None,
        help="Úroveň kontrol, které se mají provést",
    )
    parser_cms_submit.add_argument(
        "--contest-id",
        "-c",
        help="Id contestu, kam submittovat",
        type=int,
        required=True,
    )
    parser_cms_submit.add_argument(
        "--username",
        "-u",
        help="Username uživatele, za kterého submittovat.",
        type=str,
        required=True,
    )


    args = parser.parse_args(argv)

    result = None

    if args.clean:
        clean_directory(args)

    if args.subcommand == "run":
        result = run_solution(args, args.command_args)
    elif args.subcommand == "test":
        if args.target == "solution":
            result = test_solution(args)
        elif args.target == "generator":
            result = test_generator(args)
        else:
            assert False
    elif args.subcommand == "cms":
        args, unknown_args = parser.parse_known_args()
        actions = {
            "check": (CHECK_THOROUGH, lambda a: None),
            "pack": (CHECK_SANE, cms.pack),
            "submit": (CHECK_INSTANT, cms.submit_all),
            "info": (CHECK_INSTANT, cms.task_info),
            "samples": (CHECK_SANE, cms.samples),
            None: (CHECK_SANE, cms.pack),
        }
        checks = {
            CHECK_NONE: lambda a: None,
            CHECK_INSTANT: cms.check.instant,
            CHECK_SANE: cms.check.sane,
            CHECK_THOROUGH: cms.check.thorough,
        }
        check_mode, action = actions[args.cms_subcommand]
        if args.check_mode is not None: # allow overriding
            check_mode = args.check_mode
        checks[check_mode](args)
        return action(args)
    elif args.subcommand == "clean":
        clean_directory(args)
    elif args.subcommand == "license":
        print(license_gnu if args.print else license)
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
