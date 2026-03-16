import random

from src.leagues.shl.league import SHLLeague
from src.core.models import GameResult


def _make_records_and_ratings():
    teams = [f"T{i}" for i in range(1, 15)]
    records = []
    ratings = {}

    for idx, team in enumerate(teams):
        records.append(
            {
                "team": team,
                "Pts": 100 - idx,
                "W": 40 - idx,
                "OTW": 0,
                "OTL": 0,
                "L": 0,
                "GP": 52,
                "conference": "SHL",
                "division": "SHL",
            }
        )
        ratings[team] = 1500.0

    return teams, records, ratings


def test_shl_top_six_have_guaranteed_qf_and_playin_is_7_to_10_only():
    teams, records, ratings = _make_records_and_ratings()
    league = SHLLeague()

    out = league.simulate_playoffs(records, ratings, simulations=200, rng=random.Random(7), home_ice_advantage=33.0)
    by_team = {row["team"]: row for row in out}

    top_six = teams[:6]
    seeds_7_to_10 = teams[6:10]
    outside_top_ten = teams[10:]

    for team in top_six:
        assert by_team[team]["make_qf"] == 1.0
        assert by_team[team]["made_playoffs"] == 0

    for team in seeds_7_to_10:
        assert by_team[team]["made_playoffs"] == 1

    for team in outside_top_ten:
        assert by_team[team]["make_qf"] == 0.0

    # Round participant count invariants per simulation: 8 QF, 4 SF, 2 Final, 1 Champion.
    assert sum(row["make_qf"] for row in out) == 8.0
    assert sum(row["make_sf"] for row in out) == 4.0
    assert sum(row["make_final"] for row in out) == 2.0
    assert sum(row["win_champ"] for row in out) == 1.0


def test_shl_records_ignore_playoff_games():
    league = SHLLeague()
    league._teams = ["A", "B"]
    league._team_info = {
        "A": {"conference": "SHL", "division": "SHL"},
        "B": {"conference": "SHL", "division": "SHL"},
    }

    reg_game = GameResult(
        game_id="reg-1",
        game_date="2026-03-01",
        away_team="B",
        home_team="A",
        away_score=1,
        home_score=3,
        last_period_type="REG",
        game_type="REG",
    )
    playoff_game = GameResult(
        game_id="po-1",
        game_date="2026-03-10",
        away_team="B",
        home_team="A",
        away_score=0,
        home_score=4,
        last_period_type="REG",
        game_type="PLAYOFF",
    )

    records = league.build_team_records([reg_game, playoff_game])
    by_team = {row["team"]: row for row in records}

    assert by_team["A"]["Pts"] == 3
    assert by_team["A"]["GP"] == 1
    assert by_team["B"]["Pts"] == 0
    assert by_team["B"]["GP"] == 1
