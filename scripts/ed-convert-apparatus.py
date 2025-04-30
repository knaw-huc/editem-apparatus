#!/usr/bin/env python3
from editem_apparatus.apparatus_converter import ApparatusConverter
from editem_apparatus.editem_apparatus_config import EditemApparatusConfig


def main():
    cf = EditemApparatusConfig(
        project_name="israels",
        data_path="data/israels-apparatus/",
        export_path="out/israels",
        static_file_server_base_url="https://data.editem.huygens.nl/israels/apparatus",
        show_progress=False
    )
    ac = ApparatusConverter(cf)
    ac.convert()


if __name__ == '__main__':
    main()
