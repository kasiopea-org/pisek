from cms.db.task import Task, Dataset
from sqlalchemy.orm import Session
from sqlalchemy import select
import re

from pisek.cms.dataset import create_dataset
from pisek.task_config import TaskConfig


def create_task(session: Session, config: TaskConfig, description: str) -> Task:
    name = config.task_name

    task = Task(name=name, title=name, submission_format=[get_default_file_name(name)])
    dataset = create_dataset(session, config, task, description)

    task.active_dataset = dataset

    session.add(task)
    return task


def add_dataset(
    session: Session, config: TaskConfig, description: str, autojudge: bool
) -> Dataset:
    task = get_task(session, config)
    return create_dataset(session, config, task, description, autojudge)


def get_task(session: Session, config: TaskConfig):
    return session.query(Task).filter(Task.name == config.task_name).one()


def get_default_file_name(name: str):
    name = re.sub("[^a-zA-Z0-9]+", "_", name)
    return f"{name}.%l"
