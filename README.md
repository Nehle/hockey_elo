# nhlelo

Elo ratings, standings analytics, and playoff probability simulations for NHL and SHL.

## Features

- Historical Elo calculation with configurable:
  - Initial Elo
  - K-factor
  - Home-ice advantage
  - OT/SO score weights
- Optional Margin of Victory (MoV) multiplier with configurable goal-differential cap
- Streamlit dashboard for interactive analysis
- CLI workflow for batch exports and image reports
- League-specific playoff simulation structures (NHL and SHL)

## Quickstart

### 1. Create environment and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the dashboard

```bash
streamlit run app.py
```

### 3. Run CLI mode

```bash
python cli.py --league NHL --season 20252026 --sims 1000
```

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Run opt-in network smoke tests:

```bash
RUN_NETWORK_TESTS=1 pytest -m network
```

Or use Makefile shortcuts:

```bash
make check
make run-app
```

Manual diagnostic scripts:

```bash
python scripts/manual/test_shl_full.py
python scripts/manual/test_nhl.py
```

## MoV Status

MoV support is available and configurable. For release quality, treat it as experimental until all propagation and behavior tests are green in CI.

Current scope:

- MoV affects Elo updates for historical games.
- MoV affects Elo updates for simulated regular-season games.
- Playoff series simulation currently uses Elo win probabilities per game and does not apply a score-differential multiplier inside playoff games.

## Generated Outputs Policy

Generated CSV/PNG/debug outputs are intentionally not tracked in git. Recreate them locally via the app or CLI as needed.

## Scripts Layout

- scripts/manual: ad-hoc diagnostics and API sanity checks.
- scripts/maintenance: one-off migration and repair helpers used during development.

## Data Sources

- NHL API endpoints
- SHL API endpoints

Please ensure your use complies with each provider's terms.

## License

MIT. See LICENSE.
