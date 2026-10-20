# Contributing

Thanks for your interest in contributing.

## Development Setup

```bash
uv sync
```

## Running Locally

Dashboard:

```bash
uv run streamlit run app.py
```

CLI:

```bash
uv run python cli.py --league NHL --season 20252026 --sims 200
```

## Tests

```bash
uv run pytest
```

Optional network smoke tests:

```bash
RUN_NETWORK_TESTS=1 uv run pytest -m network
```

Convenience target:

```bash
make check
```

Manual diagnostics (non-CI scripts):

```bash
uv run python scripts/manual/test_shl.py
uv run python scripts/manual/test_nhl_ari.py
```

## Pull Requests

- Keep changes focused and small when possible.
- Include tests for new logic and regressions.
- Update docs when behavior or workflow changes.
- Avoid committing generated artifacts or local debug outputs.
