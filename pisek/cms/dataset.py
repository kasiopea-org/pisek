from cms.db.task import Task, Dataset
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from pisek.cms.testcase import create_testcase, get_testcases

from pisek.task_config import TaskConfig


def create_dataset(session: Session, config: TaskConfig, task: Task) -> Dataset:
    name = config["task_name"]

    dataset = Dataset(
        description="Default",
        autojudge=True,
        task_type="Batch",
        task_type_parameters=["alone", ["", ""], "diff"],
        score_type="Sum",
        score_type_parameters=100,
        task=task,
    )

    files = FileCacher()

    for testcase in get_testcases(config):
        create_testcase(session, files, dataset, *testcase)

    session.add(dataset)
    return dataset
