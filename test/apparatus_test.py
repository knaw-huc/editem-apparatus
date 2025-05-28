import unittest

from icecream import ic

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

    def test_labels_for_person_with_abb_pers_name(self):
        cf = EditemApparatusConfig(
            project_name="test",
            data_path="data/test-apparatus/",
            export_path="out/test"
        )
        ac = ApparatusConverter(cf)
        person = {
            "id": "pers026",
            "sex": "1",
            "persName": [
                {
                    "full": "yes",
                    "forename": "Cornelis Gabriel",
                    "surname": "Kleykamp"
                },
                {
                    "full": "abb",
                    "forename": "Kees",
                    "surname": "Kleykamp"
                }
            ],
            "birth": {
                "when": "1892"
            },
            "death": {
                "when": "1964"
            }
        }
        dict = {person["id"]: person}
        new_dict = ac._addLabelsForPersons(dict)
        self.assertEqual("Kees Kleykamp", new_dict['pers026']["displayLabel"])
        self.assertEqual("Kleykamp, Kees", new_dict['pers026']["sortLabel"])


if __name__ == '__main__':
    unittest.main()
