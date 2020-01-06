import unittest
from ..solution import Solution


class TestCase(unittest.TestCase):
    def __init__(self, task_dir):
        super().__init__()
        self.task_dir = task_dir


class SolutionTestCase(TestCase):
    def __init__(self, task_dir, solution_name):
        super().__init__(task_dir)
        self.task_dir = task_dir
        self.solution = Solution(task_dir, solution_name)


class GeneratorTestCase(TestCase):
    def __init__(self, task_dir, generator):
        super().__init__(task_dir)
        self.task_dir = task_dir
        self.generator = generator
