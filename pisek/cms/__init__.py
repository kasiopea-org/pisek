from cms.db.session import Session

from pisek.cms.task import create_task
from pisek.task_config import TaskConfig
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.pipeline_tools import PATH, run_pipeline


def prepare_files(config):
    contest_type = config.contest_type

    if contest_type != "cms":
        raise RuntimeError(f"Cannot upload {contest_type}-type task to CMS")

    run_pipeline(PATH, TaskPipeline, solutions=[config.primary_solution])


def create(args):
    config = TaskConfig(".")
    prepare_files(config)

    session = Session()

    create_task(session, config)

    session.commit()
