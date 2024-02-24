import subprocess
import glob
import os
import tempfile
import pisek.utils.util as util
from pisek.config.task_config import TaskConfig
from . import check


def comment_line(text, lang):
    comment_starts = {
        "cpp": "//",
        "c": "//",
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

    additional = comment_line(f"NAME: {solution}", lang)
    additional += comment_line(f"ORIGINAL FILENAME: {fn}", lang)
    if not_in_config:
        additional += comment_line(f"(not in config, pts may be off)", lang)
    expected_score = util.get_expected_score(solution, config)
    additional += comment_line(f"EXCEPTED SCORE: {expected_score}", lang)
    contents = additional + contents

    comment = f"{solution} ({expected_score}b)"

    basename = os.path.basename(fn)
    task_name = config.task_name
    print(task_name)

    with tempfile.NamedTemporaryFile(suffix="." + lang, mode="w") as tmpf:
        tmpf.write(contents)
        tmpf.flush()
        cmd = [
            "cmsAddSubmission",
            "-c",
            str(args.contest_id),
            "-f",
            f"{task_name}.%l:{tmpf.name}",
            "-C",
            comment,
            args.username,
            task_name,
        ]
        print(cmd)
        subprocess.run(cmd).check_returncode()


def submit_all(args):
    config = TaskConfig(".")
    solutions = config.solutions
    for solution in solutions:
        submit_solution(solution, args)
