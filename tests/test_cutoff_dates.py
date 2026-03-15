from datetime import date

from src.core.league import BaseLeague
from src.core.models import GameResult


class DummyLeague(BaseLeague):
    def fetch_games(self, season):
        return [], []

    def build_team_records(self, games):
        return []

    def actual_scores(self, game, win_weights):
        return 0.0, 0.0

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


def _game(game_id, game_date):
    return GameResult(
        game_id=game_id,
        game_date=game_date,
        away_team="A",
        home_team="B",
        away_score=1,
        home_score=0,
        last_period_type="REG",
    )


def test_sorted_unique_game_dates_supports_date_and_datetime_strings():
    league = DummyLeague()
    games = [
        _game("g3", "2026-01-03T19:00:00Z"),
        _game("g1", "2026-01-05"),
        _game("g2", "2026-01-03T12:00:00+00:00"),
    ]

    dates = league.sorted_unique_game_dates(games)

    assert dates == [date(2026, 1, 3), date(2026, 1, 5)]


def test_split_games_by_cutoff_is_inclusive_and_sorted():
    league = DummyLeague()
    games = [
        _game("g4", "2026-01-04T10:00:00Z"),
        _game("g1", "2026-01-01"),
        _game("g3", "2026-01-03T20:00:00Z"),
        _game("g2", "2026-01-03T08:00:00Z"),
    ]

    on_or_before, after = league.split_games_by_cutoff(games, date(2026, 1, 3))

    assert [g.game_id for g in on_or_before] == ["g1", "g2", "g3"]
    assert [g.game_id for g in after] == ["g4"]


def test_split_games_by_cutoff_none_returns_all_sorted():
    league = DummyLeague()
    games = [
        _game("g3", "2026-01-03"),
        _game("g1", "2026-01-01"),
        _game("g2", "2026-01-02"),
    ]

    ordered, after = league.split_games_by_cutoff(games, None)

    assert [g.game_id for g in ordered] == ["g1", "g2", "g3"]
    assert after == []
