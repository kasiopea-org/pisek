import subprocess
import os
import tempfile
import json
from pisek.task_config import TaskConfig

def download_data(args):
    config = TaskConfig(".")
    with tempfile.NamedTemporaryFile(suffix=".json", mode="r") as tmpf:
        cmd = [ "cmsExportEvaluation", "-c", str(args.contest_id), "-u", args.username, "-t", config.task_name, tmpf.name ]
        print(cmd)
        subprocess.run(cmd).check_returncode()
        data = json.load(tmpf)

    by_filename = {}
    for i in data:
        comment = i["comment"].split()
        if len(comment) != 2: continue
        filename = comment[0]
        by_filename[filename] = i

    output = {}
    for filename, val in by_filename.items():
        def format_evaluation(evaluation):
            return {
                "time": evaluation["execution_time"],
                "wall_clock_time": evaluation["execution_wall_clock_time"],
                "memory": evaluation["execution_memory"],
                "test": evaluation["codename"],
                "points": evaluation["outcome"],
                "status": "\n".join(evaluation["text"]),
            }

        output[filename] = {
                "test_time": val["submit_time"],
                "results": [ format_evaluation(i) for i in val["evaluations"]],
        }
        return output

def dump_data(args):
    data = download_data(args)
    with open(args.output, "w") as f:
        json.dump(data, f)

def analyze(args):
    data = download_data(args)

