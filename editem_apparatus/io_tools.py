import csv
import json
from json import JSONEncoder
from pathlib import Path
from typing import Any

import orjson
from loguru import logger


class IOHandler:

    def __init__(self, file_url_prefix: str = ""):
        self.generated_file_urls = []
        self.file_url_prefix = file_url_prefix

    def write_text(self, path: str, text: str, quiet: bool = False) -> None:
        if not quiet:
            self._log_writing_file(path)
        with open(path, mode='w', newline='') as file:
            file.write(text)
        self._add_generated_file(path)

    def read_text(self, path: str, quiet: bool = False) -> str:
        if not quiet:
            self._log_reading_file(path)
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text

    def write_json(self, path: str, data: Any, quiet: bool = False,
                   encoder: type[JSONEncoder] = JSONEncoder) -> None:
        if not quiet:
            self._log_writing_file(path)
        with open(path, mode='w', newline='') as file:
            json.dump(data, file, indent=4, ensure_ascii=False, cls=encoder)
        self._add_generated_file(path)

    def read_json(self, path: str, quiet: bool = False) -> Any:
        if not quiet:
            self._log_reading_file(path)
        with open(path, 'rb') as f:
            data = orjson.loads(f.read())
        return data

    def write_tsv(self, path: str, headers: list[str], records: list[Any], quiet: bool = False) -> None:
        if not quiet:
            self._log_writing_file(path)
        with open(path, mode='w', newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(headers)
            writer.writerows(records)

    def write_csv(self, path: str, headers: list[str], records: list[Any], quiet: bool = False) -> None:
        if not quiet:
            self._log_writing_file(path)
        with open(path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(records)

    def report_generated_files(self) -> None:
        print("generated files:")
        for f in sorted(self.generated_file_urls):
            print(f"- {f}")

    def _add_generated_file(self, path: str):
        self.generated_file_urls.append(f"{self.file_url_prefix}{path}")

    @staticmethod
    def _log_reading_file(path: str | Path, extra: str = "") -> None:
        logger.info(f"<= {path}{extra}")

    @staticmethod
    def _log_writing_file(path: str | Path, extra: str = "") -> None:
        logger.info(f"=> {path}{extra}")
