import os
import sys
import traceback
import xml.sax
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from icecream import ic
from loguru import logger

from editem_apparatus.configs import EditemConfig
from editem_apparatus.home_handler import HomeHandler

ns = {'xml': 'http://www.w3.org/XML/1998/namespace'}


class HomeConverter:
    def __init__(self, config: EditemConfig):
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
        xml_files = [xml for xml in os.listdir(base_dir) if xml.endswith("home.xml")]
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

        self._convert_to_html(xml_source, output_dir, base_name)

    def _convert_to_html(self, xml_source: str, output_dir, base_name):
        handler = HomeHandler()
        xml.sax.parseString(xml_source, handler)
        path = f"{output_dir}/{base_name}.html"
        logger.info(f"=> {path}")
        with open(path, 'w', encoding="utf8") as f:
            f.write(handler.html)
        self.generated_file_urls.append(path)

@logger.catch
def main():
    parser = ArgumentParser(
        description="Convert editem home config to html",
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--inputdir', help="Input (data) Directory", type=str, required=True)
    parser.add_argument('-o', '--outputdir', help="Output (export) Directory", type=str, required=True)
    parser.add_argument('-l', '--logfile', help="Log file (output)", type=str, default=None)
    parser.add_argument('--ignore-errors', help="Ignore errors", action='store_true')
    args = parser.parse_args()

    if args.ignore_errors:
        logger.remove()
        logger.add(sink=sys.stderr, level="WARNING")

    config = EditemConfig(
        data_path=args.inputdir,
        export_path=args.outputdir,
        show_progress=False,
        log_file_path=args.logfile,
    )

    errors = HomeConverter(config).convert()
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
