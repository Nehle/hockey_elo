# nhlelo

Elo ratings, standings analytics, and playoff probability simulations for NHL and SHL.

## Features

- Historical Elo calculation with configurable:
  - K-Factor
  - Home Ice Advantage
  - OT/SO score weights
- Placement-phase K controls for early-season volatility:
  - Placement Games
  - Placement K Add (bonus added to base K)
- Optional Margin of Victory (MoV) multiplier with configurable goal-differential cap
- Streamlit dashboard for interactive analysis
- CLI workflow for batch exports and image reports
- Date-cutoff what-if mode for historical snapshots
- Home-ice estimator calibrated from historical games
- League-specific playoff simulation structures (NHL and SHL)

## Dashboard Guide

### Tabs at a Glance

- Current Ratings: Compare Elo rank, standings rank, trend, and records.
- Elo History: Team Elo trajectories over time.
- Elo vs Standings: Visual alignment between standings and Elo rank.
- Simulations: Expected final points and playoff/championship probabilities.
- Interdivision Matrix: Division-vs-division Elo-style score percentages.
- Help: Built-in glossary and usage guidance for first-time users.

### Core Terms

- Elo: Rating system updated after each game.
- K-Factor: How quickly ratings move; higher means more reactive ratings.
- Placement Games / Placement K Add: Early-season K bonus. If either team is still in placement games, that matchup uses base K + bonus.
- Home Ice Advantage (Elo points): Rating bonus applied to the home team for win-probability calculations.
- OTW/SOW Weights: How Elo credit is split for overtime/shootout games.
- MoV Multiplier: Optional goal-differential scaling for regular-season Elo updates.

### Simulations Output

- Expected Final Points: Average regular-season points across simulation runs.
- Playoff columns: Probability of reaching each stage.
- SHL labels keep Swedish names with English clarifiers.

### What-If Mode (Date Cutoff)

Enable Historical Data Cutoff in the sidebar to freeze ratings/analytics at a selected date.
Simulations then run only on games after that date.

### Home-Ice Estimator

Use Estimate Home Ice From Data in the sidebar to calibrate the Home Ice Advantage value from completed games.
The app updates the slider using the value that best fits observed outcomes.

## Playoff Structures

### NHL

- Standard NHL bracket progression ending in Stanley Cup Finals.

### SHL

- Top 6 teams go directly to Kvartsfinal (Quarterfinals).
- Seeds 7-10 play Åttondelsfinal (Play-in).
- Bracket reseeds by highest remaining seed vs lowest remaining seed each round.

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
