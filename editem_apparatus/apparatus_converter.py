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
            self._process_xml(f"{base_dir}/{xml}", export_dir, base_name)

    def _process_xml(self, xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path) as f:
            xml = f.read()

        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        element_dict = self._simplify_keys(list(xpars.values())[0])
        js = json.dumps(element_dict, indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w') as f:
            f.write(js)

        # export all elements with xml:id to json files
        root = ET.fromstring(xml)
        identified_elements = root.findall(".//*[@xml:id]", namespaces=ns)
        entity_dict = {}
        for element in identified_elements:
            xml_id = element.attrib.get(f'{{{ns["xml"]}}}id')
            if xml_id is not None:
                xml_str = ET.tostring(element, encoding='UTF-8')
                parsed_dict = xmltodict.parse(xml_str)
                element_dict = self._simplify_keys(list(parsed_dict.values())[0])
                # filepath = os.path.join(output_dir, f"{xml_id}.json")
                # logger.info(f"=> {filepath}")
                # with open(filepath, 'w') as f:
                #     json.dump(element_dict, fp=f, indent=2, ensure_ascii=False)
                entity_dict[f"{base_name}/{xml_id}"] = element_dict

        normalized_entity_dict = self._normalize_list_values(entity_dict)
        path = f"{output_dir}/{base_name}-element-dict.json"
        logger.info(f"=> {path}")
        with open(path, 'w') as f:
            json.dump(normalized_entity_dict, fp=f, indent=2, ensure_ascii=False)

    def _simplify_keys(self, kv_dict: dict[str, Any]) -> dict[str, Any]:
        new_dict = {}
        for key, value in kv_dict.items():
            if not key.startswith("@xmlns"):
                simplified_key = key.removeprefix("@").removeprefix("#").split(":")[-1]
                if isinstance(value, Dict):
                    new_dict[simplified_key] = self._simplify_keys(value)
                elif isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, Dict):
                            new_list.append(self._simplify_keys(item))
                        else:
                            new_list.append(item)
                    new_dict[simplified_key] = new_list
                else:
                    new_dict[simplified_key] = value
        return new_dict

    def _normalize_list_values(self, in_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        def _set_value_as_list(d, path):
            keys = path.split('.')
            current = d
            for k in keys[:-1]:
                if isinstance(current, dict):
                    current = current.get(k, {})
                else:
                    return  # path does not exist or is malformed
            last_key = keys[-1]
            if isinstance(current, dict) and last_key in current:
                value = current[last_key]
                if not isinstance(value, list):
                    current[last_key] = [value]

        list_value_keys = self._find_keys_with_list_values(in_dict)
        logger.info(f"fields with list values: {list_value_keys}")
        for d in in_dict.values():
            for key in list_value_keys:
                _set_value_as_list(d, key)
        return in_dict

    @staticmethod
    def _find_keys_with_list_values(in_dict: dict[str, Any]) -> set[str]:
        def _recurse(d, path=''):
            keys_with_lists = set()
            if isinstance(d, dict):
                for key, value in d.items():
                    full_key = f"{path}.{key}" if path else key
                    if isinstance(value, list):
                        keys_with_lists.add(full_key)
                    elif isinstance(value, dict):
                        keys_with_lists.update(_recurse(value, full_key))
            return keys_with_lists

        result = set()
        for d in in_dict.values():
            result.update(_recurse(d))
        return result
