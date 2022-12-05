# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import subprocess
import os
import itertools
from typing import Optional, Dict, Any, Tuple, Callable, List

from .program import RunResultKind, Program, RunResult
from .solution import Solution
from .task_config import TaskConfig
from . import util


class Judge:
    """Abstract class for judges."""

    def __init__(self) -> None:
        pass

    def evaluate(
        self,
        solution: Solution,
        input_file: str,
        correct_output: Optional[str],
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,  # Only used for KasiopeaExternalJudge
    ) -> Tuple[float, RunResult]:
        """Runs the solution on the given input. Returns the pair (pts,
        verdict), where:
        - `pts` is the number of points received, in the interval [0.0, 1.0].
        - `verdict` contains additional information about the verdict."""
        raise NotImplementedError()


JUDGES: Dict[str, Callable[[TaskConfig], Judge]] = {
    "diff": lambda task_config: WhiteDiffJudge(),
    "judge_cms": lambda task_config: CMSExternalJudge(
        Program(task_config.task_dir, str(task_config.judge_name))
    ),
    "judge_kasiopea": lambda task_config: KasiopeaExternalJudge(
        Program(task_config.task_dir, str(task_config.judge_name))
    ),
    "ok": lambda task_config: OKJudge(),
}


def make_judge(task_config: TaskConfig) -> Judge:
    judge_type = task_config.judge_type

    if judge_type == "judge":
        judge_type += "_" + task_config.contest_type

    if judge_type not in JUDGES:
        raise RuntimeError(
            f"Úloha má neplatný typ judge: {task_config.judge_type}."
            f"Podporované typy jsou: {' '.join(JUDGES.keys())}"
        )
    return JUDGES[judge_type](task_config)


def evaluate_offline(
    judge_fn: Callable[[str], Tuple[float, RunResult]],
    solution: Solution,
    input_file: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> Tuple[float, RunResult]:
    if run_config is None:
        run_config = {}
    res, output_file = solution.run_on_file(input_file, **run_config)
    if res.kind != RunResultKind.OK:
        return 0.0, res

    assert output_file is not None, 'run_on_file returned "OK" result, but no output'
    return judge_fn(output_file)


class WhiteDiffJudge(Judge):
    """A standard judge that compares contestant's output to the correct output."""

    def __init__(self) -> None:
        super().__init__()

    def evaluate(
        self,
        solution: Solution,
        input_file: str,
        correct_output: Optional[str],
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,
    ) -> Tuple[float, RunResult]:
        if correct_output is None:
            raise RuntimeError(
                "Cannot diff solution with correct output, because the output is not given"
            )

        def white_diff(output_file: str) -> Tuple[float, RunResult]:
            assert correct_output is not None

            if util.files_are_equal(output_file, correct_output):
                return 1.0, RunResult(RunResultKind.OK)
            else:

                return 0.0, RunResult(
                    RunResultKind.OK,
                    self.create_wrong_answer_message(
                        solution, input_file, output_file, correct_output
                    ),
                )

        return evaluate_offline(white_diff, solution, input_file, run_config)

    def create_wrong_answer_message(
        self, solution, input_file, output_file, correct_output
    ):
        diff = util.diff_files(
            output_file,
            correct_output,
            "správné řešení",
            f"řešení solveru '{solution.name}'",
        )
        # Truncate diff -- we don't want this to be too long
        diff = "".join(itertools.islice(diff, 0, 25))

        return (
            f"Špatná odpověď pro {os.path.basename(input_file)}. "
            f"Diff:\n{util.quote_output(diff)}"
        )


class CMSExternalJudge(Judge):
    """Runs an external judge on contestant's output (passing input and correct
    output as arguments), returns the verdict provided by the judge.

    The API is (a subset of) the one used in CMS:
    https://cms.readthedocs.io/en/latest/Task%20types.html#tasktypes-standard-manager-output
    """

    def __init__(self, judge: Program) -> None:
        super().__init__()
        self.judge: Program = judge

    def evaluate(
        self,
        solution: Solution,
        input_file: str,
        correct_output: Optional[str],
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,
    ) -> Tuple[float, RunResult]:
        def external_judge(output_file: str) -> Tuple[float, RunResult]:
            # TODO: impose limits
            args = (
                [input_file, correct_output, output_file]
                if correct_output is not None
                else [input_file, output_file]
            )

            timeout = None if run_config is None else run_config.get("timeout")
            result = self.judge.run_raw(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Judge selhal s chybovým kódem {result.returncode}."
                    f"\n{util.quote_process_output(result)}"
                )
            pts_raw = result.stdout.decode().split("\n", 1)[0]
            try:
                pts = float(pts_raw)
            except ValueError:
                raise RuntimeError(
                    f"Judge na stdout místo počtu bodů vypsal"
                    f"\n{util.quote_process_output(result)}"
                )
            if not (0 <= pts <= 1):
                raise RuntimeError(
                    f"Judge řešení udělil {pts} bodů, což je mimo povolený rozsah [0.0, 1.0]."
                )

            msg = create_external_judge_message(result, output_file)

            return pts, RunResult(RunResultKind.OK, msg)

        return evaluate_offline(external_judge, solution, input_file, run_config)


class OKJudge(Judge):
    """A judge that checks if the output is "OK". Useful for checkers."""

    def __init__(self) -> None:
        super().__init__()

    def evaluate(
        self,
        solution: Solution,
        input_file: str,
        correct_output: Optional[str],
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,
    ) -> Tuple[float, RunResult]:
        """if correct_output is not None:
        raise RuntimeError(
            "AssertOK judge expects correct_output to be set to None"
        )"""

        def check_ok(output_file: str) -> Tuple[float, RunResult]:
            with open(output_file, "r") as f:
                out = f.read()
            if out.strip() != "OK":
                return 0.0, RunResult(RunResultKind.OK, msg=out)
            return 1.0, RunResult(RunResultKind.OK)

        return evaluate_offline(check_ok, solution, input_file, run_config)


class KasiopeaExternalJudge(Judge):
    """Runs an external judge on contestant's output (passing input and correct
    output as arguments), returns the verdict provided by the judge.

    Uses Kasiopea's API (file names passed in environment variables)
    """

    def __init__(self, judge: Program) -> None:
        super().__init__()
        self.judge: Program = judge
        self.name = self.judge.name

    def evaluate(
        self,
        solution: Solution,
        input_file: str,
        correct_output: Optional[str],
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,
    ) -> Tuple[float, RunResult]:
        def external_judge(output_file: str) -> Tuple[float, RunResult]:
            return self.evaluate_on_file(
                input_file, correct_output, output_file, run_config, judge_args
            )

        return evaluate_offline(external_judge, solution, input_file, run_config)

    def evaluate_on_file(
        self,
        input_file: str,
        correct_output_file: Optional[str],
        output_file: str,
        run_config: Optional[Dict[str, Any]] = None,
        judge_args: Optional[List[str]] = None,
    ) -> Tuple[float, RunResult]:
        if judge_args is not None:
            assert len(judge_args) == 2, (
                "Expected exactly two arguments as input: $subtask_num $seed. "
                f"Instead got {judge_args}."
            )

        timeout = None if run_config is None else run_config.get("timeout")
        with open(output_file, "r") as contestant_f:
            result = self.judge.run_raw(
                program_args=judge_args or [],
                stdin=contestant_f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                env={"TEST_INPUT": input_file, "TEST_OUTPUT": correct_output_file},
            )

        if result.returncode not in [0, 1]:
            raise RuntimeError(
                f"Judge selhal s chybovým kódem {result.returncode}.\n"
                f"{util.quote_process_output(result)}"
            )

        return float(1 - result.returncode), RunResult(
            RunResultKind.OK,
            msg=create_external_judge_message(result, output_file),
        )


def create_external_judge_message(
    subprocess_result, contestant_output_file
) -> Optional[str]:
    """
    If the answer is refused, pretty-print the judge's output along with
    what the answer was.
    """

    if subprocess_result.returncode == 1:
        msg = "Odpověď byla zamítnuta judgem. Jeho výstup:\n"
        msg += util.quote_process_output(subprocess_result)

        with open(contestant_output_file, "r") as contestant_f:
            solution_s = contestant_f.read(3000)

        msg += "\nZamítnutá odpověď:\n"
        msg += util.quote_output(solution_s)

        return msg
    else:
        return None
