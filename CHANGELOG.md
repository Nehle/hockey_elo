# Changelog

## [0.2.2] - 2026-03-16

### Added

- Sidebar button to estimate home ice advantage from the current active data scope
- Home-ice estimator utility with coarse/fine grid-search calibration against completed games
- Unit tests for home-ice estimator behavior and empty-input safeguards

### Changed

- Base ELO is now fixed to 1000 in the Streamlit app (removed configurable initial ELO control)
- Interdivision heatmap now displays percentage values directly (0-100%) instead of fractions
- Home-ice estimate button now updates slider value through safe deferred session-state flow

## [0.2.0] - 2026-03-15

### Added

- Date-cutoff what-if mode in the Streamlit app
- Sidebar controls to enable cutoff mode and pick an inclusive cutoff date
- Shared league date helpers for parsing, sorting, and splitting games by cutoff
- Unit tests for date normalization and inclusive cutoff splitting behavior

### Changed

- Ratings and all analytics tabs now use games up to the selected cutoff date in what-if mode
- Simulations now seed from cutoff ratings and simulate games after the selected cutoff date in what-if mode


## [0.1.0] - 2026-03-13

### Added

- NHL/SHL Elo rating engine with optional Margin-of-Victory multiplier
- Streamlit dashboard with MoV toggle and MoV-cap slider
- CLI reporting workflow with standings, projections, and chart export
- NHL and SHL playoff simulation framework (Monte Carlo)
- `pyproject.toml` packaging metadata and editorconfig
- `requirements-dev.txt` for development/test dependencies
- `pytest` unit tests: Elo math, MoV cap, MoV propagation through simulator
- GitHub Actions CI matrix (Python 3.10 / 3.11 / 3.12)
- `Makefile` developer shortcuts (`make check`, `make test`, `make run-app`, …)
- MIT `LICENSE`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `DATA_POLICY.md`
- `scripts/manual/` and `scripts/maintenance/` organisation for ad-hoc helper scripts

### Notes

- MoV multiplier currently applies to historical and regular-season simulated Elo updates only; playoff game simulation uses win-probability per game without score-differential weighting.
