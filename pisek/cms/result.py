from typing import Optional, Any
from cms.db.task import Dataset
from cms.db.submission import SubmissionResult, Evaluation
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
import json

from pisek.cms.submission import get_submission
from pisek.jobs.parts.testing_log import TESTING_LOG
from pisek.task_config import SolutionConfig, TaskConfig


def create_testing_log(session: Session, config: TaskConfig, dataset: Dataset):
    files = FileCacher()

    payload: dict[str, Any] = {"source": "cms"}

    for name, solution in config.solutions.subenvs():
        results: list[Any] = []
        payload[name] = {"results": results}

        try:
            result = get_submission_result(session, files, config, solution, dataset)
        except SubmissionResultError as e:
            print(f"Skipping {name}: {e}")
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
                    "test": f"{evaluation.codename}.in",
                    "points": points,
                    "result": result_type,
                }
            )

    with open(TESTING_LOG, "w") as file:
        json.dump(payload, file, indent=4)


def get_submission_result(
    session: Session,
    files: FileCacher,
    config: TaskConfig,
    solution: SolutionConfig,
    dataset: Dataset,
) -> SubmissionResult:
    submission = get_submission(session, files, config, solution, dataset.task)

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
