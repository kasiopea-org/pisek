from typing import Optional

from pisek.env.task_config import TaskConfig, FailMode
from pisek.jobs.parts.solution_result import Verdict, SUBTASK_SPEC, verdict_always


def evaluate_verdicts(
    config: TaskConfig, verdicts: list[Verdict], expected: str
) -> tuple[bool, bool, Optional[int]]:
    mode_quantifier = all if config.fail_mode == FailMode.all else any

    result = True
    definitive = True
    breaker = None
    quantifiers = [all, mode_quantifier]
    for i, quant in enumerate(quantifiers):
        oks = list(map(SUBTASK_SPEC[expected][i], verdicts))
        ok = quant(oks)

        result &= ok
        definitive &= (
            (quant == any and ok)
            or (quant == all and not ok)
            or (SUBTASK_SPEC[expected][i] == verdict_always)
        )
        if quant == all and ok == False:
            breaker = oks.index(False)
            break

    return result, definitive, breaker
