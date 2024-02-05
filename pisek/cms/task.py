from cms.db.task import Task
from sqlalchemy.orm import Session
import re

from pisek.cms.dataset import create_dataset
from pisek.task_config import TaskConfig


def create_task(session: Session, config: TaskConfig):
    name = config.task_name

    task = Task(name=name, title=name, submission_format=[get_default_file_name(name)])
    dataset = create_dataset(session, config, task)

    task.active_dataset = dataset

    session.add(task)
    session.add(dataset)


def get_default_file_name(name: str):
    name = re.sub("[^a-zA-Z0-9]+", "_", name)
    return f"{name}.%l"
