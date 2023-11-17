## es7s/commons         ##
## (c) 2023             ## A. Shavykin <<0.delameter@gmail.com>>
##----------------------##-------------------------------------------------------------

.ONESHELL:
.PHONY: help test

VERSION_FILE_PATH ?= es7s_commons/_version.py

#include $(ENV_DIST_FILE_PATH)
#-include $(ENV_LOCAL_FILE_PATH)
#export

NOW    := $(shell LC_TIME=en_US.UTF-8 date --rfc-3339=seconds)
BOLD   := $(shell tput -Txterm bold)
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
BLUE   := $(shell tput -Txterm setaf 4)
CYAN   := $(shell tput -Txterm setaf 6)
GRAY   := $(shell tput -Txterm setaf 7)
DIM    := $(shell tput -Txterm dim)
RESET  := $(shell printf '\e[m')
                                # tput -Txterm sgr0 returns SGR-0 with
                                # nF code switching esq, which displaces the columns
## Common

help:   ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v @fgrep | sed -Ee 's/^(##)\s?(\s*#?[^#]+)#*\s*(.*)/\1${YELLOW}\2${RESET}#\3/; s/(.+):(#|\s)+(.+)/##   ${GREEN}\1${RESET}#\3/; s/\*(\w+)\*/${BOLD}\1${RESET}/g; 2~1s/<([ )*<@>.A-Za-z0-9_(-]+)>/${DIM}\1${RESET}/gi' -e 's/(\x1b\[)33m#/\136m/' | column -ts# | sed -Ee 's/ {3}>/ >/'

.:
## Packaging

show-version: ## Show current package version
	@hatch version | sed -Ee "s/.+/Current: ${CYAN}&${RESET}/"

tag-version: ## Tag current git branch HEAD with the current version
	@git tag $(shell hatch version | cut -f1-3  -d\.) && git log -1

_set_next_version = (hatch version $1 | tr -d '\n' | sed -zEe "s/(Old:\s*)(\S+)(New:\s*)(\S+)/Version updated:\n${CYAN} \2${RESET} -> ${YELLOW}\4${RESET}/")
_set_current_date = (sed ${VERSION_FILE_PATH} -i -Ee 's/^(__updated__).+/\1 = "${NOW}"/w/dev/stdout' | cut -f2 -d'"')

next-version-micro: ## Increase version by 0.0.1
	@$(call _set_current_date)
	@$(call _set_next_version,micro | head -2)
	@echo

next-version-minor: ## Increase version by 0.1
	@$(call _set_current_date)
	@$(call _set_next_version,minor | head -2)
	@echo

next-version-major: ## Increase version by 1
	@$(call _set_current_date)
	@$(call _set_next_version,major | head -2)
	@echo

.:
## Building / Publishing

_freeze = (	echo "${BSEP}\e[34mFreezing \e[1;94m$1\e[22;34m:\e[m\n${BSEP}"; \
			hatch -e $1 run pip freeze -q --exclude-editable | \
				sed --unbuffered -E -e '/^(Checking|Syncing|Creating|Installing)/d' | \
				tee requirements.txt | \
				sed --unbuffered -E -e 's/^([a-zA-Z0-9_-]+)/\x1b[32m\1\x1b[m/' \
									-e 's/([0-9.]+|@[a-zA-Z0-9_-]+)$$/\x1b[33m\1\x1b[m/'; \
			echo)

freeze:  ## Update requirements.txt   <hatch>
	@$(call _freeze,default)

demolish-build:  ## Delete build output folders  <hatch>
	hatch clean

build:  ## Build a package   <hatch>
build: demolish-build
	hatch build

publish:  ## Upload last build    <hatch>
	hatch publish
