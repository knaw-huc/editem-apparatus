#!/usr/bin/env python3
from editem_apparatus.apparatus_converter import ApparatusConverter
from editem_apparatus.editem_apparatus_config import EditemApparatusConfig


def main():
    cf = EditemApparatusConfig(
        project_name="israels",
        data_path="data/israels-apparatus/",
        export_path="out/israels",
        show_progress=True
    )
    errors = ApparatusConverter(cf).convert()
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")

if __name__ == '__main__':
    main()
