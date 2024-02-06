from cms.db.session import Session

from pisek.cms.task import add_dataset, create_task, get_task
from pisek.task_config import TaskConfig
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.pipeline_tools import PATH, run_pipeline


def prepare_files(config):
    contest_type = config.contest_type

    if contest_type != "cms":
        raise RuntimeError(f"Cannot upload {contest_type}-type task to CMS")

    if run_pipeline(PATH, TaskPipeline, solutions=[config.primary_solution]) != 0:
        raise RuntimeError("Failed to test primary solution, cannot upload to CMS")


def create(args):
    config = TaskConfig(".")
    prepare_files(config)

    session = Session()

    create_task(session, config)

    session.commit()


def add(args):
    config = TaskConfig(".")
    prepare_files(config)

    session = Session()

    add_dataset(session, config)

    session.commit()
