from cms.db.task import Task
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
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


def get_task(session: Session, config: TaskConfig):
    try:
        return session.query(Task).filter(Task.name == config.task_name).one()
    except NoResultFound as e:
        raise RuntimeError("This task has not been imported into CMS yet") from e


def get_default_file_name(name: str):
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return f"{name}.%l"
