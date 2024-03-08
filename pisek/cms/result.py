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

from typing import Optional, Any
from cms.db.task import Dataset
from cms.db.submission import SubmissionResult, Evaluation
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
import json

from pisek.cms.submission import get_submission
from pisek.env.env import Env
from pisek.jobs.parts.testing_log import TESTING_LOG
from pisek.env.task_config import SolutionConfig, SubtaskConfig
from pisek.utils.terminal import colored_env
from pisek.utils.text import eprint, tab


def create_testing_log(session: Session, env: Env, dataset: Dataset) -> bool:
    config = env.config
    files = FileCacher()

    payload: dict[str, Any] = {"source": "cms"}
    success = True

    for name, solution in config.solutions.items():
        results: list[Any] = []
        payload[name] = {"results": results}

        try:
            result = get_submission_result(session, files, env, solution, dataset)
        except SubmissionResultError as e:
            eprint(colored_env(f"Skipping {name}: {e}", "yellow", env))
            success = False
            continue

        evaluation: Evaluation
        for evaluation in result.evaluations:
            points: str | float
            result_type: str

            try:
                points = float(evaluation.outcome)

                if points >= 1:
                    result_type = "ok"
                elif points <= 0:
                    result_type = "wrong_answer"
                else:
                    result_type = "partial"
            except ValueError:
                points = evaluation.outcome
                result_type = "indeterminate"

            results.append(
                {
                    "time": evaluation.execution_time,
                    "wall_clock_time": evaluation.execution_wall_clock_time,
                    "memory": evaluation.execution_memory / (1024 * 1024),
                    "test": f"{evaluation.codename}.in",
                    "points": points,
                    "result": result_type,
                }
            )

    with open(TESTING_LOG, "w") as file:
        json.dump(payload, file, indent=4)

    return success


def check_results(session: Session, env: Env, dataset: Dataset) -> bool:
    config = env.config
    files = FileCacher()

    success = True

    solution: SolutionConfig
    for name, solution in config.solutions.items():
        try:
            result = get_submission_result(session, files, env, solution, dataset)

            if not result.scored():
                raise SubmissionResultError("This submission has not been scored yet")
        except SubmissionResultError as e:
            print(colored_env(f"Skipping {name}: {e}", "yellow", env))
            success = False
            continue

        score = result.score

        score_missed_target = None

        if solution.points is not None and score != solution.points:
            score_missed_target = f"{solution.points}"
        elif solution.points_above is not None and score < solution.points_above:
            score_missed_target = f"above {solution.points_above}"
        elif solution.points_below is not None and score > solution.points_below:
            score_missed_target = f"below {solution.points_below}"

        message = f"{name}: {score} points"

        if score_missed_target is not None:
            message += f" (should be {score_missed_target})"
            message = colored_env(message, "red", env)
            success = False

        print(message)

        subtasks: list[tuple[int, SubtaskConfig]] = list(config.subtasks.items())
        fractions = get_subtask_score_fractions(result.score_details)

        if fractions is None or len(fractions) != len(subtasks):
            message = "The task seems to use an unsupported score type, skipping checking subtasks"
            print(tab(colored_env(message, "red", env)))

            success = False
            continue

        target: str
        for (num, subtask), fraction, target in zip(
            subtasks, fractions, solution.subtasks
        ):
            name = subtask.name or f"Subtask {num}"

            if target == "X":
                correct = True
            elif target == "1":
                target_name = "correct"
                correct = fraction == 1.0
            elif target == "P":
                target_name = "partially correct"
                correct = 0.0 < fraction < 1.0
            else:
                assert target in (
                    "0",
                    "W",
                    "T",
                    "!",
                ), f"Unknown expected result '{target}'"

                target_name = "wrong"
                correct = fraction == 0.0

            message = f"{name}: {fraction}"

            if not correct:
                message += f" (should be {target_name})"
                message = colored_env(message, "red", env)
                success = False

            print(tab(message))

    return success


def get_subtask_score_fractions(score_details: Any) -> Optional[list[float]]:
    if not isinstance(score_details, list):
        return None

    results = []

    for subtask in score_details:
        if not isinstance(subtask, dict):
            return None

        if "score_fraction" not in subtask:
            return None

        fraction = subtask["score_fraction"]

        if not isinstance(fraction, float):
            return None

        results.append(fraction)

    return results


def get_submission_result(
    session: Session,
    files: FileCacher,
    env: Env,
    solution: SolutionConfig,
    dataset: Dataset,
) -> SubmissionResult:
    submission = get_submission(session, files, env, solution, dataset.task)

    if submission is None:
        raise SubmissionResultError("This solution has not been submitted yet")

    result: Optional[SubmissionResult] = (
        session.query(SubmissionResult)
        .filter(SubmissionResult.submission == submission)
        .filter(SubmissionResult.dataset == dataset)
        .one_or_none()
    )

    if result is None:
        raise SubmissionResultError(
            "The latest submission hasn't started evaluating on this dataset"
        )

    if result.compilation_failed():
        raise SubmissionResultError("The submission failed to compile")

    if not result.evaluated():
        raise SubmissionResultError("The submission is still being evaluated")

    return result


class SubmissionResultError(Exception):
    pass
