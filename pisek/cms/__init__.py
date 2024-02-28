from cms.db.session import Session
from sqlalchemy.exc import IntegrityError

from pisek.cms.dataset import create_dataset, get_dataset
from pisek.cms.result import create_testing_log, check_results
from pisek.cms.submission import get_participation, submit_all
from pisek.cms.task import create_task, get_task, set_task_settings
from pisek.env.env import Env
from pisek.jobs.cache import Cache
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.utils.pipeline_tools import PATH


def prepare_files(env: Env):
    contest_type = env.config.contest_type

    if contest_type != "cms":
        raise RuntimeError(f"Cannot upload {contest_type}-type task to CMS")

    env = env.fork()
    env.solutions = [env.config.primary_solution]

    if TaskPipeline(env).run_jobs(Cache(env), env) != 0:
        raise RuntimeError("Failed to test primary solution, cannot upload to CMS")


def create(args):
    env = Env.load(PATH, **vars(args))
    prepare_files(env)

    session = Session()

    description = args.description

    task = create_task(session, env, description)
    dataset = task.active_dataset

    try:
        session.commit()
    except IntegrityError as e:
        raise RuntimeError(
            "Failed to commit transaction, does the task already exist?"
        ) from e

    print(
        f'Created task {task.name} (id {task.id}) with dataset "{dataset.description}" (id {dataset.id})'
    )


def update(args):
    env = Env.load(PATH, **vars(args))
    session = Session()

    task = get_task(session, env.config)
    set_task_settings(task, env.config)

    session.commit()

    print(f"Updated task {task.name} (id {task.id})")


def add(args):
    env = Env.load(PATH, **vars(args))
    prepare_files(env)

    session = Session()

    description = args.description
    autojudge = not args.no_autojudge

    task = get_task(session, env.config)
    dataset = create_dataset(session, env, task, description, autojudge)

    try:
        session.commit()
    except IntegrityError as e:
        raise RuntimeError(
            "Failed to commit transaction, does a dataset with this description exist already?"
        ) from e

    print(f'Added dataset "{dataset.description}" (id {dataset.id})')


def submit(args):
    env = Env.load(PATH, **vars(args))
    session = Session()

    username = args.username

    task = get_task(session, env.config)
    participation = get_participation(session, task, username)
    submissions = submit_all(session, env, task, participation)

    session.commit()

    for solution, submission in submissions:
        print(f"Submitted {solution} with id {submission.id}")


def testing_log(args):
    env = Env.load(PATH, **vars(args))
    session = Session()

    description = args.dataset

    task = get_task(session, env.config)
    dataset = get_dataset(session, task, description)
    create_testing_log(session, env, dataset)


def check(args):
    env = Env.load(PATH, **vars(args))
    session = Session()

    description = args.dataset

    task = get_task(session, env.config)
    dataset = get_dataset(session, task, description)
    check_results(session, env, dataset)
