from typing import Optional, Any
from cms.db.task import Dataset
from cms.db.submission import SubmissionResult, Evaluation
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from colorama import Fore
import json

from pisek.cms.submission import get_submission
from pisek.jobs.parts.testing_log import TESTING_LOG
from pisek.task_config import SolutionConfig, TaskConfig, SubtaskConfig


def create_testing_log(session: Session, config: TaskConfig, dataset: Dataset):
    files = FileCacher()

    payload: dict[str, Any] = {"source": "cms"}

    for name, solution in config.solutions.subenvs():
        results: list[Any] = []
        payload[name] = {"results": results}

        try:
            result = get_submission_result(session, files, config, solution, dataset)
        except SubmissionResultError as e:
            print(f"{Fore.YELLOW}Skipping {name}: {e}{Fore.RESET}")
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


def check_results(session: Session, config: TaskConfig, dataset: Dataset):
    files = FileCacher()

    solution: SolutionConfig
    for name, solution in config.solutions.subenvs():
        try:
            result = get_submission_result(session, files, config, solution, dataset)

            if not result.scored():
                raise SubmissionResultError("This submission has not been scored yet")
        except SubmissionResultError as e:
            print(f"{Fore.YELLOW}Skipping {name}: {e}{Fore.RESET}")
            continue

        score = result.score

        score_missed_target = None

        if solution.points is not None and score != solution.points:
            score_missed_target = f"{solution.points}"
        elif solution.points_above is not None and score < solution.points_above:
            score_missed_target = f"above {solution.points_above}"
        elif solution.points_below is not None and score > solution.points_below:
            score_missed_target = f"below {solution.points_below}"

        if score_missed_target is not None:
            print(
                f"{Fore.RED}{name}: {score} points (should be {score_missed_target}){Fore.RESET}"
            )
        else:
            print(f"{name}: {score} points")

        subtasks: list[tuple[str, SubtaskConfig]] = list(config.subtasks.subenvs())
        fractions = get_subtask_score_fractions(result.score_details)

        if fractions is None or len(fractions) != len(subtasks):
            print(
                f"  {Fore.YELLOW}The task seems to use an unsupported score type, skipping checking subtasks{Fore.RESET}"
            )
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
                target_name = "wrong"
                correct = fraction == 0.0

            if correct:
                print(f"  {name}: {fraction}")
            else:
                print(
                    f"  {Fore.RED}{name}: {fraction} (should be {target_name}){Fore.RESET}"
                )


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
