.PHONY: setup run test lint typecheck

setup:
	python -m pip install -e '.[dev]'

run:
	python run.py

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy kernel agents run.py
