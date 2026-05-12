all: help
SHELL=/bin/bash
.SECONDARY:
.DELETE_ON_ERROR:

RED=\033[1;31m
GREEN=\033[1;32m
YELLOW=\033[1;33m
BLUE=\033[1;34m
RESET=\033[0m

.PHONY: install
install:
	poetry lock && poetry install

.PHONY: test
test:
	poetry run pytest

.PHONY: convert-apparatus-israels
convert-apparatus-israels:
	poetry run ./scripts/ed-convert-apparatus.py

.PHONY: convert-apparatus-van-gogh
convert-apparatus-van-gogh:
	poetry run editem-apparatus-convert --project van-gogh --inputdir ../projects/van-gogh-pipeline/datasource/tei/apparatus/ --outputdir out/van-gogh --base-url https://example.org

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
	@echo -e "make-tools for $(GREEN)editem-apparatus$(RESET)"
	@echo
	@echo -e "Please use \`$(YELLOW)make <target>$(RESET)', where $(YELLOW)<target>$(RESET) is one of:"
	@echo -e "  $(BLUE)install$(RESET)  - to install the necessary requirements"
	@echo -e "  $(BLUE)test$(RESET)     - to run the unit tests in test/"
	@echo
	@echo -e "  $(BLUE)convert-apparatus-israels$(RESET)  - convert the israels apparatus files"
	@echo -e "  $(BLUE)convert-apparatus-van-gogh$(RESET) - convert the van-gogh apparatus files"
	@echo
	@echo -e "  $(BLUE)version-update-patch$(RESET)  - to update the project version to the next patch version"
	@echo -e "  $(BLUE)version-update-minor$(RESET)  - to update the project version to the next minor version"
	@echo -e "  $(BLUE)version-update-major$(RESET)  - to update the project version to the next major version"
