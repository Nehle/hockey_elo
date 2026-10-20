.PHONY: install install-dev test test-network check run-app run-cli

install:
	uv sync --no-dev

install-dev:
	uv sync

test:
	uv run pytest

test-network:
	RUN_NETWORK_TESTS=1 uv run pytest -m network

check:
	uv run python -m compileall -q app.py cli.py src tests scripts
	uv run pytest

run-app:
	uv run streamlit run app.py

run-cli:
	uv run python cli.py --league NHL --season 20252026 --sims 1000
