import subprocess
import os, sys
import tempfile
import json
from pisek.config.task_config import TaskConfig


def download_data(args):
    config = TaskConfig(".")
    with tempfile.NamedTemporaryFile(suffix=".json", mode="r") as tmpf:
        cmd = [
            "cmsExportEvaluation",
            "-c",
            str(args.contest_id),
            "-u",
            args.username,
            "-t",
            config.task_name,
            tmpf.name,
        ]
        print(cmd)
        subprocess.run(cmd).check_returncode()
        data = json.load(tmpf)

    print(file=sys.stderr)

    by_name = {}
    for i in data:
        comment = i["comment"].split()
        if len(comment) != 2:
            continue
        filename = comment[0]
        if (
            filename not in by_name
            or i["submit_time"] > by_name[filename]["submit_time"]
        ):
            by_name[filename] = i

    output = {}
    for solution in config.solutions:
        if solution not in by_name:
            print(f"Řešení {solution} nenalezeno", file=sys.stderr)
            continue

        val = by_name[solution]

        if val["status"] != "scored":
            print(
                f"Řešení {solution} ještě není vyhodnoceno (stav {val['status']})",
                file=sys.stderr,
            )
            continue

        def format_evaluation(evaluation):
            points = float(evaluation["outcome"])
            if evaluation["text"] == ["Output is correct"]:
                result = "ok"
            elif evaluation["text"] == ["Output is partially correct"]:
                result = "ok"
            elif evaluation["text"] == ["Execution timed out"]:
                result = "timeout"
            elif evaluation["text"] == ["Output isn't correct"]:
                result = "wrong_answer"
            else:
                result = "error"
                print(
                    solution,
                    evaluation["codename"],
                    evaluation["outcome"],
                    evaluation["text"],
                )
            return {
                "time": evaluation["execution_time"],
                "wall_clock_time": evaluation["execution_wall_clock_time"],
                "memory": evaluation["execution_memory"],
                "test": evaluation["codename"],
                "points": points,
                "status": "\n".join(evaluation["text"]),
                "result": result,
            }

        output[solution] = {
            "test_time": val["submit_time"],
            "results": [format_evaluation(i) for i in val["evaluations"]],
        }

    test_times = [i["test_time"] for i in output.values()]
    print(file=sys.stderr)
    if len(output) == 0:
        print("Žádná data", file=sys.stderr)
    else:
        print(
            f"Čas submitů je mezi\n    {min(test_times)}\na\n    {max(test_times)}",
            file=sys.stderr,
        )

    return output


def dump_data(args):
    data = download_data(args)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=4)


def analyze(args):
    data = download_data(args)
