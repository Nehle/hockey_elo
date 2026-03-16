from src.core.league import BaseLeague
from src.core.models import GameResult
from src.tools import simulator as simulator_mod


class TrackingLeague(BaseLeague):
    def __init__(self):
        self._teams = ["A", "B"]
        self.last_playoff_kwargs = {}

    def fetch_games(self, season):
        raise NotImplementedError()

    def build_team_records(self, games):
        return [{"team": "A"}, {"team": "B"}]

    def actual_scores(self, game, win_weights):
        if game.away_score > game.home_score:
            return win_weights["REG_WIN"], win_weights["REG_LOSS"]
        return win_weights["REG_LOSS"], win_weights["REG_WIN"]

    def get_teams(self):
        return self._teams

    def team_info(self):
        return {
            "A": {"conference": "Test", "division": "One"},
            "B": {"conference": "Test", "division": "One"},
        }

    def simulate_playoffs(self, records, ratings, simulations, rng, **kwargs):
        self.last_playoff_kwargs = dict(kwargs)
        return [
            {"team": "A", "made_playoffs": 1, "make_qf": 1, "make_sf": 0, "make_final": 0, "win_champ": 0},
            {"team": "B", "made_playoffs": 1, "make_qf": 1, "make_sf": 0, "make_final": 0, "win_champ": 0},
        ]

    def apply_simulated_game_to_records(self, records, away_team, home_team, away_score, home_score, finish_type):
        return None

    def sample_score(self, finish_type, rng, home_wins):
        if home_wins:
            return 1, 2
        return 2, 1

    def estimate_finish_type_probabilities(self, completed_games):
        return {"REG": 1.0, "OT": 0.0, "SO": 0.0}


def test_simulator_forwards_mov_to_update_and_playoffs(monkeypatch):
    league = TrackingLeague()
    calls = []

    def fake_update_elo(
        away_elo,
        home_elo,
        away_actual,
        home_actual,
        k,
        home_ice_advantage,
        use_mov=False,
        mov_cap=5,
        away_goals=0,
        home_goals=0,
    ):
        calls.append(
            {
                "use_mov": use_mov,
                "mov_cap": mov_cap,
                "away_goals": away_goals,
                "home_goals": home_goals,
            }
        )
        return away_elo, home_elo

    monkeypatch.setattr(simulator_mod, "update_elo", fake_update_elo)

    game = GameResult(
        game_id="future-1",
        game_date="2026-03-14",
        away_team="A",
        home_team="B",
        away_score=0,
        home_score=0,
        last_period_type="REG",
    )

    result = simulator_mod.simulate_season_and_playoffs_from_today(
        league=league,
        completed_games=[],
        remaining_games=[game],
        current_ratings={"A": 1500.0, "B": 1500.0},
        simulations=1,
        home_ice_advantage=33.0,
        k_factor=20.0,
        win_weights={"REG_WIN": 1.0, "REG_LOSS": 0.0, "OT_WIN": 0.67, "OT_LOSS": 0.33, "SO_WIN": 0.55, "SO_LOSS": 0.45},
        use_mov=True,
        mov_cap=7,
        seed=7,
    )

    assert len(result) == 2
    assert calls, "Expected regular-season Elo updates to be called at least once"
    assert calls[0]["use_mov"] is True
    assert calls[0]["mov_cap"] == 7
    assert league.last_playoff_kwargs.get("use_mov") is True
    assert league.last_playoff_kwargs.get("mov_cap") == 7


def test_simulator_skips_non_regular_remaining_games(monkeypatch):
    league = TrackingLeague()
    calls = []

    def fake_update_elo(
        away_elo,
        home_elo,
        away_actual,
        home_actual,
        k,
        home_ice_advantage,
        use_mov=False,
        mov_cap=5,
        away_goals=0,
        home_goals=0,
    ):
        calls.append((away_elo, home_elo))
        return away_elo, home_elo

    monkeypatch.setattr(simulator_mod, "update_elo", fake_update_elo)

    playoff_game = GameResult(
        game_id="future-playoff-1",
        game_date="2026-03-20",
        away_team="A",
        home_team="B",
        away_score=0,
        home_score=0,
        last_period_type="REG",
        game_type="PLAYOFF",
    )

    result = simulator_mod.simulate_season_and_playoffs_from_today(
        league=league,
        completed_games=[],
        remaining_games=[playoff_game],
        current_ratings={"A": 1500.0, "B": 1500.0},
        simulations=1,
        home_ice_advantage=33.0,
        k_factor=20.0,
        win_weights={"REG_WIN": 1.0, "REG_LOSS": 0.0, "OT_WIN": 0.67, "OT_LOSS": 0.33, "SO_WIN": 0.55, "SO_LOSS": 0.45},
        seed=7,
    )

    assert len(result) == 2
    assert calls == []
