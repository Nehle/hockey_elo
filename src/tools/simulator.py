import random
from typing import List, Dict, Tuple
from src.core.models import GameResult
from src.core.league import BaseLeague
from src.core.elo import expected_score, update_elo

def sample_finish_type(finish_probs: Dict[str, float], rng: random.Random) -> str:
    x = rng.random()
    if x < finish_probs.get("REG", 0): return "REG"
    if x < finish_probs.get("REG", 0) + finish_probs.get("OT", 0): return "OT"
    return "SO"

def simulate_future_game(
    league: BaseLeague,
    game: GameResult,
    ratings: Dict[str, float],
    finish_probs: Dict[str, float],
    rng: random.Random,
    home_ice_advantage: float,
    win_weights: dict
) -> Tuple[str, str, int, int, str, float, float]:
    p_home = expected_score(ratings[game.home_team] + home_ice_advantage, ratings[game.away_team])
    home_wins = rng.random() < p_home
    finish_type = sample_finish_type(finish_probs, rng)

    away_score, home_score = league.sample_score(finish_type, rng, home_wins)

    if away_score > home_score:
        w, l = (win_weights['OT_WIN'], win_weights['OT_LOSS']) if finish_type == "OT" else \
               (win_weights['SO_WIN'], win_weights['SO_LOSS']) if finish_type == "SO" else \
               (win_weights['REG_WIN'], win_weights['REG_LOSS'])
        away_actual, home_actual = w, l
    else:
        w, l = (win_weights['OT_WIN'], win_weights['OT_LOSS']) if finish_type == "OT" else \
               (win_weights['SO_WIN'], win_weights['SO_LOSS']) if finish_type == "SO" else \
               (win_weights['REG_WIN'], win_weights['REG_LOSS'])
        away_actual, home_actual = l, w

    return game.away_team, game.home_team, away_score, home_score, finish_type, away_actual, home_actual

def simulate_season_and_playoffs_from_today(
    league: BaseLeague,
    completed_games: List[GameResult],
    remaining_games: List[GameResult],
    current_ratings: Dict[str, float],
    simulations: int,
    home_ice_advantage: float,
    k_factor: float,
    win_weights: dict,
    seed: int = 42,
    use_mov: bool = False,
    mov_cap: int = 5
) -> List[dict]:
    rng = random.Random(seed)
    finish_probs = league.estimate_finish_type_probabilities(completed_games)
    
    # We get the base records map. BaseLeague.build_team_records returns list of dicts.
    base_records_list = league.build_team_records(completed_games)
    base_records = {r["team"]: r for r in base_records_list}
    teams = league.get_teams()
    team_info = league.team_info()

    results = {
        team: {
            "team": team, "conference": team_info[team]["conference"], "division": team_info[team]["division"],
            "make_playoffs": 0, "make_qf": 0, "make_sf": 0, "make_final": 0, "win_champ": 0,
            "final_points_total": 0.0,
        }
        for team in teams
    }

    for _ in range(simulations):
        ratings = {team: elo for team, elo in current_ratings.items()}
        records = {team: {key: value for key, value in rec.items()} for team, rec in base_records.items()}

        for game in remaining_games:
            if getattr(game, "game_type", "REG") != "REG":
                continue
            (away_team, home_team, away_score, home_score, finish_type, away_actual, home_actual) = simulate_future_game(
                league, game, ratings, finish_probs, rng, home_ice_advantage, win_weights
            )
            away_after, home_after = update_elo(
                ratings[away_team], ratings[home_team], 
                away_actual, home_actual, k_factor, home_ice_advantage,
                use_mov=use_mov, mov_cap=mov_cap,
                away_goals=away_score, home_goals=home_score
            )
            ratings[away_team] = away_after
            ratings[home_team] = home_after
            league.apply_simulated_game_to_records(records, away_team, home_team, away_score, home_score, finish_type)

        # Capture expected final regular-season points (averaged over simulations).
        for team in teams:
            results[team]["final_points_total"] += float(records.get(team, {}).get("Pts", 0.0))

        final_records_list = [r for r in records.values()]
        # Then we call the playoff simulator for that specific league passing specific final_records_list and new ELO ratings
        sim_stats = league.simulate_playoffs(final_records_list, ratings, 1, rng, home_ice_advantage=home_ice_advantage, use_mov=use_mov, mov_cap=mov_cap)
        for stat in sim_stats:
            team = stat['team']
            if stat.get('made_playoffs', 0): results[team]['make_playoffs'] += 1
            if stat.get('make_qf', 0) > 0: results[team]['make_qf'] += 1
            if stat.get('make_sf', 0) > 0: results[team]['make_sf'] += 1
            if stat.get('make_final', 0) > 0: results[team]['make_final'] += 1
            if stat.get('win_champ', 0) > 0: results[team]['win_champ'] += 1

    out = []
    for team in teams:
        r = results[team]
        out.append({
            "team": team, "conference": r["conference"], "division": r["division"],
            "current_elo": round(current_ratings[team], 2),
            "final_points_avg": round(r["final_points_total"] / simulations, 2) if simulations > 0 else 0.0,
            "make_playoffs_prob": round(r["make_playoffs"] / simulations, 4),
            "make_qf_prob": round(r["make_qf"] / simulations, 4),
            "make_sf_prob": round(r["make_sf"] / simulations, 4),
            "make_final_prob": round(r["make_final"] / simulations, 4),
            "win_champ_prob": round(r["win_champ"] / simulations, 4),
        })
    return sorted(out, key=lambda x: x["win_champ_prob"], reverse=True)
