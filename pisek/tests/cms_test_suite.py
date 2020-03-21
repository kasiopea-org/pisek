import unittest
import os
import re
import random
from typing import Optional, Tuple, Dict, List

from . import test_case
from ..task_config import TaskConfig
from .. import util


def cms_test_suite(
    task_dir: str, solutions: Optional[List[str]] = None, timeout=util.DEFAULT_TIMEOUT,
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions_to_test` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """

    config = TaskConfig(task_dir)
    # Make sure we don't have stale files. We run this after loading `config`
    # to make sure `task_dir` is a valid task directory
    util.clear_data_dir(task_dir)

    suite = unittest.TestSuite()
    suite.addTest(test_case.ConfigIsValid(task_dir))

    # generator = OfflineGenerator(task_dir, config.generator)

    return suite
