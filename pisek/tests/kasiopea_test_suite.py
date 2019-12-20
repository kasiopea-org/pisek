from . import test_case
import unittest
import os


class ConfigExists(test_case.TestCase):
    def runTest(self):
        self.assertTrue(
            os.path.isfile(os.path.join(self.task_dir, "config")),
            "Ve složce úlohy musí existovat soubor 'config'",
        )


def kasiopea_test_suite(task_dir):
    suite = unittest.TestSuite()
    suite.addTest(ConfigExists(task_dir))

    return suite
