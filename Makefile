.PHONY: install lint test ci

install:
	python3 -m pip install -e ".[dev]"

lint:
	python3 -m ruff check src tests

test:
	python3 -m pytest

ci: lint test
