"""Convert editem apparatus TEI XML files into JSON and HTML exports.

For every ``*.xml`` file in the input directory this module writes:

* ``<base>.json``: the complete XML document as JSON,
* ``<base>.html``: an HTML rendering of the document,
* ``<base>-entity-dict.json``: all ``xml:id`` elements keyed by ``<base>/<xml:id>``,
* ``<base>[.<list-id>]-entities.json``: entities as lists, split per
  ``listObject``/``listBibl``/``listPerson`` when those carry an ``xml:id``.

Entities are normalized along the way (language-keyed fields, list values,
person labels, IIIF graphic URLs and dimensions), and artwork relations are
afterwards annotated with labels of the referenced bio entities.
"""
import csv
import glob
import itertools
import os
import re
import sys
import traceback
import xml.etree.ElementTree as ET
import xml.sax
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from dataclasses import dataclass
from typing import Any, Dict, Union

import xmltodict
from loguru import logger
from toolz import pipe

from editem_apparatus.apparatus_handler import ApparatusHandler
from editem_apparatus.editem_apparatus_config import EditemApparatusConfig
from editem_apparatus.io_tools import IOHandler

ns = {
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'tei': 'http://www.tei-c.org/ns/1.0'
}

rw = IOHandler()


@dataclass
class NormalizedPersName:
    """The parts of a ``<persName>`` as plain strings (empty string when absent)."""
    full_name: str
    forename: str
    name_link: str
    surname: str
    add_name: str
    gen_name: str
    role_name: str


@dataclass
class Dimensions:
    """Pixel dimensions of an illustration."""
    width: int
    height: int


class ApparatusConverter:
    """Converts a directory of editem apparatus TEI files to JSON and HTML.

    Problems that do not abort the conversion are collected in ``self.errors``
    and returned by :meth:`convert`.
    """

    def __init__(self, config: EditemApparatusConfig):
        """Set up paths, illustration dimensions and logging from ``config``.

        Args:
            config: Conversion settings (input/output paths, URL mapper,
                illustration sizes file, logging options, label ordering).
        """
        self.keep_name_order_for_sort_label = config.keep_name_order_for_sort_label
        self.apparatus_directory = config.data_path.removesuffix("/")
        self.output_directory = config.export_path.removesuffix("/")
        self.graphic_url_mapper = config.graphic_url_mapper
        self.file_url_prefix = config.file_url_prefix
        self.errors = []
        self.illustration_sizes_file = config.illustration_sizes_file
        if config.illustration_sizes_file:
            self.illustration_dimensions = self._load_illustration_dimensions(config.illustration_sizes_file)
            if len(self.illustration_dimensions) == 0:
                message = "No illustrations were found in the sizes file!"
                print(f"WARNING: {message}", file=sys.stderr)
                self.errors.append(message)
        else:
            self.illustration_dimensions = {}
        if not config.show_progress:
            logger.remove()
            logger.add(sys.stderr, level="WARNING")
        if config.log_file_path:
            logger.remove()
            if os.path.exists(config.log_file_path):
                os.remove(config.log_file_path)
            logger.add(config.log_file_path)

    def convert(self) -> list[str]:
        """Convert every ``.xml`` file in the input directory.

        A failure in one file is recorded and does not stop the others. After
        all files are processed, artwork relations are labelled with bio entity
        labels and the generated files are reported.

        Returns:
            The collected error messages (empty if everything went well).
        """
        base_dir = self.apparatus_directory
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith(".xml")]
        for xml_file in xml_files:
            try:
                base_name = xml_file.removesuffix(".xml")
                export_dir = f"{self.output_directory}"
                os.makedirs(export_dir, exist_ok=True)
                self._process_xml(f"{base_dir}/{xml_file}", export_dir, base_name)
            except Exception as e:
                message = f"there was an error converting {xml_file}: {e}"
                self.errors.append(message)
                print(traceback.format_exc(), file=sys.stderr)
        self._add_labels_to_refs()
        rw.report_generated_files()
        return self.errors

    def _process_xml(self, xml_path: str, output_dir: str, base_name: str):
        """Read one XML file and write its JSON and HTML exports."""
        xml_source = rw.read_text(xml_path)

        self._convert_to_json(xml_source, output_dir, base_name)
        self._convert_to_html(xml_source, output_dir, base_name)

    def _convert_to_json(self, xml: str, output_dir: str, base_name: str):
        """Export the XML document and its identified entities as JSON.

        Writes the whole document, then, per list element (``listObject``,
        ``listBibl``, ``listPerson``, or the whole ``<text>`` if none exist),
        every element with an ``xml:id`` after running it through the
        normalization pipeline.

        Args:
            xml: The XML source.
            output_dir: Directory to write to.
            base_name: File name without extension, used as prefix for outputs.
        """
        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        element_dict = self._simplify_keys(list(xpars.values())[0])
        path = f"{output_dir}/{base_name}.json"
        rw.write_json(path, element_dict)

        list_elements = []
        root = ET.fromstring(xml)
        text_node = root.find(".//{http://www.tei-c.org/ns/1.0}text")
        if text_node is not None:
            list_tags = ["listObject", "listBibl", "listPerson"]
            list_elements = list(
                itertools.chain.from_iterable(
                    [text_node.findall(f".//tei:{lt}", namespaces=ns) for lt in list_tags]
                )
            )
            if not list_elements:
                list_elements = [text_node]

        all_entity_dict = {}
        entities_were_split = False
        for list_element in [le for le in list_elements if le is not None]:
            xml_id = list_element.attrib.get(f'{{{ns["xml"]}}}id')
            if xml_id:
                typed_base_name = f"{base_name}.{xml_id}"
                entities_were_split = True
            else:
                typed_base_name = base_name

            # export all elements with xml:id to json files
            identified_elements = list_element.findall(".//*[@xml:id]", namespaces=ns)
            entity_dict: dict[str, Any] = {}
            entity_id_list: list[str] = []
            relevant_identified_elements = [ie for ie in identified_elements if
                                            ie.tag != "{http://www.tei-c.org/ns/1.0}listObject"]
            for element in relevant_identified_elements:
                xml_id = element.attrib.get(f'{{{ns["xml"]}}}id')
                if xml_id is not None:
                    xml_str = ET.tostring(element, encoding='UTF-8')
                    parsed_dict = xmltodict.parse(xml_str)
                    element_dict = self._simplify_keys(list(parsed_dict.values())[0])
                    pers_names = element.findall('.//tei:persName[@full="yes"]', namespaces=ns)
                    if len(pers_names) > 0:
                        element_dict["full_name"] = " ".join(pers_names[0].itertext())
                    # filepath = os.path.join(output_dir, f"{xml_id}.json")
                    # logger.info(f"=> {filepath}")
                    # with open(filepath, 'w') as f:
                    #     json.dump(element_dict, fp=f, indent=2, ensure_ascii=False)
                    entity_dict[f"{base_name}/{xml_id}"] = element_dict
                    entity_id_list.append(xml_id)

            converted_entity_dict = pipe(
                entity_dict,
                self._convert_all_object_lists_with_lang_fields_to_dict,
                self._normalize_list_values,
                self._add_labels_for_persons,
                self._extend_graphic_annotation,
                self._convert_source_to_list,
                self._convert_relation_to_list,
                clean_nones
            )
            all_entity_dict.update(converted_entity_dict)
            self._export_as_json([converted_entity_dict[f"{base_name}/{k}"] for k in entity_id_list],
                                 f"{output_dir}/{typed_base_name}-entities.json")
            # TODO: sanity check on uniqueness of facet labels
        self._export_as_json(all_entity_dict, f"{output_dir}/{base_name}-entity-dict.json")
        if entities_were_split:
            self._export_as_json(list(all_entity_dict.values()), f"{output_dir}/{base_name}-entities.json")

    @staticmethod
    def _export_as_json(data: Any, path: str):
        """Write ``data`` as JSON to ``path``, with ``None`` values removed."""
        rw.write_json(path, clean_nones(data))

    def _simplify_keys(self, kv_dict: dict[str, Any]) -> dict[str, Any]:
        """Recursively turn xmltodict keys into plain names.

        Drops ``@xmlns*`` keys, strips the ``@``/``#`` prefixes and any
        namespace prefix (``xml:id`` becomes ``id``), and removes ``None`` values.
        """
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
        return clean_nones(new_dict)

    def _is_lang_type_object_list(self, value: Any) -> bool:
        """True if ``value`` is a list of dicts having ``lang`` and ``type`` keys."""
        return self._is_lang_object_list(value) and "type" in value[0]

    def _is_lang_type_object(self, value: Any) -> bool:
        """True if ``value`` is a dict having ``lang`` and ``type`` keys."""
        return self._is_lang_object(value) and "type" in value

    def _is_lang_object_list(self, value: Any) -> bool:
        """True if ``value`` is a list whose first item is a dict with a ``lang`` key."""
        return isinstance(value, list) and self._is_lang_object(value[0])

    @staticmethod
    def _is_lang_object(value: Any) -> bool:
        """True if ``value`` is a dict with a ``lang`` key."""
        return isinstance(value, dict) and "lang" in value

    def _convert_object_list_value(self, in_value: Any) -> Any:
        """Re-key language-tagged values by language (and by type, if present).

        Examples of the resulting shapes::

            [{lang, type, ...}, ...] -> {lang: {type: value}}
            [{lang, ...}, ...]       -> {lang: value}
            {lang, type, ...}        -> {lang: {type: value}}
            {lang, ...}              -> {lang: value}

        Items with a type but without a language are assigned to both ``nl``
        and ``en``. Any other value is returned unchanged. Note that this
        mutates the input dicts (``lang``/``type`` are popped).
        """
        if self._is_lang_type_object_list(in_value):
            out_dict = {}
            for i in in_value:
                langs = [i["lang"]] if "lang" in i else ["nl", "en"]
                o_type = i.pop("type")
                i.pop("lang", None)
                simplified = self._simplify(i)
                for lang in langs:
                    out_dict.setdefault(lang, {})[o_type] = simplified
            return out_dict
        elif self._is_lang_object_list(in_value):
            out_dict = {}
            for i in in_value:
                out_dict[i.pop("lang")] = self._simplify(i)
            return out_dict
        elif self._is_lang_type_object(in_value):
            lang = in_value.pop("lang")
            o_type = in_value.pop("type")
            return {lang: {o_type: self._simplify(in_value)}}
        elif self._is_lang_object(in_value):
            lang = in_value.pop("lang")
            return {lang: self._simplify(in_value)}
        else:
            return in_value

    @staticmethod
    def _simplify(d: dict[str, Any]) -> Any:
        """Collapse ``{"text": ...}`` to its whitespace-normalized string; else return ``d``."""
        if len(d) == 1 and "text" in d:
            return re.sub(r'\s+', ' ', d["text"]).strip()
        return d

    def _convert_all_object_lists_with_lang_fields_to_dict(
            self, in_dict: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Apply the language re-keying to the fields of every entity."""
        return {k: self._convert_lang_object_list_fields(v) for (k, v) in in_dict.items()}

    def _convert_lang_object_list_fields(
            self, in_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply :meth:`_convert_object_list_value` to each field of one entity."""
        return {k: self._convert_object_list_value(v) for (k, v) in in_dict.items()}

    def _normalize_list_values(self, in_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Make fields that are a list in any entity a list in all entities.

        XML-to-dict conversion yields a scalar for a single occurrence and a
        list for repeated ones; this wraps the scalars so consumers see a
        consistent type per (dotted) field path.
        """

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
        """Collect the dotted paths of all fields that hold a list in any entity."""

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
        """Add ``displayLabel`` and ``sortLabel`` to entities that have a ``persName``.

        With ``keep_name_order_for_sort_label`` both labels are the full name
        as written; otherwise they are built from the preferred name's parts.
        A warning is logged when a person has no usable name parts.
        """
        new_dict = {}
        for entity_id, entity in entity_dict.items():
            if "persName" in entity:
                preferred_pers_name = self._preferred_pers_name(entity["persName"])
                normalized_pers_name = self._normalized(preferred_pers_name)
                if len("".join(
                        [normalized_pers_name.forename, normalized_pers_name.name_link, normalized_pers_name.surname,
                         normalized_pers_name.add_name, normalized_pers_name.gen_name])) == 0:
                    logger.warning(
                        f"no nameparts (forename, surname, etc.) found in Person #{entity_id}, using fullname for displayLabel/sortLabel")
                if self.keep_name_order_for_sort_label:
                    full_name = entity.pop("full_name")
                    entity["displayLabel"] = full_name
                    entity["sortLabel"] = full_name
                else:
                    entity["displayLabel"] = self._display_label(normalized_pers_name)
                    entity["sortLabel"] = self._sort_label(normalized_pers_name)

            new_dict[entity_id] = entity
        return new_dict

    def _extend_graphic_annotation(self, entity_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Rewrite graphic URLs and add image width/height.

        Only active when both a URL mapper and illustration dimensions are
        configured. Graphics missing from the sizes file get a warning and an
        entry in ``self.errors``.
        """
        if self.graphic_url_mapper and self.illustration_dimensions:
            new_dict = {}
            for entity_id, entity in entity_dict.items():
                if "graphic" in entity and ("url" in entity["graphic"]):
                    graphic_url = entity["graphic"]["url"]
                    entity["graphic"]["url"] = self.graphic_url_mapper(graphic_url)
                    if graphic_url in self.illustration_dimensions:
                        dimensions = self.illustration_dimensions[graphic_url]
                        entity["graphic"]["width"] = dimensions.width
                        entity["graphic"]["height"] = dimensions.height
                    else:
                        msg = f"missing width/height: no illustration dimensions found in {self.illustration_sizes_file} for <graphic url=\"{graphic_url}\"/>: no entry for file {graphic_url}"
                        logger.warning(msg)
                        self.errors.append(msg)
                new_dict[entity_id] = entity
            return new_dict
        else:
            return entity_dict

    @staticmethod
    def _convert_source_to_list(entity_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Split each entity's space-separated ``source`` string into a list."""
        new_dict = {}
        for entity_id, entity in entity_dict.items():
            if "source" in entity:
                entity["source"] = entity["source"].split(" ")
            new_dict[entity_id] = entity
        return new_dict

    @staticmethod
    def _convert_relation_to_list(entity_dict: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Wrap a single ``relation`` dict in a list so it is always a list."""
        new_dict = {}
        for entity_id, entity in entity_dict.items():
            if "relation" in entity and isinstance(entity["relation"], dict):
                entity["relation"] = [entity["relation"]]
            new_dict[entity_id] = entity
        return new_dict

    @staticmethod
    def _preferred_pers_name(pers_names: Union[dict[str, Any], list[dict[str, Any]]]) -> dict[str, Any]:
        """Pick the ``persName`` to build labels from.

        A single name is used as is. Among several, the abbreviated one
        (``full="abb"``) is preferred, unless it lacks a ``forename`` and
        another name has one; with no abbreviated name the first is used.
        """
        if isinstance(pers_names, dict):
            return pers_names
        elif len(pers_names) == 1:
            return pers_names[0]
        else:
            abbs = [pn for pn in pers_names if pn["full"] == "abb"]
            if abbs:
                abb = abbs[0]
                if "forename" in abb:
                    return abb
                else:
                    try:
                        return [pn for pn in pers_names if "forename" in pn][0]
                    except IndexError:
                        # fallback
                        return abb
            else:
                return pers_names[0]

    @staticmethod
    def _display_label(pers_name: NormalizedPersName) -> str:
        """Build the display label: name parts in natural order, or the full name if none."""
        parts = [pers_name.forename, pers_name.name_link, pers_name.surname, pers_name.add_name, pers_name.gen_name]
        non_empty_parts = [p for p in parts if p]
        if len(non_empty_parts) == 0:
            non_empty_parts = [pers_name.full_name]
        return " ".join(non_empty_parts)

    def _sort_label(self, pers_name: NormalizedPersName) -> str:
        """Build the sort label for a person.

        By default: ``"<nameLink> <surname> <addName> <genName>, <forename>"``
        (surname-first). With ``keep_name_order_for_sort_label``: the parts in
        written order, followed by ``", <roleName>"`` when a role is present.
        Falls back to the full name when there are no name parts.
        """
        if self.keep_name_order_for_sort_label:
            # use the text in the order presented in <persName>
            parts = [pers_name.forename, pers_name.gen_name, pers_name.name_link, pers_name.surname, pers_name.add_name]
            non_empty_parts = [p for p in parts if p]
            postfix = f", {pers_name.role_name}" if pers_name.role_name is not (None or "") else ""
            if len(non_empty_parts) == 1:
                return non_empty_parts[0] + postfix
            elif len(non_empty_parts) == 0:
                return pers_name.full_name + postfix
            else:
                return " ".join(non_empty_parts) + postfix
        else:
            parts = [pers_name.name_link.capitalize(), pers_name.surname, pers_name.add_name, pers_name.gen_name,
                     pers_name.forename]
            non_empty_parts = [p for p in parts if p]
            if len(non_empty_parts) == 1:
                return non_empty_parts[0]
            elif len(non_empty_parts) == 0:
                return pers_name.full_name
            else:
                return " ".join(non_empty_parts[:-1]) + ", " + non_empty_parts[-1]

    def _normalized(self, pers_name: dict[str, Any]) -> NormalizedPersName:
        """Extract the name parts of a ``persName`` dict into a :class:`NormalizedPersName`."""
        # now deprecated? https://editem.pages.huc.knaw.nl/editem-schema/templates/biolist/biolist-encoding.html#name
        full_name = self._value(pers_name, "name")
        forename = self._value(pers_name, "forename")
        name_link = self._value(pers_name, "nameLink")
        surname = self._normalized_surname(pers_name)
        add_name = self._value(pers_name, "addName")
        gen_name = self._value(pers_name, "genName")
        role_name = self._value(pers_name, "roleName")
        return NormalizedPersName(
            full_name=full_name,
            forename=forename,
            name_link=name_link,
            surname=surname,
            add_name=add_name,
            gen_name=gen_name,
            role_name=role_name
        )

    @staticmethod
    def _value(pers_name: dict[str, Any], field: str) -> str:
        """Get ``field`` from ``pers_name`` as a string.

        Missing or ``None`` gives ``""``; a list is joined with ``", "`` (and a
        warning is logged).
        """
        value = pers_name.get(field, "")
        if value is None:
            return ""
        elif isinstance(value, (list, tuple)):
            value = ", ".join((x for x in value if isinstance(x, str)))
            logger.warning(f"Expected string, got array for {field}, forcing concatenation to: '{value}'")
        return value

    @staticmethod
    def _normalized_surname(pers_name: dict[str, Any]) -> str:
        """Get the surname as a string.

        A list of two surnames becomes ``"first (second)"``; a single-item list
        yields that item; any other list length yields ``""``.
        """
        surname_value: Union[list[str], str] = pers_name.get("surname", [])
        if isinstance(surname_value, str):
            return surname_value
        elif isinstance(surname_value, list):
            surnames = [s for s in surname_value if s is not None]
            if len(surnames) == 1:
                return surnames[0]
            elif len(surnames) == 2:
                if isinstance(surnames[1], str):
                    return f"{surnames[0]} ({surnames[1]})"
                else:
                    return f"{surnames[0]} ({surnames[1]['text']})"
            else:
                return ""
        else:
            return ""

    def _add_label_to_ref(self, entity: dict[str, Any], label4ref: dict[str, str], sort_label4ref: dict[str, str]) -> \
            dict[str, Any]:
        """Add ``displayLabel``/``sortLabel`` to each ``relation`` of an entity, based on its ``ref``.

        Args:
            entity: The entity whose relations are annotated (modified in place).
            label4ref: Display labels keyed by ref (e.g. ``bio.xml#id``).
            sort_label4ref: Sort labels keyed by ref.

        Unknown refs are logged and recorded in ``self.errors``, and get a
        placeholder display label.
        """
        if "relation" in entity:
            relation = entity["relation"]
            if isinstance(relation, dict):
                relation = [relation]
            for i, rel in enumerate(relation):
                if "ref" in rel:
                    ref = relation[i]["ref"]
                    if ref in label4ref:
                        relation[i]["displayLabel"] = label4ref[ref]
                        relation[i]["sortLabel"] = sort_label4ref[ref]
                    else:
                        error = f"invalid ref: {ref} for artwork.xml#{entity['id']}"
                        logger.error(error)
                        self.errors.append(error)
                        relation[i]["displayLabel"] = f"!no label found for ref {ref}"
        return entity

    def _add_labels_to_refs(self):
        """Label the relations in the artwork exports with labels from ``bio-entities.json``.

        Rewrites ``artwork*-entities.json`` and ``artwork-entity-dict.json`` in
        the output directory. Does nothing for files that do not exist.
        """
        # load bio-entities
        label_for_ref = {}
        sort_label_for_ref = {}
        bio_path = f"{self.output_directory}/bio-entities.json"
        if os.path.exists(bio_path):
            bio_entities = rw.read_json(bio_path)
            label_for_ref = {f"bio.xml#{b['id']}": b["displayLabel"] for b in bio_entities}
            sort_label_for_ref = {f"bio.xml#{b['id']}": b["sortLabel"] for b in bio_entities}

        # rewrite artwork.*-entities.json, add label to relation.ref elements
        artwork_paths = glob.glob(f"{self.output_directory}/artwork*-entities.json")
        for artwork_path in artwork_paths:
            artwork_entities = rw.read_json(artwork_path)
            new_artwork_entities = [self._add_label_to_ref(a, label_for_ref, sort_label_for_ref) for a in
                                    artwork_entities]
            rw.write_json(artwork_path, new_artwork_entities)
        entity_dict_path = f"{self.output_directory}/artwork-entity-dict.json"
        if os.path.exists(entity_dict_path):
            entity_dict = rw.read_json(entity_dict_path)
            new_entity_dict = {k: self._add_label_to_ref(v, label_for_ref, sort_label_for_ref)
                               for k, v in entity_dict.items()}
            rw.write_json(entity_dict_path, new_entity_dict)

    @staticmethod
    def _convert_to_html(xml_string: str, output_dir: str, base_name: str) -> None:
        """Render the XML as HTML with :class:`ApparatusHandler` and write ``<base_name>.html``."""
        # toc = _head
        handler = ApparatusHandler()
        xml.sax.parseString(xml_string, handler)
        path = f"{output_dir}/{base_name}.html"
        rw.write_text(path, handler.html_string)

    @staticmethod
    def _load_illustration_dimensions(illustration_sizes_file: str) -> dict[str, Dimensions]:
        """Load illustration sizes from a tab-separated file.

        The file needs a header with ``file``, ``width`` and ``height`` columns.

        Returns:
            A mapping from file name to its :class:`Dimensions`.
        """
        illustration_dimensions: dict[str, Dimensions] = {}
        if illustration_sizes_file is not None:
            with open(illustration_sizes_file, encoding='utf8') as f:
                for record in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                    illustration_dimensions[record["file"]] = Dimensions(int(record["width"]), int(record["height"]))
        return illustration_dimensions


# Source - https://stackoverflow.com/a/60124334
# Posted by MatanRubin
# Retrieved 2026-08-19, License - CC BY-SA 4.0

def clean_nones(value: Any) -> Any:
    """
    Recursively remove all None values from dictionaries and lists, and returns
    the result as a new dictionary or list.
    """
    if isinstance(value, list):
        return [clean_nones(x) for x in value if x is not None]
    elif isinstance(value, dict):
        return {
            key: clean_nones(val)
            for key, val in value.items()
            if val is not None
        }
    else:
        return value


def main():
    """Command-line entry point.

    Parses arguments, builds the IIIF graphic URL mapper and the converter
    config, runs the conversion, and exits with status 1 if errors occurred
    (unless ``--ignore-errors`` is given).
    """
    parser = ArgumentParser(
        description="Extract structured data from editem apparatus tei xml",
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--project', help="Project name", type=str, required=True)
    parser.add_argument('-i', '--inputdir', help="Input (data) Directory", type=str, required=True)
    parser.add_argument('-o', '--outputdir', help="Output (export) Directory", type=str, required=True)
    parser.add_argument('-b', '--base-url', help="URL for the IIIF image server (scheme + server + prefix)", type=str,
                        required=True)
    parser.add_argument('-n', '--no-prefix',
                        help="Do not add any further prefixes (defaults to '{project}|illustrations|') to the base URL",
                        action='store_true')
    parser.add_argument('-X', '--no-extension',
                        help="Actively strip the extension from the URL, by default one is always added (jpg is guessed by default)",
                        action='store_true')
    parser.add_argument('-l', '--logfile', help="Log file (output)", type=str, default=None)
    parser.add_argument('-s', '--sizes', help="Illustration sizes file", type=str)
    parser.add_argument('--ignore-errors', help="Ignore errors", action='store_true')
    parser.add_argument('--keep-name-order-for-sort-label', help="Don't use lastname, firstname for sortLabel",
                        action='store_true')
    args = parser.parse_args()

    if args.ignore_errors:
        logger.remove()
        logger.add(sink=sys.stderr, level="WARNING")

    def url_mapper(url):
        """Map an illustration file name to its IIIF image URL.

        Prepends the base URL (plus ``<project>|illustrations|`` unless
        ``--no-prefix``) and then either strips the extension (``--no-extension``)
        or appends ``.jpg`` when the file name has no image extension.
        """
        base = args.base_url
        if base[-1] != '/':
            base += '/'
        if args.no_prefix:
            base += f"{url}"
        else:
            base += f"{args.project}|illustrations|{url}"
        if args.no_extension:
            if has_image_extension(url):
                base = ".".join(base.split('.')[:-1])
            return base
        else:
            if not has_image_extension(url):  # some projects don't add the extension
                return f"{base}.jpg"  # guess one
            return base

    def has_image_extension(url) -> Any:
        """True if ``url`` ends with a known image extension."""
        return url.endswith(('.jpg', '.jpeg', '.tif', '.gif', '.png', '.webp'))

    config = EditemApparatusConfig(
        project_name=args.project,
        data_path=args.inputdir,
        export_path=args.outputdir,
        show_progress=False,
        graphic_url_mapper=url_mapper,
        log_file_path=args.logfile,
        illustration_sizes_file=args.sizes,
        keep_name_order_for_sort_label=args.keep_name_order_for_sort_label
    )

    errors = ApparatusConverter(config).convert()
    if errors:
        for error in errors:
            logger.error(error)
        if args.ignore_errors:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
