import json
import os
import xml.etree.ElementTree as ET

import xmltodict
from loguru import logger

ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}


class ApparatusConverter:
    def __init__(self, apparatus_directory: str, output_directory: str):
        self.apparatus_directory = apparatus_directory.removesuffix("/")
        self.output_directory = output_directory.removesuffix("/")

    def convert(self):
        base_dir = self.apparatus_directory
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith(".xml")]
        for xml in xml_files:
            base_name = xml.removesuffix(".xml")
            export_dir = f"{self.output_directory}/{base_name}"
            os.makedirs(export_dir, exist_ok=True)
            self.process_xml(f"{base_dir}/{xml}", export_dir, base_name)

    @staticmethod
    def process_xml(xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path, encoding='UTF8') as f:
            xml = f.read()

        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        js = json.dumps(list(xpars.values())[0], indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding='UTF8') as f:
            f.write(js)

        # export all elements with xml:id to json files
        root = ET.fromstring(xml)
        identified_elements = root.findall(".//*[@xml:id]", namespaces=ns)
        for element in identified_elements:
            xml_id = element.attrib.get(f'{{{ns["xml"]}}}id')
            xml_str = ET.tostring(element, encoding='unicode')
            parsed_dict = xmltodict.parse(xml_str)
            filepath = os.path.join(output_dir, f"{xml_id}.json")
            logger.info(f"=> {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(list(parsed_dict.values())[0], f, indent=2, ensure_ascii=False)
