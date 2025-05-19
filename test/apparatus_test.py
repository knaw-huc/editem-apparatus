import unittest

from editem_apparatus.apparatus_converter import ApparatusConverter
from editem_apparatus.editem_apparatus_config import EditemApparatusConfig


class ApparatusTestCase(unittest.TestCase):
    def test_converter(self):
        cf = EditemApparatusConfig(
            project_name="test",
            data_path="data/test-apparatus/",
            export_path="out/test"
        )
        ac = ApparatusConverter(cf)
        self.assertIsNotNone(ac)


if __name__ == '__main__':
    unittest.main()
