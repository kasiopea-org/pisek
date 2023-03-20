from pisek.task_config import TaskConfig

def glob_to_regex(glob):
    """Does not return an 'anchored' regex, i.e., a* -> a.*, not ^a.*$"""
    pattern = glob.replace(".in", "").replace(".", "\\.").replace("*", ".*")
    pattern = pattern[:-2] if pattern.endswith(".*") else pattern + "$"
    if not pattern:
        pattern = ".*" # probably ok either way, but just to be sure
    return pattern

def subtask_formula(subtask):
    pts = subtask.score
    regex = "^(" + "|".join(glob_to_regex(glob) for glob in subtask.in_globs) + ")"
    return f'[{pts}, "{regex}"]'

def scoring_formula(config: TaskConfig):
    fls = []
    fls.append(r'[0, "^sample"]')
    for i, subtask in sorted(config.subtasks.items()):
        fls.append(subtask_formula(subtask))
    return "[\n " + ",\n ".join(f for f in fls) + "\n]"

def time_limits(config: TaskConfig):
    model = config.timeout_model_solution
    other = config.timeout_other_solutions
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
    print(f"Manager: {dash(config.solution_manager)}")
    print(f"Judge: {dash(config.judge_name)}")