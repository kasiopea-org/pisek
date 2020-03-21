import subprocess
from typing import Optional, Dict, Any, Tuple, Callable, cast
from .program import RunResult, Program
from .solution import Solution
from . import util


class Verdict:
    def __init__(self, run_result, msg=None) -> None:
        self.result: RunResult = run_result
        self.msg: str = msg

    def __repr__(self):
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
        - `verdict` contains additional information about the verdict. """
        raise NotImplementedError()


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

        def white_diff(output_file: str):
            correct_output_but_named_differently_because_of_damn_mypy_not_being_able_to_recognize_it_as_definitely_not_being_null = cast(
                str, correct_output
            )
            if util.files_are_equal(
                output_file,
                correct_output_but_named_differently_because_of_damn_mypy_not_being_able_to_recognize_it_as_definitely_not_being_null,
            ):
                return 1.0, Verdict(RunResult.OK)
            else:
                return 0.0, Verdict(RunResult.WRONG_ANSWER)

        return evaluate_offline(white_diff, solution, input_file, run_config)


class ExternalJudge(Judge):
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
        def external_judge(output_file: str):
            # TODO: impose limits
            args = (
                [input_file, correct_output, output_file]
                if correct_output is not None
                else [input_file, output_file]
            )
            self.judge.run_raw(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            return 1.0, Verdict(RunResult.OK)

        return evaluate_offline(external_judge, solution, input_file, run_config)
