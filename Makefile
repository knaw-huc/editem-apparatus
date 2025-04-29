all: help
SHELL=/bin/bash
#include .local/.env

.PHONY: install
install:
	poetry lock && poetry install

.PHONY: tests
tests:
	poetry run pytest

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
	@echo "make-tools for untanngle"
	@echo
	@echo "Please use \`make <target>', where <target> is one of:"
	@echo "  install  - to install the necessary requirements"
	@echo "  tests    - to run the unit tests in tests/"
	@echo
	@echo "  version-update-patch  - to update the project version to the next patch version"
	@echo "  version-update-minor  - to update the project version to the next minor version"
	@echo "  version-update-major  - to update the project version to the next major version"
