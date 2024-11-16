# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

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
import sys
import signal

from pisek.utils.util import clean_task_dir
from pisek.utils.text import eprint
from pisek.utils.colors import ColorSettings
from pisek.license import license, license_gnu
from pisek.visualize import visualize
from pisek.config.config_tools import update_and_replace_config
from pisek.version import print_version

from pisek.jobs.task_pipeline import TaskPipeline
from pisek.utils.pipeline_tools import run_pipeline, PATH, locked_folder


def sigint_handler(sig, frame):
    eprint("\rStopping...")
    sys.exit(2)


@locked_folder
def test_task(args, **kwargs):
    return test_task_path(PATH, **vars(args), **kwargs)


def test_task_path(path, solutions: Optional[list[str]] = None, **env_args):
    return run_pipeline(path, TaskPipeline, solutions=solutions, **env_args)


def test_solution(args):
    if args.solution is None:
        eprint("Specify a solution name to test.")
        eprint("Example:   pisek [--all_tests] test solution solve_slow_4b")
        return 1

    eprint(f"Testing solution: {args.solution}")
    return test_task(args, solutions=[args.solution])


def test_generator(args):
    eprint("Testing generator")
    return test_task(args, solutions=[])


@locked_folder
def clean_directory(args) -> bool:
    task_dir = PATH
    eprint(f"Cleaning directory: {os.path.abspath(task_dir)}")
    return clean_task_dir(task_dir, args.pisek_dir)


def main(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Tool for developing tasks for programming competitions. "
            "Full documentation is at https://github.com/kasiopea-org/pisek"
        )
    )

    def add_argument_description(parser):
        parser.add_argument(
            "--description",
            "-d",
            type=str,
            help="create the dataset with the description DESCRIPTION",
        )

    def add_argument_dataset(parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--dataset",
            "-d",
            type=str,
            required=False,
            help="use the dataset with the description DESCRIPTION",
        )

        group.add_argument(
            "--active-dataset",
            "-a",
            action="store_true",
            help="use active dataset",
        )

    # ------------------------------- pisek -------------------------------

    parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="clean directory beforehand",
    )
    parser.add_argument(
        "--plain",
        "-p",
        action="store_true",
        help="do not use ANSI escape sequences",
    )
    parser.add_argument(
        "--no-jumps",
        action="store_true",
        help="do not use ANSI cursor movement & clear sequences",
    )
    parser.add_argument(
        "--no-colors",
        action="store_true",
        help="do not use ANSI color sequences",
    )
    parser.add_argument(
        "--pisek-dir",
        help="pisek directory for higher level settings",
        type=str,
    )

    subparsers = parser.add_subparsers(
        help="subcommand to run", dest="subcommand", required=True
    )

    # ------------------------------- pisek version -------------------------------

    parser_version = subparsers.add_parser("version", help="print current version")

    # ------------------------------- pisek test -------------------------------

    parser_test = subparsers.add_parser("test", help="test task")
    parser_test.add_argument(
        "target",
        choices=["generator", "solution", "all"],
        nargs="?",
        default="all",
        help="what to test?",
    )
    parser_test.add_argument(
        "solution", type=str, help="name of the solution to test", nargs="?"
    )
    parser_test.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="be more verbose (enter multiple times for even more verbosity)",
    )
    parser_test.add_argument(
        "--file-contents",
        "-C",
        action="store_true",
        help="show file contents on error",
    )
    parser_test.add_argument(
        "--timeout",
        "-t",
        type=float,
        help="override time limit for solutions to TIMEOUT seconds",
    )
    parser_test.add_argument(
        "--full", "-f", action="store_true", help="don't stop on first failure"
    )
    parser_test.add_argument(
        "--strict",
        action="store_true",
        help="interpret warnings as failures (for final check)",
    )
    parser_test.add_argument(
        "--repeat-inputs",
        "-n",
        type=int,
        default=1,
        help="generate REPEAT_INPUTS times more inputs (seeded inputs only)",
    )
    parser_test.add_argument(
        "--all-inputs",
        "-a",
        action="store_true",
        help="test each solution on all inputs",
    )
    parser_test.add_argument(
        "--skip-on-timeout",
        action="store_true",
        help="skip all following inputs on first timeout",
    )
    parser_test.add_argument(
        "--testing-log",
        "-T",
        action="store_true",
        help="write test results to testing_log.json",
    )

    # ------------------------------- pisek clean -------------------------------

    parser_clean = subparsers.add_parser("clean", help="clean task directory")

    # ------------------------------- pisek config -------------------------------

    parser_config = subparsers.add_parser("config", help="manage task config")
    config_subparsers = parser_config.add_subparsers(
        help="subcommand to run", dest="config_subcommand", required=True
    )
    config_subparsers.add_parser(
        "update", help="update config to newest version (replaces the config)"
    )

    # ------------------------------- pisek visualize -------------------------------

    parser_visualize = subparsers.add_parser(
        "visualize", help="show solution statistics and closeness to limit"
    )
    parser_visualize.add_argument(
        "--filter",
        "-f",
        choices=("slowest", "all"),
        default="slowest",
        type=str,
        help="which inputs to show (slowest/all)",
    )
    parser_visualize.add_argument(
        "--bundle",
        "-b",
        action="store_true",
        help="don't group inputs by subtask",
    )
    parser_visualize.add_argument(
        "--solutions",
        "-s",
        default=None,
        type=str,
        nargs="*",
        help="visualize only solutions with a name or source in SOLUTIONS",
    )
    parser_visualize.add_argument(
        "--filename",
        default="testing_log.json",
        type=str,
        help="read testing log from FILENAME",
    )
    parser_visualize.add_argument(
        "--limit",
        "-l",
        default=None,
        type=float,
        help="visualize as if the time limit was LIMIT seconds",
    )
    parser_visualize.add_argument(
        "--segments",
        "-S",
        type=int,
        help="print bars SEGMENTS characters wide",
    )

    # ------------------------------- pisek license -------------------------------

    parser_license = subparsers.add_parser("license", help="print license")
    parser_license.add_argument(
        "--print", action="store_true", help="print entire license"
    )

    # ------------------------------- pisek cms -------------------------------

    parser_cms = subparsers.add_parser("cms", help="import task into CMS")
    subparsers_cms = parser_cms.add_subparsers(
        help="subcommand to run", dest="cms_subcommand", required=True
    )

    parser_cms_create = subparsers_cms.add_parser("create", help="create a new task")
    add_argument_description(parser_cms_create)

    parser_cms_update = subparsers_cms.add_parser(
        "update", help="update the basic properties of an existing task"
    )

    parser_cms_add = subparsers_cms.add_parser(
        "add", help="add a dataset to an existing task"
    )
    add_argument_description(parser_cms_add)
    parser_cms_add.add_argument(
        "--no-autojudge",
        action="store_true",
        help="disable background judging for the new dataset",
    )

    parser_cms_submit = subparsers_cms.add_parser(
        "submit", help="submit reference solutions for evaluation using CMS"
    )
    parser_cms_submit.add_argument(
        "--username",
        "-u",
        type=str,
        required=True,
        help="submit as the user with username USERNAME",
    )

    parser_cms_testing_log = subparsers_cms.add_parser(
        "testing-log",
        help="generate a testing log for reference solutions submitted to CMS",
    )
    add_argument_dataset(parser_cms_testing_log)

    parser_cms_check = subparsers_cms.add_parser(
        "check",
        help="check if reference solutions scored as expected in CMS",
    )
    add_argument_dataset(parser_cms_check)

    parser_cms_export = subparsers_cms.add_parser(
        "export",
        help="Export inputs and outputs, for publishing.",
    )
    parser_cms_export.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Save tests into this directory.",
    )

    args = parser.parse_args(argv)
    ColorSettings.set_state(not args.plain and not args.no_colors)

    result = None

    if args.clean:
        if not clean_directory(args):
            return 1

    if args.subcommand == "version":
        result = print_version()
    elif args.subcommand == "test":
        if args.target == "generator":
            result = test_generator(args)
        elif args.target == "solution":
            result = test_solution(args)
        elif args.target == "all":
            result = test_task(args, solutions=None)
        else:
            eprint(f"Unknown testing target: {args.target}")
            exit(1)

    elif args.subcommand == "config":
        if args.config_subcommand == "update":
            result = not update_and_replace_config(PATH, args.pisek_dir)
        else:
            raise RuntimeError(f"Unknown config command {args.config_subcommand}")

    elif args.subcommand == "cms":
        args, unknown_args = parser.parse_known_args()

        try:
            import pisek.cms as cms
        except ImportError as err:
            err.add_note("Failed to locate CMS installation")
            raise

        if args.cms_subcommand == "create":
            result = cms.create(args)
        elif args.cms_subcommand == "update":
            result = cms.update(args)
        elif args.cms_subcommand == "add":
            result = cms.add(args)
        elif args.cms_subcommand == "submit":
            result = cms.submit(args)
        elif args.cms_subcommand == "testing-log":
            result = cms.testing_log(args)
        elif args.cms_subcommand == "check":
            result = cms.check(args)
        elif args.cms_subcommand == "export":
            result = cms.export(args)
        else:
            raise RuntimeError(f"Unknown CMS command {args.cms_subcommand}")

    elif args.subcommand == "clean":
        result = not clean_directory(args)
    elif args.subcommand == "visualize":
        result = visualize(PATH, **vars(args))
    elif args.subcommand == "license":
        print(license_gnu if args.print else license)
    else:
        raise RuntimeError(f"Unknown subcommand {args.subcommand}")

    return result


def main_wrapped():
    signal.signal(signal.SIGINT, sigint_handler)
    result = main(sys.argv[1:])

    if result:
        exit(1)


if __name__ == "__main__":
    main_wrapped()
