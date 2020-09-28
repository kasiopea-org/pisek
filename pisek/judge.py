import subprocess
from typing import Optional, Dict, Any, Tuple, Callable, cast
from .program import RunResult, Program
from .solution import Solution
from .task_config import TaskConfig
from . import util


class Verdict:
    def __init__(self, run_result: RunResult, msg: Optional[str] = None) -> None:
        self.result: RunResult = run_result
        self.msg: Optional[str] = msg

    def __repr__(self) -> str:
        return f"Verdict(result={self.result}, msg={self.msg})"


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
    ) -> Tuple[float, Verdict]:
        """Runs the solution on the given input. Returns the pair (pts,
        verdict), where:
        - `pts` is the number of points received, in the interval [0.0, 1.0].
        - `verdict` contains additional information about the verdict."""
        raise NotImplementedError()


JUDGES: Dict[str, Callable[[str, TaskConfig], Judge]] = {
    "diff": lambda task_dir, task_config: WhiteDiffJudge(),
    "judge_cms": lambda task_dir, task_config: CMSExternalJudge(
        Program(task_dir, str(task_config.judge_name))
    ),
    "judge_kasiopea": lambda task_dir, task_config: KasiopeaExternalJudge(
        Program(task_dir, str(task_config.judge_name))
    ),
    "ok": lambda task_dir, task_config: OKJudge(),
}


def make_judge(task_dir: str, task_config: TaskConfig) -> Judge:
    judge_type = task_config.judge_type

    if judge_type == "judge":
        judge_type += "_" + task_config.contest_type

    if judge_type not in JUDGES:
        raise RuntimeError(
            f"Úloha má neplatný typ judge: {task_config.judge_type}."
            f"Podporované typy jsou: {' '.join(JUDGES.keys())}"
        )
    return JUDGES[judge_type](task_dir, task_config)


def evaluate_offline(
    judge_fn: Callable[[str], Tuple[float, Verdict]],
    solution: Solution,
    input_file: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> Tuple[float, Verdict]:
    if run_config is None:
        run_config = {}
    res, output_file = solution.run_on_file(input_file, **run_config)
    if res != RunResult.OK:
        return 0.0, Verdict(res)

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
    ) -> Tuple[float, Verdict]:
        if correct_output is None:
            raise RuntimeError(
                "Cannot diff solution with correct output, because the output is not given"
            )

        def white_diff(output_file: str) -> Tuple[float, Verdict]:
            assert correct_output is not None

            if util.files_are_equal(output_file, correct_output):
                return 1.0, Verdict(RunResult.OK)
            else:
                return 0.0, Verdict(RunResult.OK)

        return evaluate_offline(white_diff, solution, input_file, run_config)


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
    ) -> Tuple[float, Verdict]:
        def external_judge(output_file: str) -> Tuple[float, Verdict]:
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
                    f"Judge selhal s chybovým kódem {result.returncode}. stdout: {result.stdout}, stderr: {result.stderr}"
                )
            pts_raw = result.stdout.decode().split("\n", 1)[0]
            try:
                pts = float(pts_raw)
            except:
                raise RuntimeError(f"Judge místo počtu bodů vypsal {result.stdout}")
            if not (0 <= pts <= 1):
                raise RuntimeError(
                    f"Judge řešení udělil {pts} bodů, což je mimo povolený rozsah [0.0, 1.0]."
                )
            msg = result.stderr.decode().split("\n")[0]

            return pts, Verdict(RunResult.OK, msg)

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
    ) -> Tuple[float, Verdict]:
        """if correct_output is not None:
        raise RuntimeError(
            "AssertOK judge expects correct_output to be set to None"
        )"""

        def check_ok(output_file: str) -> Tuple[float, Verdict]:
            with open(output_file, "r") as f:
                out = f.read()
            if out.strip() != "OK":
                return 0.0, Verdict(RunResult.OK, msg=out)
            return 1.0, Verdict(RunResult.OK)

        return evaluate_offline(check_ok, solution, input_file, run_config)


class KasiopeaExternalJudge(Judge):
    """Runs an external judge on contestant's output (passing input and correct
    output as arguments), returns the verdict provided by the judge.

    Uses Kasiopea's API (file names passed in environment variables)
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
    ) -> Tuple[float, Verdict]:
        def external_judge(output_file: str) -> Tuple[float, Verdict]:

            # TODO: impose limits
            args = (
                [input_file, correct_output, output_file]
                if correct_output is not None
                else [input_file, output_file]
            )

            timeout = None if run_config is None else run_config.get("timeout")
            with open(output_file, "r") as contestant_f:
                result = self.judge.run_raw(
                    args,
                    stdin=contestant_f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env={"TEST_INPUT": input_file, "TEST_OUTPUT": correct_output},
                )

            if result.returncode not in [0, 1]:
                raise RuntimeError(
                    f"Judge selhal s chybovým kódem {result.returncode}. stdout: {result.stdout}, stderr: {result.stderr}"
                )

            return float(1 - result.returncode), Verdict(
                RunResult.OK,
                msg=f"stdout: {result.stdout}, stderr: {result.stderr}"
                if result.returncode == 1
                else None,
            )

        return evaluate_offline(external_judge, solution, input_file, run_config)
