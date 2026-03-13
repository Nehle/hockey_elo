# Contributing

Thanks for your interest in contributing.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Running Locally

Dashboard:

```bash
streamlit run app.py
```

CLI:

```bash
python cli.py --league NHL --season 20252026 --sims 200
```

## Tests

```bash
pytest
```

Optional network smoke tests:

```bash
RUN_NETWORK_TESTS=1 pytest -m network
```

Convenience target:

```bash
make check
```

Manual diagnostics (non-CI scripts):

```bash
python scripts/manual/test_shl.py
python scripts/manual/test_nhl_ari.py
```

## Pull Requests

- Keep changes focused and small when possible.
- Include tests for new logic and regressions.
- Update docs when behavior or workflow changes.
- Avoid committing generated artifacts or local debug outputs.
