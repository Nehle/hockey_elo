from src.core.elo import calculate_elo, expected_score, update_elo
from src.core.league import BaseLeague
from src.core.models import GameResult
import src.core.elo as elo_mod


class DummyLeague(BaseLeague):
    def __init__(self):
        self._teams = ["A", "B"]

    def fetch_games(self, season):
        raise NotImplementedError()

    def build_team_records(self, games):
        return [{"team": team} for team in self._teams]

    def actual_scores(self, game, win_weights):
        finish_type = game.last_period_type
        if finish_type == "OT":
            w, l = win_weights["OT_WIN"], win_weights["OT_LOSS"]
        elif finish_type == "SO":
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
        return [
            {"team": "A", "made_playoffs": 0, "make_qf": 0, "make_sf": 0, "make_final": 0, "win_champ": 0},
            {"team": "B", "made_playoffs": 0, "make_qf": 0, "make_sf": 0, "make_final": 0, "win_champ": 0},
        ]

    def apply_simulated_game_to_records(self, records, away_team, home_team, away_score, home_score, finish_type):
        return None

    def sample_score(self, finish_type, rng, home_wins):
        if home_wins:
            return 1, 3
        return 3, 1

    def estimate_finish_type_probabilities(self, completed_games):
        return {"REG": 1.0, "OT": 0.0, "SO": 0.0}


def test_expected_score_is_complementary():
    p_a = expected_score(1600.0, 1500.0)
    p_b = expected_score(1500.0, 1600.0)
    assert abs((p_a + p_b) - 1.0) < 1e-12


def test_update_elo_home_ice_reduces_home_gain_when_home_wins():
    _, home_no_ice = update_elo(
        away_elo=1500.0,
        home_elo=1500.0,
        away_actual=0.0,
        home_actual=1.0,
        k=20.0,
        home_ice_advantage=0.0,
    )
    _, home_with_ice = update_elo(
        away_elo=1500.0,
        home_elo=1500.0,
        away_actual=0.0,
        home_actual=1.0,
        k=20.0,
        home_ice_advantage=50.0,
    )
    assert (home_with_ice - 1500.0) < (home_no_ice - 1500.0)


def test_mov_cap_limits_effect_size():
    _, home_low_cap = update_elo(
        away_elo=1500.0,
        home_elo=1500.0,
        away_actual=0.0,
        home_actual=1.0,
        k=20.0,
        home_ice_advantage=0.0,
        use_mov=True,
        mov_cap=1,
        away_goals=1,
        home_goals=8,
    )
    _, home_high_cap = update_elo(
        away_elo=1500.0,
        home_elo=1500.0,
        away_actual=0.0,
        home_actual=1.0,
        k=20.0,
        home_ice_advantage=0.0,
        use_mov=True,
        mov_cap=5,
        away_goals=1,
        home_goals=8,
    )
    assert (home_high_cap - 1500.0) > (home_low_cap - 1500.0)


def test_calculate_elo_responds_to_mov_toggle():
    league = DummyLeague()
    game = GameResult(
        game_id="g1",
        game_date="2026-03-13",
        away_team="A",
        home_team="B",
        away_score=1,
        home_score=6,
        last_period_type="REG",
    )
    weights = {
        "REG_WIN": 1.0,
        "REG_LOSS": 0.0,
        "OT_WIN": 0.67,
        "OT_LOSS": 0.33,
        "SO_WIN": 0.55,
        "SO_LOSS": 0.45,
    }

    ratings_plain, _, _ = calculate_elo(
        league=league,
        games=[game],
        initial_elo=1500.0,
        k_factor=20.0,
        home_ice_advantage=0.0,
        win_weights=weights,
        use_mov=False,
        mov_cap=5,
    )
    ratings_mov, _, _ = calculate_elo(
        league=league,
        games=[game],
        initial_elo=1500.0,
        k_factor=20.0,
        home_ice_advantage=0.0,
        win_weights=weights,
        use_mov=True,
        mov_cap=5,
    )

    assert ratings_mov["B"] > ratings_plain["B"]


def test_calculate_elo_placement_k_boost_uses_or_rule_and_expires(monkeypatch):
    class PlacementLeague(DummyLeague):
        def __init__(self):
            self._teams = ["A", "B", "C"]

        def team_info(self):
            return {
                "A": {"conference": "Test", "division": "One"},
                "B": {"conference": "Test", "division": "One"},
                "C": {"conference": "Test", "division": "One"},
            }

    captured_k = []

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
        captured_k.append(k)
        return away_elo, home_elo

    monkeypatch.setattr(elo_mod, "update_elo", fake_update_elo)

    league = PlacementLeague()
    weights = {
        "REG_WIN": 1.0,
        "REG_LOSS": 0.0,
        "OT_WIN": 0.67,
        "OT_LOSS": 0.33,
        "SO_WIN": 0.55,
        "SO_LOSS": 0.45,
    }
    games = [
        GameResult("g1", "2026-03-01", "A", "B", 3, 1, "REG"),
        GameResult("g2", "2026-03-02", "A", "B", 2, 1, "REG"),
        GameResult("g3", "2026-03-03", "A", "C", 2, 1, "REG"),
        GameResult("g4", "2026-03-04", "B", "C", 2, 1, "REG"),
        GameResult("g5", "2026-03-05", "A", "C", 2, 1, "REG"),
    ]

    calculate_elo(
        league=league,
        games=games,
        initial_elo=1500.0,
        k_factor=20.0,
        home_ice_advantage=0.0,
        win_weights=weights,
        placement_games=2,
        placement_k_add=30.0,
    )

    assert captured_k == [50.0, 50.0, 50.0, 50.0, 20.0]
