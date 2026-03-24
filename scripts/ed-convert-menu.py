#!/usr/bin/env python3
from editem_apparatus.editem_menu_config import EditemMenuConfig
from editem_apparatus.menu_converter import MenuConverter


def main():
    cf = EditemMenuConfig(
        data_path="data/van-gogh-config/",
        export_path="out",
        show_progress=True,
        file_url_prefix="http://localhost:8040/files/van-gogh/config/"
    )
    errors = MenuConverter(cf).convert()
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")


if __name__ == '__main__':
    main()
