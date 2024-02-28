from datetime import timedelta
from cms.db.task import Task
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
import re

from pisek.cms.dataset import create_dataset
from pisek.env.env import Env
from pisek.env.task_config import TaskConfig


def create_task(session: Session, env: Env, description: str) -> Task:
    config = env.config

    task = Task(name=config.name, title=config.name)
    set_task_settings(task, config)

    dataset = create_dataset(session, env, task, description)

    task.active_dataset = dataset

    session.add(task)
    return task


def set_task_settings(task: Task, config: TaskConfig):
    task.title = config.cms.title or config.name
    task.submission_format = config.cms.submission_format or [
        get_default_file_name(config.name)
    ]
    task.max_submission_number = config.cms.max_submissions
    task.min_submission_interval = (
        timedelta(seconds=config.cms.min_submission_interval)
        if config.cms.min_submission_interval is not None
        else None
    )
    task.score_precision = config.cms.score_precision
    task.score_mode = config.cms.score_mode
    task.feedback_level = config.cms.feedback_level


def get_task(session: Session, config: TaskConfig):
    try:
        return session.query(Task).filter(Task.name == config.name).one()
    except NoResultFound as e:
        raise RuntimeError("This task has not been imported into CMS yet") from e


def get_default_file_name(name: str):
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return f"{name}.%l"
