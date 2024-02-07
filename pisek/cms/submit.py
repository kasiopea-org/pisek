from cms.db.contest import Contest
from cms.db.task import Task
from cms.db.user import Participation, User
from cms.db.submission import Submission, File
from cms.db.filecacher import FileCacher
from cms.grading.language import Language
from cms.grading.languagemanager import get_language
from sqlalchemy.orm import Session
from os import path
from datetime import datetime

from pisek.task_config import SolutionConfig, TaskConfig


def get_participation(session: Session, task: Task, username: str) -> Participation:
    return (
        session.query(Participation)
        .join(User)
        .filter(Participation.contest_id == task.contest_id)
        .filter(User.username == username)
        .one()
    )


def submit_all(
    session: Session, config: TaskConfig, task: Task, participation: Participation
):
    files = FileCacher()

    for _name, solution in config.solutions.subenvs():
        submit(session, files, config, solution, task, participation)


def submit(
    session: Session,
    files: FileCacher,
    config: TaskConfig,
    solution: SolutionConfig,
    task: Task,
    participation: Participation,
):
    file_path, language = resolve_solution(task.contest, config, solution)

    if len(task.submission_format) != 1:
        raise RuntimeError(
            "Cannot submit solutions to tasks that require multiple files"
        )

    submission = Submission(
        timestamp=datetime.now(),
        language=language.name,
        participation=participation,
        task=task,
    )
    session.add(submission)

    filename = task.submission_format[0]
    digest = files.put_file_from_path(file_path, f"Solution to task {task}")

    session.add(File(filename=filename, digest=digest, submission=submission))


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
