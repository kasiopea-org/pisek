from typing import Iterator, Any, Optional
from cms.db.task import Task, Dataset, Manager
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from os import path, listdir
import re
import datetime

from pisek.cms.testcase import create_testcase, get_testcases
from pisek.task_config import TaskConfig
from pisek.jobs.parts.task_job import BUILD_DIR


def create_dataset(
    session: Session,
    config: TaskConfig,
    task: Task,
    description: Optional[str],
    autojudge: bool = True,
) -> Dataset:
    if description is None:
        description = create_description()

    score_params = get_group_score_parameters(config)

    task_type: str
    task_params: Any

    if config.task_type == "batch":
        task_type = "Batch"
        task_params = (
            "grader" if config.stub is not None else "alone",
            ("", ""),
            "comparator" if config.judge_type == "judge" else "diff",
        )
    elif config.task_type == "communication":
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
        time_limit=config.limits.cms.time_limit,
        memory_limit=(
            config.limits.cms.mem_limit * 1024 * 1024
            if config.limits.cms.mem_limit > 0
            else None
        ),
        task=task,
    )

    session.add(dataset)

    files = FileCacher()

    for testcase in get_testcases(config):
        create_testcase(session, files, dataset, *testcase)

    add_judge(session, files, config, dataset)
    add_stubs(session, files, config, dataset)
    add_headers(session, files, config, dataset)

    return dataset


def get_group_score_parameters(config: TaskConfig) -> list[tuple[int, str]]:
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


def add_judge(
    session: Session, files: FileCacher, config: TaskConfig, dataset: Dataset
):
    if config.judge_type != "judge":
        return

    if config.task_type == "batch":
        judge_name = "checker"
    elif config.task_type == "communication":
        judge_name = "manager"

    judge = files.put_file_from_path(
        path.join(BUILD_DIR, path.basename(config.judge)),
        f"{judge_name} for {config.task_name}",
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


def add_stubs(
    session: Session, files: FileCacher, config: TaskConfig, dataset: Dataset
):
    if config.stub is None:
        return

    if config.task_type == "batch":
        stub_basename = "grader"
    elif config.task_type == "communication":
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
            f"{stub_basename}{ext} for {config.task_name}",
        )
        session.add(
            Manager(dataset=dataset, filename=f"{stub_basename}{ext}", digest=stub)
        )

        exts.add(ext)

    for ext, content in ERROR_STUBS.items():
        if ext in exts:
            continue

        stub = files.put_file_content(
            content.encode(), f"{stub_basename}{ext} for {config.task_name}"
        )
        session.add(
            Manager(dataset=dataset, filename=f"{stub_basename}{ext}", digest=stub)
        )


def add_headers(
    session: Session, files: FileCacher, config: TaskConfig, dataset: Dataset
):
    for header in config.headers:
        basename = path.basename(header)

        header = files.put_file_from_path(
            header, f"Header {basename} for {config.task_name}"
        )
        session.add(Manager(dataset=dataset, filename=basename, digest=header))


def create_description() -> str:
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return date
