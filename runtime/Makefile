POETRY := $(shell poetry --version)

.PHONY: target install format lint unit-test pr build

target:
	@$(MAKE) pr

install:
ifndef POETRY
	pip install --upgrade pip poetry
	poetry install
else
	$(info a version for poetry was found $(POETRY).)
	$(info poetry install packages.)
	poetry install
endif


format:
	poetry run isort .
	poetry run black .

lint: install format
# python3
	poetry run flake8
# one api

integ-test: install
	poetry run pytest tests/integ

unit-test:
	poetry run pytest tests/unit
	
pr: lint #unit-test

build: pr
	poetry build