from src.core.league import BaseLeague
from src.tools.analytics import compare_elo_vs_standings


class DummyLeague(BaseLeague):
    def fetch_games(self, season):
        return [], []

    def build_team_records(self, games):
        return [
            {
                "team": "A",
                "standings_rank": 1,
                "conference": "Test",
                "division": "One",
                "Pts": 10,
                "GP": 5,
                "W": 5,
                "OTW": 0,
                "L": 0,
                "OTL": 0,
            },
            {
                "team": "B",
                "standings_rank": 2,
                "conference": "Test",
                "division": "One",
                "Pts": 8,
                "GP": 5,
                "W": 4,
                "OTW": 0,
                "L": 1,
                "OTL": 0,
            },
        ]

    def actual_scores(self, game, win_weights):
        return 0.0, 1.0

    def get_teams(self):
        return ["A", "B"]

    def team_info(self):
        return {
            "A": {"conference": "Test", "division": "One"},
            "B": {"conference": "Test", "division": "One"},
        }

    def simulate_playoffs(self, records, ratings, simulations, rng, **kwargs):
        return []

    def apply_simulated_game_to_records(self, records, away_team, home_team, away_score, home_score, finish_type):
        return None

    def sample_score(self, finish_type, rng, home_wins):
        return 1, 0

    def estimate_finish_type_probabilities(self, completed_games):
        return {"REG": 1.0, "OT": 0.0, "SO": 0.0}


def _row(rows, team):
    for row in rows:
        if row["team"] == team:
            return row
    raise AssertionError(f"Team {team} not found")


def test_trend_uses_last_10_games_window_when_available():
    league = DummyLeague()
    ratings = {"A": 1200.0, "B": 1100.0}
    team_history = {
        "A": [("START", 1000.0)] + [(f"g{i}", 1000.0 + i) for i in range(1, 13)],
        "B": [("START", 1000.0)] + [(f"g{i}", 1000.0) for i in range(1, 13)],
    }

    rows = compare_elo_vs_standings(league, ratings, [], team_history)

    # Current 1012.0 minus value 10 games ago 1002.0 => +10.0
    assert _row(rows, "A")["elo_trend_10g"] == 10.0


def test_trend_fallback_for_fewer_than_10_games():
    league = DummyLeague()
    ratings = {"A": 1050.0, "B": 1010.0}
    team_history = {
        "A": [
            ("START", 1000.0),
            ("g1", 1002.0),
            ("g2", 1004.0),
            ("g3", 1007.0),
            ("g4", 1010.0),
        ],
        "B": [("START", 1000.0), ("g1", 1001.0)],
    }

    rows = compare_elo_vs_standings(league, ratings, [], team_history)

    # Fewer than 10 games => current minus first post-START entry.
    assert _row(rows, "A")["elo_trend_10g"] == 8.0


def test_trend_is_zero_when_team_has_no_games():
    league = DummyLeague()
    ratings = {"A": 1000.0, "B": 1000.0}
    team_history = {
        "A": [("START", 1000.0)],
        "B": [("START", 1000.0)],
    }

    rows = compare_elo_vs_standings(league, ratings, [], team_history)

    assert _row(rows, "A")["elo_trend_10g"] == 0.0
    assert _row(rows, "B")["elo_trend_10g"] == 0.0
