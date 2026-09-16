.PHONY: install lint test ci pages

install:
	python3 -m pip install -e ".[dev]"

lint:
	python3 -m ruff check src tests

test:
	python3 -m pytest

ci: lint test

# Public docs site (GitHub Pages artifact under build/pages). Stdlib only.
# Preview: python3 -m http.server --directory build/pages 8080
pages:
	python3 scripts/build_pages.py
