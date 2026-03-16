import pytest

from src.core.league import BaseLeague
from src.core.models import GameResult
from src.tools.analytics import estimate_home_ice_advantage


class DummyLeague(BaseLeague):
    def __init__(self):
        self._teams = ["A", "B"]

    def fetch_games(self, season):
        raise NotImplementedError()

    def build_team_records(self, games):
        return []

    def actual_scores(self, game, win_weights):
        if game.last_period_type == "OT":
            w, l = win_weights["OT_WIN"], win_weights["OT_LOSS"]
        elif game.last_period_type == "SO":
            w, l = win_weights["SO_WIN"], win_weights["SO_LOSS"]
        else:
            w, l = win_weights["REG_WIN"], win_weights["REG_LOSS"]

        if game.away_score > game.home_score:
            return w, l
        return l, w

    def get_teams(self):
        return self._teams

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
        if home_wins:
            return 1, 2
        return 2, 1

    def estimate_finish_type_probabilities(self, completed_games):
        return {"REG": 1.0, "OT": 0.0, "SO": 0.0}


def make_game(game_id: int, home_wins: bool) -> GameResult:
    away_team = "A" if game_id % 2 == 0 else "B"
    home_team = "B" if game_id % 2 == 0 else "A"
    away_score, home_score = (1, 3) if home_wins else (3, 1)
    return GameResult(
        game_id=f"g{game_id}",
        game_date=f"2026-01-{(game_id % 28) + 1:02d}",
        away_team=away_team,
        home_team=home_team,
        away_score=away_score,
        home_score=home_score,
        last_period_type="REG",
    )


def test_estimate_home_ice_advantage_detects_positive_edge():
    league = DummyLeague()
    games = [make_game(i, home_wins=(i % 10) < 7) for i in range(1, 201)]
    win_weights = {
        "REG_WIN": 1.0,
        "REG_LOSS": 0.0,
        "OT_WIN": 0.67,
        "OT_LOSS": 0.33,
        "SO_WIN": 0.55,
        "SO_LOSS": 0.45,
    }

    estimate, objective = estimate_home_ice_advantage(
        league=league,
        games=games,
        win_weights=win_weights,
        initial_elo=1500.0,
        k_factor=20.0,
        search_min=0.0,
        search_max=120.0,
    )

    assert estimate > 5.0
    assert objective >= 0.0


def test_estimate_home_ice_advantage_handles_balanced_results_near_zero():
    league = DummyLeague()
    games = [make_game(i, home_wins=(i % 2 == 0)) for i in range(1, 201)]
    win_weights = {
        "REG_WIN": 1.0,
        "REG_LOSS": 0.0,
        "OT_WIN": 0.67,
        "OT_LOSS": 0.33,
        "SO_WIN": 0.55,
        "SO_LOSS": 0.45,
    }

    estimate, _ = estimate_home_ice_advantage(
        league=league,
        games=games,
        win_weights=win_weights,
        initial_elo=1500.0,
        k_factor=20.0,
        search_min=0.0,
        search_max=120.0,
    )

    assert estimate <= 20.0


def test_estimate_home_ice_advantage_raises_on_empty_games():
    league = DummyLeague()
    win_weights = {
        "REG_WIN": 1.0,
        "REG_LOSS": 0.0,
        "OT_WIN": 0.67,
        "OT_LOSS": 0.33,
        "SO_WIN": 0.55,
        "SO_LOSS": 0.45,
    }

    with pytest.raises(ValueError):
        estimate_home_ice_advantage(
            league=league,
            games=[],
            win_weights=win_weights,
            initial_elo=1500.0,
            k_factor=20.0,
        )
