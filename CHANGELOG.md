# Changelog

## [0.3.2] - 2026-03-17

### Added

- New in-app `Help` tab with quick-start guidance, glossary, tab explanations, and league-specific playoff terminology
- Inline help text/tooltips for key controls and simulation columns to improve first-time user onboarding

### Changed

- Standardized and clarified UI terminology across the dashboard for consistency (ratings, simulations, cutoff mode, and matrix language)
- Updated NHL and SHL playoff stage labels for clearer interpretation (SHL retains Swedish terms with English clarifiers)
- Expanded `README.md` with aligned terminology and practical documentation for tabs, parameters, what-if mode, and simulation outputs

## [0.3.1] - 2026-03-17

### Changed

- Updated default Elo tuning values in app and CLI:
	- Base K: 20
	- Placement Games: 10
	- Placement K Add: 10
	- Home Ice Advantage: 42

## [0.3.0] - 2026-03-17

### Added

- Placement-phase K controls in the Streamlit app: `Placement Games` and `Placement K Add`
- CLI flags for placement-phase K tuning: `--placement-games` and `--placement-k-add`
- Placement-K regression coverage across historical Elo, simulation path, and home-ice estimator path

### Changed

- Elo updates now support a per-match placement boost rule: if either team is still within its first X games, the game uses `base_k + placement_k_add`
- Season simulations now apply the same placement-K rule to regular-season simulated games
- Home-ice estimator calibration now uses the same placement-K rule for consistency with ratings and simulations
- Streamlit simulation cache schema bumped to avoid stale cache collisions with placement-K-enhanced results

## [0.2.5] - 2026-03-16

### Added

- Simulation output now includes average final regular-season points per team (`Final Pts (avg)`) in the app table

### Changed

- Simulations table now keeps `Final Pts (avg)` numeric so the column can be sorted directly in the UI
- Added backward-compatible handling for older cached simulation payloads that do not include `final_points_avg`
- Bumped simulation cache schema key to invalidate stale cached results after the new output field addition

## [0.2.4] - 2026-03-16

### Added

- SHL game-type tagging (`REG` vs `PLAYOFF`) in fetched schedule data
- SHL playoff regression tests covering top-6 direct quarterfinal qualification, 7-10 play-in behavior, and standings exclusion of playoff games
- Simulator regression test ensuring non-regular remaining games are skipped in season simulation

### Changed

- SHL standings now count only regular-season games for seeding purposes
- SHL playoff bracket is now explicitly hardcoded to: top-6 direct to quarterfinals, 7v10 and 8v9 play-in, then reseeding by highest-vs-lowest seed each round
- Simulation table playoff probabilities now remain numeric in the app grid so sorting behaves correctly (no string-based percent sorting issues)
- SHL simulation table display now shows 100% in the first-stage column for teams already guaranteed quarterfinal participation
- Streamlit cache keys were refreshed for game fetch and simulation outputs to avoid stale pre-fix SHL results

## [0.2.3] - 2026-03-16

### Added

- Current Ratings now includes `ELO Trend (10g)` based on Elo change over each team's last 10 completed games
- Unit tests for Elo trend column behavior across >=10 games, <10 games fallback, and no-games edge cases

### Changed

- Elo trend values now stay numeric in the table and use signed display formatting, so sorting works numerically instead of alphabetically
- CLI comparison generation now receives team history so trend data is available consistently across app and CLI paths

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
