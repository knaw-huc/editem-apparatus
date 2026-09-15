import sys
import unittest
import xml.etree.ElementTree as ET

from loguru import logger

from editem_apparatus.io_tools import IOHandler


class MyTestCase(unittest.TestCase):

    def test_pers_name(self):
        ns = {'xml': 'http://www.w3.org/XML/1998/namespace', 'tei': 'http://www.tei-c.org/ns/1.0'}
        logger.error(ns)
        xml = IOHandler().read_text("/tmp/bio.xml")
        root = ET.fromstring(xml)
        self.assertIsNotNone(root)
        pers_names = root.findall('.//tei:persName[@full="yes"]', namespaces=ns)
        for p in pers_names:
            print(" ".join(p.itertext()))
        self.assertIsNotNone(pers_names)
        self.assertFalse(True)


if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    unittest.main()
