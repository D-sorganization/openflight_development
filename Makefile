.PHONY: test test-ui test-all lint format dev build-ui start install hooks

## Run Python tests
test:
	uv run pytest tests/ -v

## Run UI unit tests
test-ui:
	cd ui && npm test

## Run all tests (Python + UI)
test-all:
	uv run pytest tests/ -v
	cd ui && npm test

## Run all linters (Python + UI)
lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run pylint src/openflight/ --fail-under=9
	cd ui && npm run lint

## Auto-format Python code
format:
	uv run ruff format .
	uv run ruff check --fix .

## Start server in mock mode (no hardware needed)
dev:
	scripts/start-kiosk.sh --mock

## Build the React UI
build-ui:
	cd ui && npm install && npm run build

## Start the full application (requires hardware)
start:
	scripts/start-kiosk.sh

## Install all dependencies (Python + UI)
install:
	uv sync --group dev
	cd ui && npm install

## Install pre-commit hooks
hooks:
	uv run pre-commit install
