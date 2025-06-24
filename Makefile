all: help
SHELL=/bin/bash
#include .local/.env

.PHONY: install
install:
	poetry lock && poetry install

.PHONY: test
test:
	poetry run pytest

.PHONY: convert-apparatus-israels
convert-apparatus-israels:
	poetry run ./scripts/ed-convert-apparatus.py

.PHONY: version-update-patch
version-update-patch:
	poetry run version patch

.PHONY: version-update-minor
version-update-minor:
	poetry run version minor

.PHONY: version-update-major
version-update-major:
	poetry run version major

.PHONY: help
help:
	@echo "make-tools for editem-apparatus"
	@echo
	@echo "Please use \`make <target>', where <target> is one of:"
	@echo "  install  - to install the necessary requirements"
	@echo "  test     - to run the unit tests in test/"
	@echo
	@echo "  convert-apparatus-israels - convert the israels apparatus files"
	@echo
	@echo "  version-update-patch  - to update the project version to the next patch version"
	@echo "  version-update-minor  - to update the project version to the next minor version"
	@echo "  version-update-major  - to update the project version to the next major version"
