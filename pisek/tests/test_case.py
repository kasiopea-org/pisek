import unittest


class TestCase(unittest.TestCase):
    def __init__(self, task_dir):
        super().__init__()
        self.task_dir = task_dir


class SolutionTestCase(TestCase):
    def __init__(self, task_dir, solution_name):
        super().__init__(task_dir)
        self.task_dir = task_dir
        self.solution_name = solution_name
