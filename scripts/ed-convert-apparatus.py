#!/usr/bin/env python3
from editem_apparatus.apparatus_converter import ApparatusConverter
from editem_apparatus.editem_apparatus_config import EditemApparatusConfig


def graphic_url_mapper(url: str) -> str:
    return f"https://preview.dev.diginfra.org/iiif/3/israels|HuygensING|israels|illustrations|{url}.jpg"


def main():
    cf = EditemApparatusConfig(
        project_name="israels",
        data_path="data/israels-apparatus/",
        export_path="out/israels",
        graphic_url_mapper=graphic_url_mapper,
        show_progress=True,
        file_url_prefix="http://localhost:8040/files/israels/apparatus",
        illustration_sizes_file="/Users/bram/workspaces/editem/editem/data/project/israels/scans/sizes_illustrations.tsv"
    )
    errors = ApparatusConverter(cf).convert()
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")


if __name__ == '__main__':
    main()
