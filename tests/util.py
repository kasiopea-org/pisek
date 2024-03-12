import configparser
import glob
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from pisek.env import config_hierarchy
from pisek.__main__ import test_task_path
from pisek.utils.util import quote_output, clean_task_dir


class TestFixture(unittest.TestCase):
    def fixture_path(self):
        return None

    def setUp(self):
        if not self.fixture_path():
            return

        self.task_dir_orig = os.path.abspath(
            os.path.join(os.path.dirname(__file__), self.fixture_path())
        )
        self.task_dir = tempfile.mkdtemp()

        # shutil.copytree() requires that the destination directory does not exist,
        os.rmdir(self.task_dir)
        shutil.copytree(self.task_dir_orig, self.task_dir)
        # print(os.listdir(self.task_dir))
        # print(os.listdir(self.task_dir + "/src"))

        if not clean_task_dir(self.task_dir):
            exit(1)

        self.cwd_orig = os.getcwd()
        os.chdir(self.task_dir)

    def runTest(self):
        # Implement this!
        pass

    def tearDown(self):
        if not self.fixture_path():
            return

        os.chdir(self.cwd_orig)

        assert self.task_dir.startswith("/tmp") or self.task_dir.startswith("/var")
        shutil.rmtree(self.task_dir)

    def log_files(self):
        """Log all files for checking whether new ones have been created."""
        self.original_files = os.listdir(self.task_dir)

    def created_files(self):
        """Additional files that are expected to be created."""
        return []

    def check_files(self):
        """
        Check whether there are no new unexpected files.
        Ignored:
            .pisek_cache data/* build/*
        """
        directories = ["build", "data"]
        files = [".pisek_cache"] + self.created_files()

        all_paths = set(self.original_files + directories + files)

        for path in os.listdir(self.task_dir):
            self.assertIn(
                path,
                all_paths,
                f"Pisek generated new file {path}.",
            )


class TestFixtureVariant(TestFixture):
    def expecting_success(self):
        return True

    def catch_exceptions(self):
        return False

    def modify_task(self):
        """
        Code which modifies the task before running the tests should go here.
        For example, if we want to check that the presence of `sample.in` is
        correctly checked for, we would remove the file here.
        """
        pass

    def runTest(self):
        if not self.fixture_path():
            return

        self.modify_task()
        self.log_files()

        # We lower the timeout to make the self-tests run faster. The solutions
        # run instantly, with the exception of `solve_slow_4b`, which takes 10 seconds
        # and we want to consider it a timeout
        @mock.patch("sys.stdout", new_callable=io.StringIO)
        @mock.patch("sys.stderr", new_callable=io.StringIO)
        def run(*args):
            return test_task_path(
                self.task_dir,
                inputs=1,
                strict=False,
                full=False,
                timeout=1,
                plain=False,
            )

        runner = unittest.TextTestRunner(failfast=True)

        self.assertEqual(run(), not self.expecting_success())

        self.check_end_state()
        self.check_files()

    def check_end_state(self):
        # Here we can verify whether some conditions hold when Pisek finishes,
        # making sure that the end state is reasonable
        pass


def overwrite_file(task_dir, old_file, new_file, new_file_name=None):
    os.remove(os.path.join(task_dir, old_file))
    shutil.copy(
        os.path.join(task_dir, new_file),
        os.path.join(task_dir, new_file_name or old_file),
    )


def modify_config(task_dir: str, modification_fn):
    """
    `modification_fn` accepts the config (in "raw" ConfigParser format) and may
    modify it. The modified version is then saved.

    For example, if we want to change the evaluation method ("out_check")
    from `diff` to `judge`, we would do that in `modification_fn` via:
        config["tests"]["out_check"] = "judge"
        config["tests"]["out_judge"] = "judge"  # To specify the judge program file
    """

    config = configparser.ConfigParser()
    config_path = os.path.join(task_dir, config_hierarchy.CONFIG_FILENAME)
    read_files = config.read(config_path)
    if not read_files:
        raise FileNotFoundError(f"Chybí konfigurační soubor {config_path}.")

    modification_fn(config)

    with open(config_path, "w") as f:
        config.write(f)
