from cms.db.task import Task, Dataset, Testcase
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from os import path
from glob import glob
from itertools import chain

from pisek.task_config import TaskConfig
from pisek.jobs.parts.task_job import GENERATED_SUBDIR, OUTPUTS_SUBDIR


def create_dataset(session: Session, config: TaskConfig, task: Task) -> Dataset:
    name = config["task_name"]

    dataset = Dataset(
        description="Default",
        autojudge=True,
        task_type="Batch",
        task_type_parameters=["alone", ["", ""], "diff"],
        score_type="Sum",
        score_type_parameters=100,
        task=task,
    )

    files = FileCacher()

    for testcase in get_testcases(config):
        create_testcase(session, files, dataset, *testcase)

    session.add(dataset)
    return dataset


def create_testcase(
    session: Session,
    files: FileCacher,
    dataset: Dataset,
    codename: str,
    input_file: str,
    output_file: str | None,
) -> Testcase:
    input = files.put_file_from_path(input_file, f"Input for testcase {codename}")

    if output_file is not None:
        output = files.put_file_from_path(
            output_file, f"Output for testcase {codename}"
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


def get_testcases(config: TaskConfig) -> list[tuple[str, str, str | None]]:
    test_dir = path.join(config.data_subdir, GENERATED_SUBDIR)
    output_dir = path.join(config.data_subdir, OUTPUTS_SUBDIR)
    sample_dir = config.static_subdir

    sample_globs = config.subtasks["0"].in_globs
    test_globs = config.subtasks.all_globs
    solution = config.primary_solution

    outputs_needed = config.task_type == "batch" and config.judge_needs_out

    testcases = []

    for input_file in get_inputs_in(sample_globs, sample_dir):
        codename = input_file[:-3]
        input_file = path.join(sample_dir, input_file)

        if outputs_needed:
            output_file = path.join(sample_dir, f"{codename}.out")
        else:
            output_file = None

        testcases.append((codename, input_file, output_file))

    for input_file in get_inputs_in(test_globs, test_dir):
        codename = input_file[:-3]
        input_file = path.join(test_dir, input_file)

        if outputs_needed:
            output_file = path.join(output_dir, f"{codename}.{solution}.out")
        else:
            output_file = None

        testcases.append((codename, input_file, output_file))

    return testcases


def get_inputs_in(globs: list[str], dir: str) -> list[str]:
    files = chain.from_iterable(glob(g, root_dir=dir) for g in globs)
    inputs = filter(lambda f: f.endswith(".in"), files)
    return list(set(inputs))
