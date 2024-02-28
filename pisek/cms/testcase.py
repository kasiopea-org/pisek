from cms.db.task import Dataset, Testcase
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from os import path
from glob import glob
from itertools import chain

from pisek.env.env import Env
from pisek.paths import TaskPath


def create_testcase(
    session: Session,
    files: FileCacher,
    dataset: Dataset,
    codename: str,
    input_file: TaskPath,
    output_file: TaskPath | None,
) -> Testcase:
    input = files.put_file_from_path(
        input_file.fullpath, f"Input for testcase {codename}"
    )

    if output_file is not None:
        output = files.put_file_from_path(
            output_file.fullpath, f"Output for testcase {codename}"
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
    output_dir = TaskPath.output_path(env)
    sample_dir = TaskPath.static_path(env)

    sample_globs = config.subtasks[0].in_globs
    test_globs = config.input_globs
    solution = config.solutions[config.primary_solution].source

    outputs_needed = config.task_type == "batch" and config.judge_needs_out

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
    files = chain.from_iterable(glob(g, root_dir=dir.fullpath) for g in globs)
    return list(set(files))
