from typing import List, Dict, Tuple
from src.core.models import GameResult
from src.core.league import BaseLeague
from src.core.elo import build_elo_rankings

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
