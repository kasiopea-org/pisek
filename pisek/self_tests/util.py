import io
import os
import shutil
import tempfile
import unittest
from ..tests.util import get_test_suite


class TestFixtureVariant(unittest.TestCase):

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

    def expecting_success(self):
        return True

    def modify_task(self):
        # Code which modifies the task before running the tests should go here.
        # For example, if we want to check that the presence of `sample.in` is
        # correctly checked for, we would remove the file here.
        pass

    def runTest(self):
        if not self.fixture_path():
            return

        self.modify_task()
        # We lower the timeout to make the self-tests run faster. The solutions
        # run instantly, with the exception of `solve_slow_4b`, which takes 10 seconds
        # and we want to consider it a timeout
        suite = get_test_suite(self.task_dir, timeout=1)

        # with open(os.devnull, "w") as devnull:
        output = io.StringIO()
        runner = unittest.TextTestRunner(stream=output, failfast=True)

        result = runner.run(suite)

        out = output.getvalue()
        out = "\n".join([f"> {x}" for x in out.split("\n")])

        self.assertEqual(
            result.wasSuccessful(),
            self.expecting_success(),
            "Neočekávaný výsledek testu: test {}měl projít, ale {}prošel.".format(
                "" if self.expecting_success() else "ne",
                "" if result.wasSuccessful() else "ne",
            )
            + " Výstup testu:\n{}".format(out),
        )

    def tearDown(self):
        if not self.fixture_path():
            return

        shutil.rmtree(self.task_dir)
