from cms.db.task import Task, Dataset
from sqlalchemy.orm import Session
import re

def create_task(session: Session, name: str):
    task = Task(
        name=name,
        title=name,
        submission_format=[get_default_file_name(name)]
    )

    dataset = Dataset(
        description="Default",
        autojudge=True,
        task_type="Batch",
        task_type_parameters=["alone", ["", ""], "diff"],
        score_type="Sum",
        score_type_parameters=100,
        task=task
    )

    task.active_dataset = dataset

    session.add(task)
    session.add(dataset)

def get_default_file_name(name: str):
    name = re.sub("[^a-zA-Z0-9]+", "_")
    return f"{name}.%l"
