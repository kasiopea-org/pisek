from typing import Optional, Dict, Any, Tuple
from .program import RunResult
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
        if run_config is None:
            run_config = {}
        res, output = solution.run_on_file(input_file, **run_config)
        if res != RunResult.OK:
            return 0.0, Verdict(res)

        assert output is not None, 'run_on_file returned "OK" result, but no output'
        if util.files_are_equal(output, correct_output):
            return 1.0, Verdict(res)
        else:
            return 0.0, Verdict(RunResult.WRONG_ANSWER)
