import glob
import os
import pisek.util as util
from pisek.task_config import TaskConfig
from . import ssh, check

def comment_line(text, lang):
    comment_starts = {
        "cpp": "//",
        "c" : "//",
        "java": "//",
        "py": "#",
    }

    start = comment_starts.get(lang, "#")
    return f"{start} {text}\n"


def submit_solution(solution, args, not_in_config=False):
    config = TaskConfig(".")
    fn = util.resolve_extension(config.task_dir, solution)
    lang = os.path.splitext(fn)[-1][1:]
    with open(fn) as f:
        contents = f.read()

    additional = comment_line(f"ORIGINAL FILENAME: {fn}", lang)
    if not_in_config:
        additional += comment_line(f"(not in config, pts may be off)", lang)
    additional += comment_line(f"EXCEPTED SCORE: {util.get_expected_score(solution, config)}", lang)
    contents = additional + contents

    basename = os.path.basename(fn)
    task_name = config.task_name
    print(task_name)

    print(ssh.copy_tmp_file_and(args, f"cmsAddSubmission -c {args.contest_id} -f {task_name}.%l:{basename} {args.username} {task_name}", contents=contents, basename=basename))

def submit_all(args):
    config = TaskConfig(".")
    solutions = config.solutions
    for solution in solutions:
        submit_solution(solution, args)
