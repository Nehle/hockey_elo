.PHONY: install install-dev test test-network check run-app run-cli

install:
	python -m pip install -r requirements.txt

install-dev:
	python -m pip install -r requirements-dev.txt

test:
	pytest

test-network:
	RUN_NETWORK_TESTS=1 pytest -m network

check:
	python -m compileall -q app.py cli.py src tests scripts
	pytest

run-app:
	streamlit run app.py

run-cli:
	python cli.py --league NHL --season 20252026 --sims 1000
