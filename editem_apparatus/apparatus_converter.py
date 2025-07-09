import json
import os
import sys
import traceback
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict

import xmltodict
from loguru import logger

from editem_apparatus.editem_apparatus_config import EditemApparatusConfig

ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}


@dataclass
class NormalizedPersName:
    forename: str
    name_link: str
    surname: str
    add_name: str


class ApparatusConverter:
    def __init__(self, config: EditemApparatusConfig):
        self.apparatus_directory = config.data_path.removesuffix("/")
        self.output_directory = config.export_path.removesuffix("/")
        self.graphic_url_mapper = config.graphic_url_mapper
        self.errors = []
        if not config.show_progress:
            logger.remove()
            logger.add(sys.stdout, level="WARNING")
        if config.log_file_path:
            logger.remove()
            if os.path.exists(config.log_file_path):
                os.remove(config.log_file_path)
            logger.add(config.log_file_path)

    def convert(self) -> list[str]:
        base_dir = self.apparatus_directory
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith(".xml")]
        for xml in xml_files:
            try:
                base_name = xml.removesuffix(".xml")
                export_dir = f"{self.output_directory}"
                os.makedirs(export_dir, exist_ok=True)
                self._process_xml(f"{base_dir}/{xml}", export_dir, base_name)
            except Exception as e:
                message = f"there was an error converting {xml}: {e}"
                self.errors.append(message)
                print(traceback.format_exc(), file=sys.stderr)
        self._add_labels_to_refs()
        return self.errors

    def _process_xml(self, xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path, encoding="utf8") as f:
            xml = f.read()

        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        element_dict = self._simplify_keys(list(xpars.values())[0])
        js = json.dumps(element_dict, indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding="utf8") as f:
            f.write(js)

        # export all elements with xml:id to json files
        root = ET.fromstring(xml)
        text_node = root.find(".//{http://www.tei-c.org/ns/1.0}text")
        identified_elements = text_node.findall(".//*[@xml:id]", namespaces=ns)
        entity_dict: dict[str, Any] = {}
        entity_id_list: list[str] = []
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
                entity_id_list.append(xml_id)

        converted_entity_dict = self._convert_all_object_lists_with_lang_fields_to_dict(entity_dict)

        normalized_entity_dict = self._normalize_list_values(converted_entity_dict)

        labelled_entity_dict = self._add_labels_for_persons(normalized_entity_dict)

        extended_graph_url_entity_dict = self._extend_graphic_url(labelled_entity_dict)

        self._export_as_json(extended_graph_url_entity_dict, f"{output_dir}/{base_name}-entity-dict.json")

        self._export_as_json([extended_graph_url_entity_dict[f"{base_name}/{k}"] for k in entity_id_list],
                             f"{output_dir}/{base_name}-entities.json")
        # TODO: sanity check on uniqueness of facet labels

    @staticmethod
    def _export_as_json(data: Any, path: str):
        logger.info(f"=> {path}")
        with open(path, 'w', encoding="utf8") as f:
            json.dump(data, fp=f, indent=2, ensure_ascii=False)

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

    def _is_lang_type_object_list(self, value: Any) -> bool:
        return self._is_lang_object_list(value) and "type" in value[0]

    @staticmethod
    def _is_lang_object_list(value: Any) -> bool:
        return isinstance(value, list) and isinstance(value[0], dict) and "lang" in value[0]

    def _convert_object_list_value(self, in_value: Any) -> Any:
        if self._is_lang_type_object_list(in_value):
            out_dict = {}
            for i in in_value:
                if "lang" in i:
                    lang = i["lang"]
                    out_dict[lang] = {}
                else:
                    # TODO: make possible lang values configurable
                    out_dict["nl"] = {}
                    out_dict["en"] = {}
            for i in in_value:
                if "lang" in i:
                    lang = i.pop("lang")
                    o_type = i.pop("type")
                    other = "".join(i.values())
                    out_dict[lang][o_type] = other
                else:
                    o_type = i.pop("type")
                    other = "".join(i.values())
                    out_dict["en"][o_type] = other
                    out_dict["nl"][o_type] = other
            return out_dict
        elif self._is_lang_object_list(in_value):
            out_dict = {}
            for i in in_value:
                lang = i.pop("lang")
                other = "".join(i.values())
                out_dict[lang] = other
            return out_dict
        else:
            return in_value

    def _convert_lang_object_list_fields(
            self, in_dict: dict[str, Any]
    ) -> dict[str, Any]:
        return {k: self._convert_object_list_value(v) for (k, v) in in_dict.items()}

    def _convert_all_object_lists_with_lang_fields_to_dict(
            self, in_dict: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        return {k: self._convert_lang_object_list_fields(v) for (k, v) in in_dict.items()}

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

    def _add_labels_for_persons(self, entity_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        new_dict = {}
        for entity_id, entity in entity_dict.items():
            if "persName" in entity:
                preferred_pers_name = self._preferred_pers_name(entity["persName"])
                normalized_pers_name = self._normalized(preferred_pers_name)
                entity["displayLabel"] = self._display_label(normalized_pers_name)
                entity["sortLabel"] = self._sort_label(normalized_pers_name)
            new_dict[f"{entity_id}"] = entity
        return new_dict

    def _extend_graphic_url(
            self,
            entity_dict: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        if self.graphic_url_mapper:
            new_dict = {}
            for entity_id, entity in entity_dict.items():
                if "graphic" in entity and ("url" in entity["graphic"]):
                    graphic_url = entity["graphic"]["url"]
                    entity["graphic"]["url"] = self.graphic_url_mapper(graphic_url)
                new_dict[f"{entity_id}"] = entity
            return new_dict
        else:
            return entity_dict

    @staticmethod
    def _preferred_pers_name(pers_names: list[dict[str, Any]]) -> dict[str, Any]:
        if len(pers_names) == 1:
            return pers_names[0]
        else:
            abb = [pn for pn in pers_names if pn["full"] == "abb"][0]
            if "forename" in abb:
                return abb
            else:
                return [pn for pn in pers_names if "forename" in pn][0]

    @staticmethod
    def _display_label(pers_name: NormalizedPersName) -> str:
        parts = [pers_name.forename, pers_name.name_link, pers_name.surname, pers_name.add_name]
        non_empty_parts = [p for p in parts if p]
        return " ".join(non_empty_parts)

    @staticmethod
    def _sort_label(pers_name: NormalizedPersName) -> str:
        parts = [pers_name.name_link.capitalize(), pers_name.surname, pers_name.add_name, pers_name.forename]
        non_empty_parts = [p for p in parts if p]
        if len(non_empty_parts) == 1:
            return non_empty_parts[0]
        else:
            return " ".join(non_empty_parts[:-1]) + ", " + non_empty_parts[-1]

    def _normalized(self, pers_name: dict[str, Any]) -> NormalizedPersName:
        forename = pers_name.get("forename", "")
        name_link = pers_name.get("nameLink", "")
        surname = self._normalized_surname(pers_name)
        add_name = pers_name.get("addName", "")
        return NormalizedPersName(
            forename, name_link, surname, add_name
        )

    @staticmethod
    def _normalized_surname(pers_name: dict[str, Any]) -> str:
        surnames: list[str] | str = pers_name.get("surname", [])
        if isinstance(surnames, str):
            return surnames
        elif isinstance(surnames, list):
            if len(surnames) == 1:
                return surnames[0]
            elif len(surnames) == 2:
                return f"{surnames[0]} ({surnames[1]['text']})"
            else:
                return ""
        else:
            return ""

    def _add_label_to_ref(self, entity: dict[str, Any], label4ref: dict[str, str]) -> dict[str, Any]:
        if "relation" in entity and "ref" in entity["relation"]:
            ref = entity["relation"]["ref"]
            if ref in label4ref:
                entity["relation"]["label"] = label4ref[ref]
            else:
                error = f"invalid ref: {ref} for artwork.xml#{entity['id']}"
                logger.error(error)
                self.errors.append(error)
                entity["relation"]["label"] = f"!no label found for ref {ref}"
        return entity

    def _add_labels_to_refs(self):
        bio_path = f"{self.output_directory}/bio-entities.json"
        with open(bio_path) as f:
            bio_entities = json.load(f)
        label_for_ref = {f"bio.xml#{b['id']}": b["displayLabel"] for b in bio_entities}
        artwork_path = f"{self.output_directory}/artwork-entities.json"
        with open(artwork_path) as f:
            artwork_entities = json.load(f)
        new_artwork_entities = [self._add_label_to_ref(a, label_for_ref) for a in
                                artwork_entities]
        with open(artwork_path, "w", encoding="utf8") as f:
            json.dump(new_artwork_entities, f, indent=4, ensure_ascii=False)
