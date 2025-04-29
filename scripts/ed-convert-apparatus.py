#!/usr/env python3
from editem_apparatus.apparatus_converter import ApparatusConverter


def main():
    ac = ApparatusConverter("data/israels-apparatus/", "out/israels")
    ac.convert()


if __name__ == '__main__':
    main()
