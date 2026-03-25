import json
import os
import sys
import traceback
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import Any, Dict, Union

import xmltodict
from icecream import ic
from loguru import logger

from editem_apparatus.editem_menu_config import EditemMenuConfig

ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}


class MenuConverter:
    def __init__(self, config: EditemMenuConfig):
        self.apparatus_directory = config.data_path.removesuffix("/")
        self.output_directory = config.export_path.removesuffix("/")
        self.file_url_prefix = config.file_url_prefix
        self.errors = []
        self.generated_file_urls = []
        if not config.show_progress:
            logger.remove()
            logger.add(sys.stderr, level="WARNING")
        if config.log_file_path:
            logger.remove()
            if os.path.exists(config.log_file_path):
                os.remove(config.log_file_path)
            logger.add(config.log_file_path)

    def convert(self) -> list[str]:
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
        print("generated files:")
        for f in sorted(self.generated_file_urls):
            print(f"- {f}")
        return self.errors

    def _process_xml(self, xml_path: str, output_dir: str, base_name: str):
        logger.info(f"<= {xml_path}")
        with open(xml_path, encoding="utf8") as f:
            xml_source = f.read()

        self._convert_to_json(xml_source, output_dir, base_name)

    def _convert_to_json(self, xml: str, output_dir: str, base_name: str):
        # export json conversion of complete xml file
        xpars = xmltodict.parse(xml)
        element_dict = self._simplify_keys(list(xpars.values())[0])
        simplified_menu = self._simplify_menu(element_dict["standOff"]["menubar"])
        # self._print_menu_node(simplified_menu)
        js = json.dumps(simplified_menu, indent=2, ensure_ascii=False)
        path = f"{output_dir}/{base_name}.json"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding="utf8") as f:
            f.write(js)
        self._add_generated_file(path)

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

    def _add_generated_file(self, path: str):
        self.generated_file_urls.append(f"{self.file_url_prefix}{path}")

    def _simplify_menu(self, node: Union[dict, list, str]) -> Union[dict, list, str]:
        if isinstance(node, list):
            return [self._simplify_menu(item) for item in node]

        if isinstance(node, dict):
            new_node = {}
            for key, value in node.items():
                if key == "menuitem":
                    new_node["items"] = self._simplify_menu(value)
                elif key == "ptr":
                    # Compact ptr.target → target
                    new_node["target"] = value["target"].replace(".xml", "")
                else:
                    new_node[key] = self._simplify_menu(value)
            return new_node

        return node

    def _print_menu_node(self, node: Union[dict, list, str], depth: int = 0) -> None:
        indent = "  " * depth

        if isinstance(node, list):
            for item in node:
                self._print_menu_node(item, depth)

        elif isinstance(node, dict):
            if "label" in node:
                print(f"{indent}{node['label']}", end='')
                if "target" in node:
                    print(f" ({node['target']})", end='')
                print()
            for key in ("menu", "items"):
                if key in node:
                    self._print_menu_node(node[key], depth + 1)


def main():
    parser = ArgumentParser(
        description="Convert editem menu config to json",
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--inputdir', help="Input (data) Directory", type=str, required=True)
    parser.add_argument('-o', '--outputdir', help="Output (export) Directory", type=str, required=True)
    parser.add_argument('-l', '--logfile', help="Log file (output)", type=str, default=None)
    parser.add_argument('--ignore-errors', help="Ignore errors", action='store_true')
    args = parser.parse_args()

    if args.ignore_errors:
        logger.remove()
        logger.add(sink=sys.stderr, level="WARNING")

    config = EditemMenuConfig(
        data_path=args.inputdir,
        export_path=args.outputdir,
        show_progress=False,
        log_file_path=args.logfile,
    )

    errors = MenuConverter(config).convert()
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
