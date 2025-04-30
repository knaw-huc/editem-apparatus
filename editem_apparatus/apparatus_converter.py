import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict

import xmltodict
from loguru import logger

from editem_apparatus.editem_apparatus_config import EditemApparatusConfig

ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}


class ApparatusConverter:
    def __init__(self, config: EditemApparatusConfig):
        self.apparatus_directory = config.data_path.removesuffix("/")
        self.output_directory = config.export_path.removesuffix("/")
        self.static_file_server_base_url = config.static_file_server_base_url.removesuffix("/")
        if not config.show_progress:
            logger.remove()
            logger.add(sys.stdout, level="WARNING")
        if config.log_file_path:
            logger.remove()
            if os.path.exists(config.log_file_path):
                os.remove(config.log_file_path)
            logger.add(config.log_file_path)

    def convert(self):
        base_dir = self.apparatus_directory
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith(".xml")]
        for xml in xml_files:
            base_name = xml.removesuffix(".xml")
            export_dir = f"{self.output_directory}/{base_name}"
            os.makedirs(export_dir, exist_ok=True)
            self.process_xml(f"{base_dir}/{xml}", export_dir, base_name)

    def process_xml(self, xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path, encoding='UTF8') as f:
            xml = f.read()

        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        element_dict = self.simplify_keys(list(xpars.values())[0])
        js = json.dumps(element_dict, indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding='UTF8') as f:
            f.write(js)

        # export all elements with xml:id to json files
        root = ET.fromstring(xml)
        identified_elements = root.findall(".//*[@xml:id]", namespaces=ns)
        for element in identified_elements:
            xml_id = element.attrib.get(f'{{{ns["xml"]}}}id')
            if xml_id is not None:
                xml_str = ET.tostring(element, encoding='unicode')
                parsed_dict = xmltodict.parse(xml_str)
                element_dict = self.simplify_keys(list(parsed_dict.values())[0])
                filepath = os.path.join(output_dir, f"{xml_id}.json")
                logger.info(f"=> {filepath}")
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(element_dict, f, indent=2, ensure_ascii=False)

    def simplify_keys(self, kvdict: dict[str, Any]) -> dict[str, Any]:
        new_dict = {}
        for key, value in kvdict.items():
            if not key.startswith("@xmlns"):
                simplified_key = key.removeprefix("@").removeprefix("#").split(":")[-1]
                if isinstance(value, Dict):
                    new_dict[simplified_key] = self.simplify_keys(value)
                elif isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, Dict):
                            new_list.append(self.simplify_keys(item))
                        else:
                            new_list.append(item)
                    new_dict[simplified_key] = new_list
                else:
                    new_dict[simplified_key] = value
                if simplified_key == "ref":
                    new_dict[simplified_key] = f"{self.static_file_server_base_url}/{value.replace('.xml#', '/')}.json"
        return new_dict
