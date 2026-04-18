.PHONY: requirements clean data build lint format help

#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PROJECT_NAME = solar
PYTHON_INTERPRETER ?= python

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Install Python Dependencies
requirements:
	$(PYTHON_INTERPRETER) -m pip install -e .

## Delete all compiled Python files
clean:
	$(PYTHON_INTERPRETER) -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"

## Lint using flake8
lint:
	flake8 src tests

## Format codebase using black
format:
	black src tests

## Build the project (placeholder)
build:
	@echo "Build process not yet defined."

## Process data (placeholder)
data:
	@echo "Data processing not yet defined."

#################################################################################
# PROJECT RULES                                                                 #
#################################################################################

help:
	@echo "Available commands:"
	@echo "  requirements : Install project dependencies"
	@echo "  clean        : Remove temporary python files"
	@echo "  lint         : Run flake8 checks"
	@echo "  format       : Run black formatter"
	@echo "  build        : Build the project"
	@echo "  data         : Run data processing"
