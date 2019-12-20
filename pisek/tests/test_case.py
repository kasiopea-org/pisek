import unittest


class TestCase(unittest.TestCase):
    def __init__(self, task_dir):
        super().__init__()
        self.task_dir = task_dir
