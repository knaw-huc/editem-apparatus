import unittest

from editem_apparatus.apparatus_converter import ApparatusConverter


class ApparatusTestCase(unittest.TestCase):
    def test_converter(self):
        ac = ApparatusConverter("data/israels-apparatus/", "out/israels")
        self.assertIsNotNone(ac)


if __name__ == '__main__':
    unittest.main()
