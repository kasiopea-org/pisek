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
from typing import Optional
import unittest
import sys

from pisek.task_config import TaskConfig
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.env import Env
from pisek.jobs.cache import Cache
from pisek.jobs.status import tab

from pisek import util
from pisek.license import license, license_gnu
import pisek.cms as cms
from pisek.visualize import visualize_command

def eprint(msg, *args, **kwargs):
    print(msg, *args, file=sys.stderr, **kwargs)


def test_task(args, **kwargs):
    cwd = os.getcwd()
    return (test_task_path(cwd, **vars(args), **kwargs))

def test_task_path(path, solutions: Optional[list[str]] = None, **env_args):
    config = TaskConfig(path)
    err = config.load()
    if err:
        eprint(f"Error when loading config:\n{tab(err)}")
        return 1

    if solutions is None:
        solutions = config.get_without_log('solution_names')

    env = Env(
        task_dir=path,
        config=config,
        solutions=solutions,
        **env_args
    )

    pipeline = TaskPipeline(env.fork())
    return pipeline.run_jobs(Cache(env), env)


def test_solution(args):
    if args.solution is None:
        eprint(f"Enter solution name to test")
        eprint(f"Example:   pisek [--all_tests] test solution solve_slow_4b")
        return 1

    eprint(f"Testing solution: {args.solution}")
    return test_task(args, solutions=[args.solution])


def test_generator(args):
    eprint(f"Testing generator")
    return test_task(args, solutions=[])


def clean_directory(args):
    task_dir = os.getcwd()
    eprint(f"Cleaning repository: {task_dir}")
    util.clean_task_dir(task_dir)


def main(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Tool for developing tasks for programming competitions."
            "Full documentation is at https://github.com/kasiopea-org/pisek"
        )
    )

    def add_argument_verbose(parser):
        parser.add_argument(
            "--verbose", "-v", action="count", default=2, help="zvyš ukecanost výstupů"
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

    def add_argument_ninputs(parser):
        parser.add_argument(
            "--inputs",
            "-n",
            type=int,
            default=5,
            help="počet testů (pouze pro kasiopeu)",
        )

    def add_argument_clean(parser):
        parser.add_argument(
            "--clean",
            "-c",
            action="store_true",
            help="nejprve vyčisti, pak proveď žádané",
        )

    def add_argument_cms_contest(parser):
        parser.add_argument(
            "--contest-id",
            "-c",
            help="Id contestu, kam submitovat",
            type=int,
            required=True,
        )

    def add_argument_cms_user(parser):
        parser.add_argument(
            "--username",
            "-u",
            help="Username uživatele, za kterého submitovat.",
            type=str,
            required=True,
        )

    def add_argument_mode(parser):
        parser.add_argument(
            "--mode",
            "-m",
            default="slowest",
            type=str,
            help="Mód zobrazování.\n slowest: Nejpomalejší vstup\n all: všechny vstupy",
        )
    
    def add_argument_no_subtasks(parser):
        parser.add_argument(
            "--no-subtasks",
            "-n",
            action="store_true",
            help="Zobrazit všechny vstupy dohromady (ne po subtascích).",
        )
    
    def add_argument_solutions(parser):
        parser.add_argument(
            "--solutions",
            "-s",
            default='all',
            type=str,
            nargs="*",
            help="Řešení, která se mají vizualizovat.",
        )

    def add_argument_filename(parser):
        parser.add_argument(
            "--filename",
            "-f",
            default="testing_log.json",
            type=str,
            help="Jméno jsonu, ze kterého načítat data.",
        )
    
    def add_argument_measured_stat(parser):
        parser.add_argument(
            "--measured-stat",
            "-M",
            default="time",
            type=str,
            help="Podle čeho visualizovat programy. Zatím implementováno pouze time.",
        )
    
    def add_argument_limit(parser):
        parser.add_argument(
            "--limit",
            "-l",
            default=None,
            type=float,
            help="Limit measured_stat na řešení.",
        )
    
    def add_argument_segments(parser):
        parser.add_argument(
            "--segments",
            "-S",
            default=5,
            type=int,
            help="Počet segmentů do limitu.",
        )

    add_argument_verbose(parser)
    add_argument_timeout(parser)
    add_argument_full(parser)
    add_argument_strict(parser)
    add_argument_no_checker(parser)
    add_argument_ninputs(parser)
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
    add_argument_timeout(parser_test)
    add_argument_full(parser_test)
    add_argument_strict(parser_test)
    add_argument_no_checker(parser_test)
    add_argument_ninputs(parser_test)
    add_argument_clean(parser_test)

    _parser_clean = subparsers.add_parser("clean", help="vyčisti")
    
    parser_visualize = subparsers.add_parser("visualize", help="Zobraz statistiky řešení a jak blízko jsou limitu.")
    add_argument_mode(parser_visualize)
    add_argument_no_subtasks(parser_visualize)
    add_argument_solutions(parser_visualize)
    add_argument_filename(parser_visualize)
    add_argument_measured_stat(parser_visualize)
    add_argument_limit(parser_visualize)
    add_argument_segments(parser_visualize)

    parser_license = subparsers.add_parser("license", help="vypiš licenci písku")
    parser_license.add_argument(
        "--print", action="store_true", help="Vypiš celou licenci"
    )

    parser_cms = subparsers.add_parser("cms", help="Nástroj na nahrávání Pískovitých úloh do CMSka")
    subparsers_cms = parser_cms.add_subparsers(help="podpříkazy", dest="cms_subcommand")
    parser_cms_check = subparsers_cms.add_parser("check", help="do a preflight check")
    parser_cms_pack = subparsers_cms.add_parser("pack", help="check and pack")
    parser_cms_submit = subparsers_cms.add_parser("submit", help="submit for testing")
    add_argument_cms_contest(parser_cms_submit)
    add_argument_cms_user(parser_cms_submit)
    parser_cms_analyze = subparsers_cms.add_parser("analyze", help="analyze submitted solutions")
    add_argument_cms_contest(parser_cms_analyze)
    add_argument_cms_user(parser_cms_analyze)
    parser_cms_dump = subparsers_cms.add_parser("dump", help="save json with run logs from submitted solutions")
    add_argument_cms_contest(parser_cms_dump)
    add_argument_cms_user(parser_cms_dump)
    parser_cms_dump.add_argument(
        "output",
        help="Output file (json)",
        type=str,
    )

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


    args = parser.parse_args(argv)

    result = None

    if args.clean:
        clean_directory(args)

    if args.subcommand == "run":
        raise NotImplementedError()
    elif args.subcommand == "test":
        if args.target == "solution":
            result = test_solution(args)
        elif args.target == "generator":
            result = test_generator(args)
        else:
            eprint(f"Unknown testing target: {args.target}")
            exit(1)
    elif args.subcommand is None:
        result = test_task(args, solutions=None)
    elif args.subcommand == "cms":
        args, unknown_args = parser.parse_known_args()
        actions = {
            "check": (CHECK_THOROUGH, lambda a: None),
            "pack": (CHECK_SANE, cms.pack),
            "submit": (CHECK_INSTANT, cms.submit_all),
            "analyze": (CHECK_NONE, cms.analyze),
            "dump": (CHECK_NONE, cms.dump_data),
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
    elif args.subcommand == "visualize":
        visualize_command(args)
    elif args.subcommand == "license":
        print(license_gnu if args.print else license)
    else:
        raise RuntimeError(f"Unknown subcommand {args.subcommand}")

    return result


def main_wrapped():
    result = main(sys.argv[1:])
    if result:
        exit(1)


if __name__ == "__main__":
    main_wrapped()
