import unittest

from util import TestFixtureVariant


class TestMax(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/max/"


if __name__ == "__main__":
    unittest.main(verbosity=2)
