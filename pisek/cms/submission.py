from typing import Optional
from cms.db.contest import Contest
from cms.db.task import Task
from cms.db.user import Participation, User
from cms.db.submission import Submission, File
from cms.db.filecacher import FileCacher
from cms.grading.language import Language
from cms.grading.languagemanager import get_language
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import Session
from os import path
from datetime import datetime

from pisek.task_config import SolutionConfig, TaskConfig


def get_participation(session: Session, task: Task, username: str) -> Participation:
    if task.contest_id is None:
        raise RuntimeError("The task is not part of any contest")

    try:
        return (
            session.query(Participation)
            .join(User)
            .filter(Participation.contest_id == task.contest_id)
            .filter(User.username == username)
            .one()
        )
    except NoResultFound as e:
        raise RuntimeError(
            f'There is no user named "{username}" in the given contest'
        ) from e


def submit_all(
    session: Session, config: TaskConfig, task: Task, participation: Participation
) -> list[tuple[str, Submission]]:
    files = FileCacher()
    submissions = []

    for name, solution in config.solutions.subenvs():
        submission = submit(session, files, config, solution, task, participation)
        submissions.append((name, submission))

    return submissions


def submit(
    session: Session,
    files: FileCacher,
    config: TaskConfig,
    solution: SolutionConfig,
    task: Task,
    participation: Participation,
) -> Submission:
    file_path, language = resolve_solution(task.contest, config, solution)

    if len(task.submission_format) != 1:
        raise RuntimeError(
            "Cannot submit solutions to tasks that require multiple files"
        )

    digest = files.put_file_from_path(file_path, f"Solution to task {task.id}")
    submission = get_submission_of_digest(session, digest, language, task)

    if submission is not None:
        return submission

    submission = Submission(
        timestamp=datetime.now(),
        language=language.name,
        participation=participation,
        task=task,
    )
    session.add(submission)

    filename = task.submission_format[0]
    session.add(File(filename=filename, digest=digest, submission=submission))

    return submission


def get_submission(
    session: Session,
    files: FileCacher,
    config: TaskConfig,
    solution: SolutionConfig,
    task: Task,
) -> Optional[Submission]:
    file_path, language = resolve_solution(task.contest, config, solution)
    digest = files.put_file_from_path(file_path, f"Solution to task {task.name}")

    return get_submission_of_digest(session, digest, language, task)


def get_submission_of_digest(
    session: Session,
    digest: str,
    language: Language,
    task: Task,
) -> Optional[Submission]:
    return (
        session.query(Submission)
        .join(File)
        .filter(Submission.task == task)
        .filter(Submission.language == language.name)
        .filter(File.digest == digest)
        .order_by(Submission.timestamp.desc())
        .first()
    )


def resolve_solution(
    contest: Contest, config: TaskConfig, solution: SolutionConfig
) -> tuple[str, Language]:
    subdir = config.solutions_subdir
    source: str = solution.source

    for language_name in contest.languages:
        language: Language = get_language(language_name)

        for ext in language.source_extensions:
            if source.endswith(ext):
                file_path = path.join(subdir, source)
                return file_path, language

            file_path = path.join(subdir, source + ext)

            if path.isfile(file_path):
                return file_path, language

    raise RuntimeError(f"Solution {source} isn't available in any enabled language")
