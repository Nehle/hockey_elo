from typing import List, Dict, Tuple
from src.core.models import GameResult
from src.core.league import BaseLeague
from src.core.elo import build_elo_rankings, expected_score, update_elo


def _float_range(start: float, stop: float, step: float) -> List[float]:
    values: List[float] = []
    current = start
    while current <= stop + 1e-9:
        values.append(round(current, 6))
        current += step
    return values


def _home_ice_mse(
    league: BaseLeague,
    games: List[GameResult],
    win_weights: dict,
    initial_elo: float,
    k_factor: float,
    home_ice_advantage: float,
    use_mov: bool,
    mov_cap: int,
) -> float:
    teams = list(league.get_teams())
    ratings = {team: initial_elo for team in teams}
    ordered_games = league.sort_games_by_date(games)

    total_error = 0.0
    game_count = 0

    for game in ordered_games:
        if game.away_team not in ratings:
            ratings[game.away_team] = initial_elo
        if game.home_team not in ratings:
            ratings[game.home_team] = initial_elo

        away_before = ratings[game.away_team]
        home_before = ratings[game.home_team]
        away_actual, home_actual = league.actual_scores(game, win_weights)

        home_expected = expected_score(home_before + home_ice_advantage, away_before)
        total_error += (home_actual - home_expected) ** 2
        game_count += 1

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
            home_goals=game.home_score,
        )
        ratings[game.away_team] = away_after
        ratings[game.home_team] = home_after

    if game_count == 0:
        return float("inf")
    return total_error / game_count


def estimate_home_ice_advantage(
    league: BaseLeague,
    games: List[GameResult],
    win_weights: dict,
    initial_elo: float,
    k_factor: float,
    use_mov: bool = False,
    mov_cap: int = 5,
    search_min: float = 0.0,
    search_max: float = 200.0,
    coarse_step: float = 5.0,
    fine_window: float = 10.0,
    fine_step: float = 1.0,
) -> Tuple[float, float]:
    if not games:
        raise ValueError("Cannot estimate home ice advantage with no games")

    coarse_candidates = _float_range(search_min, search_max, coarse_step)
    best_coarse = search_min
    best_coarse_loss = float("inf")

    for candidate in coarse_candidates:
        loss = _home_ice_mse(
            league,
            games,
            win_weights,
            initial_elo,
            k_factor,
            candidate,
            use_mov,
            mov_cap,
        )
        if loss < best_coarse_loss:
            best_coarse_loss = loss
            best_coarse = candidate

    fine_min = max(search_min, best_coarse - fine_window)
    fine_max = min(search_max, best_coarse + fine_window)
    fine_candidates = _float_range(fine_min, fine_max, fine_step)

    best_fine = best_coarse
    best_fine_loss = best_coarse_loss
    for candidate in fine_candidates:
        loss = _home_ice_mse(
            league,
            games,
            win_weights,
            initial_elo,
            k_factor,
            candidate,
            use_mov,
            mov_cap,
        )
        if loss < best_fine_loss:
            best_fine_loss = loss
            best_fine = candidate

    return best_fine, best_fine_loss

def compare_elo_vs_standings(league: BaseLeague, ratings: Dict[str, float], games: List[GameResult]) -> List[dict]:
    elo_rankings = build_elo_rankings(ratings)
    elo_rank_map = {team: rank for rank, team, _ in elo_rankings}
    elo_value_map = {team: elo for _, team, elo in elo_rankings}
    standings = league.build_team_records(games)

    comparison = []
    for row in standings:
        team = row["team"]
        elo_rank = elo_rank_map[team]
        standings_rank = row["standings_rank"]
        comparison.append({
            **row,
            "elo_rank": elo_rank,
            "rank_diff": standings_rank - elo_rank,
            "elo": round(elo_value_map[team], 2),
        })

    return sorted(comparison, key=lambda x: x["elo_rank"])

def build_interdivision_matrix(league: BaseLeague, games: List[GameResult], win_weights: dict) -> Tuple[List[str], List[dict]]:
    team_info = league.team_info()
    divisions = list(set(info["division"] for info in team_info.values()))

    matrix: Dict[Tuple[str, str], dict] = {}
    for a in divisions:
        for b in divisions:
            if a == b: continue
            matrix[(a, b)] = {"division_a": a, "division_b": b, "games": 0, "a_score_total": 0.0, "a_wins": 0}

    for game in games:
        away_div = team_info[game.away_team]["division"]
        home_div = team_info[game.home_team]["division"]
        if away_div == home_div: continue

        away_actual, home_actual = league.actual_scores(game, win_weights)
        matrix[(away_div, home_div)]["games"] += 1
        matrix[(away_div, home_div)]["a_score_total"] += away_actual
        if game.away_score > game.home_score: matrix[(away_div, home_div)]["a_wins"] += 1

        matrix[(home_div, away_div)]["games"] += 1
        matrix[(home_div, away_div)]["a_score_total"] += home_actual
        if game.home_score > game.away_score: matrix[(home_div, away_div)]["a_wins"] += 1

    rows = []
    for a in divisions:
        row = {"division": a}
        for b in divisions:
            if a == b:
                row[b] = None
                row[f"{b}_games"] = None
                continue
            rec = matrix[(a, b)]
            row[b] = rec["a_score_total"] / rec["games"] if rec["games"] else None
            row[f"{b}_games"] = rec["games"]
        rows.append(row)

    return divisions, rows
