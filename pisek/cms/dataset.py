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

from typing import Iterator, Any, Optional
from cms.db.task import Task, Dataset, Manager
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from os import path, listdir
import re
import datetime

from pisek.cms.testcase import create_testcase, get_testcases
from pisek.env.env import Env
from pisek.env.task_config import JudgeType, TaskConfig, TaskType
from pisek.paths import TaskPath


def create_dataset(
    session: Session,
    env: Env,
    task: Task,
    description: Optional[str],
    autojudge: bool = True,
) -> Dataset:
    if description is None:
        description = create_description()

    config = env.config

    score_params = get_group_score_parameters(config)

    task_type: str
    task_params: Any

    if config.task_type == TaskType.batch:
        task_type = "Batch"
        task_params = (
            "grader" if config.stub is not None else "alone",
            ("", ""),
            "comparator" if config.out_check == JudgeType.judge else "diff",
        )
    elif config.task_type == TaskType.communication:
        task_type = "Communication"
        task_params = (1, "stub" if config.stub is not None else "alone", "std_io")
    else:
        raise RuntimeError(f"Cannot upload {config.task_type} task to CMS")

    dataset = Dataset(
        description=description,
        autojudge=autojudge,
        task_type=task_type,
        task_type_parameters=task_params,
        score_type="GroupMin",
        score_type_parameters=score_params,
        time_limit=config.cms.time_limit,
        memory_limit=config.cms.mem_limit * 1024 * 1024,
        task=task,
    )

    session.add(dataset)

    files = FileCacher()

    for testcase in get_testcases(env):
        create_testcase(session, files, dataset, *testcase)

    add_judge(session, files, env, dataset)
    add_stubs(session, files, env, dataset)
    add_headers(session, files, env, dataset)

    return dataset


def get_group_score_parameters(config: TaskConfig) -> list[tuple[int, str]]:
    params = []

    for subtask in config.subtasks.values():
        globs = map(strip_input_extention, subtask.all_globs)
        params.append((subtask.points, globs_to_regex(globs)))

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


def add_judge(session: Session, files: FileCacher, env: Env, dataset: Dataset):
    config = env.config

    if config.out_check != JudgeType.judge:
        return

    assert config.out_judge is not None

    if config.task_type == TaskType.batch:
        judge_name = "checker"
    elif config.task_type == TaskType.communication:
        judge_name = "manager"

    judge = files.put_file_from_path(
        TaskPath.executable_path(env, path.basename(config.out_judge)).path,
        f"{judge_name} for {config.name}",
    )
    session.add(Manager(dataset=dataset, filename=judge_name, digest=judge))


MISSING_STUB_ERROR = "Language not supported"
ERROR_STUBS = {
    ".c": f"#error {MISSING_STUB_ERROR}",
    ".cpp": f"#error {MISSING_STUB_ERROR}",
    ".cs": f"#error {MISSING_STUB_ERROR}",
    ".hs": f'{{-# LANGUAGE DataKinds #-}} import GHC.TypeLits; type Error = TypeError (Text "{MISSING_STUB_ERROR}")',
    ".java": MISSING_STUB_ERROR,
    ".pas": f"{{$Message Fatal '{MISSING_STUB_ERROR}'}}",
    ".php": f"<?php throw new Exception('{MISSING_STUB_ERROR}'); ?>",
    ".py": MISSING_STUB_ERROR,
    ".rs": f'compile_error!("{MISSING_STUB_ERROR}");',
}


def add_stubs(session: Session, files: FileCacher, env: Env, dataset: Dataset):
    config = env.config

    if config.stub is None:
        return

    if config.task_type == TaskType.batch:
        stub_basename = "grader"
    elif config.task_type == TaskType.communication:
        stub_basename = "stub"

    directory, target_basename = path.split(config.stub)
    directory = path.normpath(directory)

    exts = set()

    for filename in listdir(directory):
        basename, ext = path.splitext(filename)

        if basename != target_basename:
            continue

        stub = files.put_file_from_path(
            path.join(directory, filename),
            f"{stub_basename}{ext} for {config.name}",
        )
        session.add(
            Manager(dataset=dataset, filename=f"{stub_basename}{ext}", digest=stub)
        )

        exts.add(ext)

    for ext, content in ERROR_STUBS.items():
        if ext in exts:
            continue

        stub = files.put_file_content(
            content.encode(), f"{stub_basename}{ext} for {config.name}"
        )
        session.add(
            Manager(dataset=dataset, filename=f"{stub_basename}{ext}", digest=stub)
        )


def add_headers(session: Session, files: FileCacher, env: Env, dataset: Dataset):
    config = env.config

    for header in config.headers:
        basename = path.basename(header)

        header = files.put_file_from_path(
            header, f"Header {basename} for {config.name}"
        )
        session.add(Manager(dataset=dataset, filename=basename, digest=header))


def get_dataset(session: Session, task: Task, description: str) -> Dataset:
    try:
        return (
            session.query(Dataset)
            .filter(Dataset.task == task)
            .filter(Dataset.description == description)
            .one()
        )
    except NoResultFound as e:
        raise RuntimeError(
            f'The task has no dataset with the description "{description}"'
        ) from e


def create_description() -> str:
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return date
