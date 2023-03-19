import os
import sys
from . import check, info
from pisek.task_config import TaskConfig
import pisek.util as util
import zipfile

TESTS_ZIP = "tests.zip"
SAMPLES_ZIP = "sample_tests.zip"

def zip_testdata(path, out, sample_tests=False):
    config = TaskConfig(".")
    try:
        os.remove(out)
    except OSError:
        pass # does not exist

    zipf = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(path):
        for file in files:
            if len(file) > 3 and file[-3:] == ".in":
                name = file[:-3]
                if sample_tests:
                    out_file = file[:-3] + ".out"
                else:
                    out_file = util.get_output_name(file, config.solutions[0])
                zipf.write(os.path.join(root, file),
                           "input." + name)
                zipf.write(os.path.join(root, out_file),
                            "output." + name)

    zipf.close()

def samples(args):
    config = TaskConfig(".")
    print(f"Vytvářím {SAMPLES_ZIP}.")
    zip_testdata(config.samples_subdir, SAMPLES_ZIP, sample_tests=True)

def pack(args):
    config = TaskConfig(".")

    info.task_info()

    print(f"Vytvářím {TESTS_ZIP}…", end=" ")
    sys.stdout.flush()
    zip_testdata(config.data_subdir, TESTS_ZIP)
    print(f"hotovo.")
    samples(args)
