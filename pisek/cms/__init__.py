from cms.db.session import Session

from pisek.cms.task import create_task
from pisek.task_config import TaskConfig

def create(args):
    config = TaskConfig(".")
    session = Session()

    name = config["task_name"]

    create_task(session, name)

    session.commit()
