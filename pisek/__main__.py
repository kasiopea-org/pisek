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

from pisek.jobs.task_pipeline import TaskPipeline
from pisek.utils.pipeline_tools import run_pipeline, PATH, locked_folder

from pisek.utils.util import clean_task_dir
from pisek.utils.text import eprint
from pisek.license import license, license_gnu
from pisek.visualize import visualize


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
        eprint(f"Specify a solution name to test.")
        eprint(f"Example:   pisek [--all_tests] test solution solve_slow_4b")
        return 1

    eprint(f"Testing solution: {args.solution}")
    return test_task(args, solutions=[args.solution])


def test_generator(args):
    eprint(f"Testing generator")
    return test_task(args, solutions=[])


@locked_folder
def clean_directory(args) -> bool:
    task_dir = PATH
    eprint(f"Cleaning directory: {os.path.abspath(task_dir)}")
    return clean_task_dir(task_dir)


def main(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Tool for developing tasks for programming competitions. "
            "Full documentation is at https://github.com/kasiopea-org/pisek"
        )
    )

    def add_argument_timeout(parser):
        parser.add_argument(
            "--timeout",
            "-t",
            type=float,
            help="Override time limit for solutions to TIMEOUT seconds.",
        )

    def add_argument_full(parser):
        parser.add_argument(
            "--full", "-f", action="store_true", help="Don't stop on first failure."
        )

    def add_argument_strict(parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Interpret warnings as failures (for final check).",
        )

    def add_argument_ninputs(parser):
        parser.add_argument(
            "--inputs",
            "-n",
            type=int,
            default=5,
            help="Test on INPUTS difference inputs (only for Kasiopea tasks).",
        )

    def add_argument_all_inputs(parser):
        parser.add_argument(
            "--all-inputs",
            action="store_true",
            help="Test each solution on all inputs.",
        )

    def add_argument_skip_on_timeout(parser):
        parser.add_argument(
            "--skip-on-timeout",
            action="store_true",
            help="Skip all following inputs on first timeout.",
        )

    def add_argument_testing_log(parser):
        parser.add_argument(
            "--testing-log",
            action="store_true",
            help="Write test results to testing_log.json.",
        )

    def add_argument_clean(parser):
        parser.add_argument(
            "--clean",
            "-c",
            action="store_true",
            help="Clean directory beforehand.",
        )

    def add_argument_plain(parser):
        parser.add_argument(
            "--plain",
            action="store_true",
            help="Do not use ANSI escape sequences.",
        )

    def add_argument_no_jumps(parser):
        parser.add_argument(
            "--no-jumps",
            action="store_true",
            help="Do not use ANSI control sequences.",
        )

    def add_argument_no_colors(parser):
        parser.add_argument(
            "--no-colors",
            action="store_true",
            help="Do not use ANSI color sequences.",
        )

    def add_argument_filter(parser):
        parser.add_argument(
            "--filter",
            "-f",
            choices=("slowest", "all"),
            default="slowest",
            type=str,
            help="Which inputs to show:\n slowest: Show slowest input only.\n all: Show all inputs.",
        )

    def add_argument_bundle(parser):
        parser.add_argument(
            "--bundle",
            "-b",
            action="store_true",
            help="Don't group inputs by subtask.",
        )

    def add_argument_solutions(parser):
        parser.add_argument(
            "--solutions",
            "-s",
            default=None,
            type=str,
            nargs="*",
            help="Visualize only solutions with a name or source in SOLUTIONS.",
        )

    def add_argument_filename(parser):
        parser.add_argument(
            "--filename",
            default="testing_log.json",
            type=str,
            help="Read testing log from FILENAME.",
        )

    def add_argument_limit(parser):
        parser.add_argument(
            "--limit",
            "-l",
            default=None,
            type=float,
            help="Visualize as if the time limit was LIMIT seconds.",
        )

    def add_argument_segments(parser):
        parser.add_argument(
            "--segments",
            "-S",
            type=int,
            help="Print bars SEGMENTS characters wide.",
        )

    def add_argument_description(parser):
        parser.add_argument(
            "--description",
            "-d",
            type=str,
            help="Created the dataset with a description of DESCRIPTION.",
        )

    def add_argument_dataset(parser):
        parser.add_argument(
            "--dataset",
            "-d",
            type=str,
            required=True,
            help="Use the dataset with the description DESCRIPTION.",
        )

    add_argument_timeout(parser)
    add_argument_full(parser)
    add_argument_strict(parser)
    add_argument_ninputs(parser)
    add_argument_all_inputs(parser)
    add_argument_skip_on_timeout(parser)
    add_argument_clean(parser)
    add_argument_plain(parser)
    add_argument_no_jumps(parser)
    add_argument_no_colors(parser)
    add_argument_testing_log(parser)

    subparsers = parser.add_subparsers(help="Run this subcommand.", dest="subcommand")

    parser_test = subparsers.add_parser("test", help="test")
    parser_test.add_argument(
        "target",
        choices=["solution", "generator"],
        help="Test this program type ('solution' or 'generator').",
    )
    parser_test.add_argument(
        "solution", type=str, help="Test the solution with this name.", nargs="?"
    )
    add_argument_timeout(parser_test)
    add_argument_full(parser_test)
    add_argument_strict(parser_test)
    add_argument_ninputs(parser_test)
    add_argument_clean(parser_test)

    _parser_clean = subparsers.add_parser("clean", help="Clean the directory.")

    parser_visualize = subparsers.add_parser(
        "visualize", help="Show solutions statistics and closeness to limit."
    )
    add_argument_filter(parser_visualize)
    add_argument_bundle(parser_visualize)
    add_argument_solutions(parser_visualize)
    add_argument_filename(parser_visualize)
    add_argument_limit(parser_visualize)
    add_argument_segments(parser_visualize)

    parser_license = subparsers.add_parser("license", help="Print license")
    parser_license.add_argument(
        "--print", action="store_true", help="Print entire license."
    )

    parser_cms = subparsers.add_parser("cms", help="Import tasks into CMS.")
    subparsers_cms = parser_cms.add_subparsers(
        help="The subcommand to run.", dest="cms_subcommand"
    )

    parser_cms_create = subparsers_cms.add_parser("create", help="Create a new task.")
    add_argument_description(parser_cms_create)

    parser_cms_update = subparsers_cms.add_parser(
        "update", help="Update the basic properties of an existing task."
    )

    parser_cms_add = subparsers_cms.add_parser(
        "add", help="Add a dataset to an existing task."
    )
    add_argument_description(parser_cms_add)
    parser_cms_add.add_argument(
        "--no-autojudge",
        action="store_true",
        help="Disable background judging for the new dataset.",
    )

    parser_cms_submit = subparsers_cms.add_parser(
        "submit", help="Submit reference solutions for evaluation using CMS."
    )
    parser_cms_submit.add_argument(
        "--username",
        "-u",
        type=str,
        required=True,
        help="Submit as the user with username USERNAME.",
    )

    parser_cms_testing_log = subparsers_cms.add_parser(
        "testing-log",
        help="Generate a testing log for reference solutions submitted to CMS.",
    )
    add_argument_dataset(parser_cms_testing_log)

    parser_cms_check = subparsers_cms.add_parser(
        "check",
        help="Check if reference solutions scored as expected in CMS.",
    )
    add_argument_dataset(parser_cms_check)

    args = parser.parse_args(argv)

    result = None

    if args.clean:
        if not clean_directory(args):
            return 1

    if args.subcommand == "test":
        if args.target == "solution":
            result = test_solution(args)
        elif args.target == "generator":
            result = test_generator(args)
        else:
            eprint(f"Unknown testing target: {args.target}")
            exit(1)
    elif args.subcommand is None:
        result = test_task(args, solutions=None, target="all")
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
