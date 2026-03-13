import math
from typing import Dict, List, Tuple
from .models import GameResult
from .league import BaseLeague

def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

def update_elo(
    away_elo: float,
    home_elo: float,
    away_actual: float,
    home_actual: float,
    k: float,
    home_ice_advantage: float,
    use_mov: bool = False,
    mov_cap: int = 5,
    away_goals: int = 0,
    home_goals: int = 0,
) -> Tuple[float, float]:
    away_expected = expected_score(away_elo, home_elo + home_ice_advantage)
    home_expected = expected_score(home_elo + home_ice_advantage, away_elo)

    mov_multiplier = 1.0
    if use_mov:
        goal_diff = abs(away_goals - home_goals)
        goal_diff = min(goal_diff, mov_cap)
        mov_multiplier = math.log(goal_diff + 1.5)

    effective_k = k * mov_multiplier

    new_away = away_elo + effective_k * (away_actual - away_expected)
    new_home = home_elo + effective_k * (home_actual - home_expected)
    return new_away, new_home

def calculate_elo(
    league: BaseLeague,
    games: List[GameResult],
    initial_elo: float,
    k_factor: float,
    home_ice_advantage: float,
    win_weights: dict,
    use_mov: bool = False,
    mov_cap: int = 5
) -> Tuple[Dict[str, float], List[dict], Dict[str, List[Tuple[str, float]]]]:
    teams = league.get_teams()
    ratings = {team: initial_elo for team in teams}
    history: List[dict] = []
    team_history: Dict[str, List[Tuple[str, float]]] = {
        team: [("START", initial_elo)] for team in teams
    }

    for game in games:
        away_before = ratings[game.away_team]
        home_before = ratings[game.home_team]

        away_actual, home_actual = league.actual_scores(game, win_weights)
        away_after, home_after = update_elo(
            away_before,
            home_before,
            away_actual,
            home_actual,
            k=k_factor,
            home_ice_advantage=home_ice_advantage,
            use_mov=use_mov,
            mov_cap=mov_cap,
            away_goals=game.away_score,
            home_goals=game.home_score
        )

        ratings[game.away_team] = away_after
        ratings[game.home_team] = home_after

        team_history[game.away_team].append((game.game_date, away_after))
        team_history[game.home_team].append((game.game_date, home_after))

        history.append({
            "game_id": game.game_id,
            "game_date": game.game_date,
            "away_team": game.away_team,
            "home_team": game.home_team,
            "away_score": game.away_score,
            "home_score": game.home_score,
            "last_period_type": game.last_period_type,
            "away_actual": away_actual,
            "home_actual": home_actual,
            "away_elo_before": round(away_before, 2),
            "home_elo_before": round(home_before, 2),
            "away_elo_after": round(away_after, 2),
            "home_elo_after": round(home_after, 2),
        })

    return ratings, history, team_history

def build_elo_rankings(ratings: Dict[str, float]) -> List[Tuple[int, str, float]]:
    sorted_teams = sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)
    return [(i, team, elo) for i, (team, elo) in enumerate(sorted_teams, start=1)]

def elo_win_prob(team_a: str, team_b: str, ratings: Dict[str, float], home_ice_advantage: float, neutral: bool = False) -> float:
    a = ratings[team_a]
    b = ratings[team_b]
    if neutral:
        return expected_score(a, b)
    return expected_score(a + home_ice_advantage, b)
