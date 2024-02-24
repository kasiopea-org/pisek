from pisek.config.task_config import TaskConfig


def subtask_formula(subtask):
    pts = subtask.score
    regex = subtask.globs_regex()
    return f'[{pts}, "{regex}"]'


def scoring_formula(config: TaskConfig):
    fls = []
    fls.append(r'[0, "^sample"]')
    for i, subtask in sorted(config.subtasks.items()):
        fls.append(subtask_formula(subtask))
    return "[\n " + ",\n ".join(f for f in fls) + "\n]"


def time_limits(config: TaskConfig):
    model = config.limits.solve.time_limit
    other = config.limits.sec_solve.time_limit
    if model == other:
        return model, None
    else:
        return model, other


def task_info(args=None):
    config = TaskConfig(".")
    print("\n\nFormule:")
    formula = scoring_formula(config)
    print(formula)

    time_limit, alt_time_limit = time_limits(config)
    print("\n\nČas:", end=" ")
    if alt_time_limit is None:
        print(time_limit)
    else:
        print(time_limit, f"   (vzorové, {alt_time_limit} ostatní)")

    def dash(text):
        return text if text is not None else "—"

    print(f"Stub: {dash(config.stub)}")
    print(f"Judge: {dash(config.judge_name)}")
