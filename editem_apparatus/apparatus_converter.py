import json
import os
import xml.etree.ElementTree as ET

import xmltodict
from loguru import logger


class ApparatusConverter:
    def __init__(self, apparatus_directory: str, output_directory: str):
        base_dir = apparatus_directory.removesuffix("/")
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith(".xml")]
        for xml in xml_files:
            base_name = xml.removesuffix(".xml")
            export_dir = f"{output_directory}/{base_name}"
            os.makedirs(export_dir, exist_ok=True)
            self.process_xml(f"{base_dir}/{xml}", export_dir, base_name)

    @staticmethod
    def process_xml(xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path, encoding='UTF8') as f:
            xml = f.read()

        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        js = json.dumps(xpars, indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding='UTF8') as f:
            f.write(js)

        # export all elements with xml:id to json files
        root = ET.fromstring(xml)
        ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}
        identified_elements = root.findall(".//*[@xml:id]", namespaces=ns)
        for element in identified_elements:
            xml_id = element.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
            xml_str = ET.tostring(element, encoding='unicode')
            parsed_dict = xmltodict.parse(xml_str)
            filepath = os.path.join(output_dir, f"{xml_id}.json")
            logger.info(f"=> {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(parsed_dict, f, indent=2, ensure_ascii=False)
