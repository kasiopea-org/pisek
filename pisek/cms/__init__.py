from cms.db.session import Session
from pisek.cms.dataset import create_dataset

from pisek.cms.submit import get_participation, submit_all
from pisek.cms.task import create_task, get_task
from pisek.task_config import TaskConfig
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.pipeline_tools import PATH, run_pipeline


def prepare_files(config: TaskConfig):
    contest_type = config.contest_type

    if contest_type != "cms":
        raise RuntimeError(f"Cannot upload {contest_type}-type task to CMS")

    if run_pipeline(PATH, TaskPipeline, solutions=[config.primary_solution]) != 0:
        raise RuntimeError("Failed to test primary solution, cannot upload to CMS")


def create(args):
    config = TaskConfig(".")
    prepare_files(config)

    session = Session()

    description = args.description

    task = create_task(session, config, description)
    dataset = task.active_dataset

    session.commit()

    print(
        f'Created task {task.name} (id {task.id}) with dataset "{dataset.description}" (id {dataset.id})'
    )


def add(args):
    config = TaskConfig(".")
    prepare_files(config)

    session = Session()

    description = args.description
    autojudge = not args.no_autojudge

    task = get_task(session, config)
    dataset = create_dataset(session, config, task, description, autojudge)

    session.commit()

    print(f'Added dataset "{dataset.description}" (id {dataset.id})')


def submit(args):
    config = TaskConfig(".")
    session = Session()

    username = args.username

    task = get_task(session, config)
    participation = get_participation(session, task, username)
    submissions = submit_all(session, config, task, participation)

    session.commit()

    for solution, submission in submissions:
        print(f"Submitted {solution} with id {submission.id}")
