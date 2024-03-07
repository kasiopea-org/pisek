# pisek cms - Tool for importing tasks from Pisek into CMS.
#
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# The CMS module imports and calls internal CMS libraries,
# as well as dependencies of CMS (sqlalchemy).
# Since these dependencies aren't declared anywhere, importing this module
# will cause an exception on most installations.
# It is therefore important not to import this module unless a cms command has actually been called.

# The implementation uses CMS's sqlalchemy types to make changes to the database.
# It also uses some other APIs, like session creation.
# If CMS changes its database schema or some of its internal APIs,
# this module will likely break.

# This module obviously also uses internal methods of pisek,
# mostly config parsing and some general utilities.
# Large refactors in pisek will also require changes to this module.

# Some functionality is duplicated, most notably enumerating all inputs
# and finding the file extensions of solutions.
# All of this functionality is implemented inside private methods of pipeline jobs,
# making it inaccessible to part of Pisek that don't use the pipeline.

# The pipeline is called when creating a dataset, in order to generate inputs and outputs
# and to compile the judge.
# It is called as if the user requested the primary solution to be tested.

# One small thing to note is that which automatic submission corresponds
# to which solution isn't explicitly stored anywhere.
# Instead, the check and testing-log commands simply search the database for
# a matching (task, file hash, language) triple.

from argparse import Namespace
from cms.db.session import Session
from sqlalchemy.exc import IntegrityError

from pisek.cms.dataset import create_dataset, get_dataset
from pisek.cms.result import create_testing_log, check_results
from pisek.cms.submission import get_participation, submit_all
from pisek.cms.task import create_task, get_task, set_task_settings
from pisek.env.env import Env
from pisek.jobs.cache import Cache
from pisek.jobs.task_pipeline import TaskPipeline
from pisek.utils.pipeline_tools import with_env


def prepare_files(env: Env):
    contest_type = env.config.contest_type

    if contest_type != "cms":
        raise RuntimeError(f"Cannot upload {contest_type}-type task to CMS")

    env = env.fork()
    env.solutions = [env.config.primary_solution]

    if TaskPipeline(env).run_jobs(Cache(env), env) != 0:
        raise RuntimeError("Failed to test primary solution, cannot upload to CMS")


@with_env
def create(env: Env, args: Namespace) -> int:
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
    return 0


@with_env
def update(env: Env, args: Namespace) -> int:
    session = Session()

    task = get_task(session, env.config)
    set_task_settings(task, env.config)

    session.commit()

    print(f"Updated task {task.name} (id {task.id})")
    return 0


@with_env
def add(env: Env, args: Namespace) -> int:
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
    return 0


@with_env
def submit(env: Env, args: Namespace) -> int:
    session = Session()

    username = args.username

    task = get_task(session, env.config)
    participation = get_participation(session, task, username)
    submissions = submit_all(session, env, task, participation)

    session.commit()

    for solution, submission in submissions:
        print(f"Submitted {solution} with id {submission.id}")
    return 0


@with_env
def testing_log(env: Env, args: Namespace) -> int:
    session = Session()

    description = args.dataset

    task = get_task(session, env.config)
    dataset = get_dataset(session, task, description)
    success = create_testing_log(session, env, dataset)

    return 0 if success else 1


@with_env
def check(env: Env, args: Namespace) -> int:
    session = Session()

    description = args.dataset

    task = get_task(session, env.config)
    dataset = get_dataset(session, task, description)
    success = check_results(session, env, dataset)

    return 0 if success else 1
