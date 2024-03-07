# pisek cms - Tool for importing tasks from Pisek into CMS.
#
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from cms.db.task import Dataset, Testcase
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from glob import glob
from itertools import chain

from pisek.env.env import Env
from pisek.env.task_config import TaskType
from pisek.paths import TaskPath


def create_testcase(
    session: Session,
    files: FileCacher,
    dataset: Dataset,
    codename: str,
    input_file: TaskPath,
    output_file: TaskPath | None,
) -> Testcase:
    input = files.put_file_from_path(input_file.path, f"Input for testcase {codename}")

    if output_file is not None:
        output = files.put_file_from_path(
            output_file.path, f"Output for testcase {codename}"
        )
    else:
        output = files.put_file_content(
            "No output".encode(), f"Almost empty output file"
        )

    testcase = Testcase(
        dataset=dataset, codename=codename, input=input, output=output, public=True
    )

    session.add(testcase)
    return testcase


def get_testcases(env: Env) -> list[tuple[str, TaskPath, TaskPath | None]]:
    config = env.config

    test_dir = TaskPath.generated_path(env)
    sample_dir = TaskPath.static_path(env)

    sample_globs = config.subtasks[0].in_globs
    test_globs = config.input_globs
    solution = config.solutions[config.primary_solution].source

    outputs_needed = config.task_type == TaskType.batch and config.judge_needs_out

    testcases = []

    for input in get_inputs_in(sample_globs, sample_dir):
        codename = input[:-3]
        input_file = TaskPath.static_path(env, input)

        if outputs_needed:
            output_file = TaskPath.output_static_file(env, input)
        else:
            output_file = None

        testcases.append((codename, input_file, output_file))

    for input in get_inputs_in(test_globs, test_dir):
        codename = input[:-3]
        input_file = TaskPath.input_path(env, input)

        if outputs_needed:
            output_file = TaskPath.output_file(env, input, solution)
        else:
            output_file = None

        testcases.append((codename, input_file, output_file))

    return testcases


def get_inputs_in(globs: list[str], dir: TaskPath) -> list[str]:
    files = chain.from_iterable(glob(g, root_dir=dir.path) for g in globs)
    return list(set(files))
