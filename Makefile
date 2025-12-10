.PHONY: test lint type-check run

# run unit tests
test:
	PYTHONPATH=. pytest

# linter (ruff)
lint:
	PYTHONPATH=. ruff check app tests

# static types (mypy)
type-check:
	PYTHONPATH=. mypy app

# run the app
run:
	PYTHONPATH=. python -m app.cmd.main

# build example Excel report
excel:
	PYTHONPATH=. python -m app.cmd.build_example_excel