from typing import Iterator
from cms.db.task import Task, Dataset
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
import re

from pisek.cms.testcase import create_testcase, get_testcases
from pisek.task_config import TaskConfig

TASK_TYPES = {"batch": "Batch", "communication": "Communication"}


def create_dataset(session: Session, config: TaskConfig, task: Task) -> Dataset:
    score_params = get_group_score_parameters(config)

    dataset = Dataset(
        description="Default",
        autojudge=True,
        task_type=TASK_TYPES[config.task_type],
        task_type_parameters=("alone", ("", ""), "diff"),
        score_type="GroupMin",
        score_type_parameters=score_params,
        task=task,
    )

    files = FileCacher()

    for testcase in get_testcases(config):
        create_testcase(session, files, dataset, *testcase)

    session.add(dataset)
    return dataset


def get_group_score_parameters(config: TaskConfig) -> list[tuple[str, int]]:
    params = []

    for _name, subtask in config.subtasks.subenvs():
        globs = map(strip_input_extention, subtask.all_globs)
        params.append((subtask.score, globs_to_regex(globs)))

    return params


def strip_input_extention(file: str) -> str:
    if not file.endswith(".in"):
        raise RuntimeError("Input file {file} does not have a .in extention")

    return file[:-3]


def glob_char_to_regex(c: str) -> str:
    if c == "?":
        return "."
    elif c == "*":
        return ".*"
    else:
        return re.escape(c)


def globs_to_regex(globs: Iterator[str]) -> str:
    patterns = []

    for glob in globs:
        pattern = "".join(map(glob_char_to_regex, glob))
        patterns.append(f"({pattern})")

    return f"^{'|'.join(patterns)}$"
