# Changelog

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
