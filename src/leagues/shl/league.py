from typing import List, Tuple, Dict
from src.core.league import BaseLeague
from src.core.models import GameResult
from .fetcher import fetch_shl_games, get_shl_seasons

class SHLLeague(BaseLeague):
    def __init__(self):
        super().__init__()
        self._teams = []
        self._team_info = {}
        self._seasons = get_shl_seasons()

    def get_available_seasons(self) -> Dict[str, str]:
        return self._seasons

    def fetch_games(self, season: str) -> Tuple[List[GameResult], List[GameResult]]:
        completed, remaining, teams, team_info = fetch_shl_games(season)
        self._teams = teams
        self._team_info = team_info
        return completed, remaining

    def get_teams(self) -> List[str]:
        return self._teams

    def team_info(self) -> dict:
        return self._team_info

    def build_team_records(self, games: List[GameResult]) -> List[dict]:
        # Only count regular-season games in standings; playoff games don't affect seeds
        reg_games = [g for g in games if getattr(g, 'game_type', 'REG') == "REG"]
        records_dict = {
            team: {
                'team': team, 
                'W': 0, 'L': 0, 'OTW': 0, 'OTL': 0, 
                'Pts': 0, 'GP': 0, 
                'conference': self._team_info.get(team, {}).get('conference', 'SHL'),
                'division': self._team_info.get(team, {}).get('division', 'SHL')
            }
            for team in self._teams
        }

        # Calculate using SHL 3-point system
        for g in reg_games:
            if g.home_team not in records_dict or g.away_team not in records_dict:
                continue

            home = records_dict[g.home_team]
            away = records_dict[g.away_team]

            home['GP'] += 1
            away['GP'] += 1

            if g.home_score > g.away_score:
                if g.last_period_type in ["OT", "SO"]:
                    home['OTW'] += 1
                    home['Pts'] += 2
                    away['OTL'] += 1
                    away['Pts'] += 1
                else:
                    home['W'] += 1
                    home['Pts'] += 3
                    away['L'] += 1
            elif g.away_score > g.home_score:
                if g.last_period_type in ["OT", "SO"]:
                    away['OTW'] += 1
                    away['Pts'] += 2
                    home['OTL'] += 1
                    home['Pts'] += 1
                else:
                    away['W'] += 1
                    away['Pts'] += 3
                    home['L'] += 1

        # Sort: Pts first, then W
        records = sorted(
            list(records_dict.values()), 
            key=lambda x: (x['Pts'], x['W']), 
            reverse=True
        )
        for i, row in enumerate(records):
            row['standings_rank'] = i + 1
        return records

    def actual_scores(self, game: GameResult, win_weights: dict) -> Tuple[float, float]:
        hw = win_weights.get('REG_WIN', 1.0)
        aw = win_weights.get('REG_LOSS', 0.0)

        if game.home_score > game.away_score:
            if game.last_period_type in ["OT", "SO"]:
                hw = win_weights.get('OT_WIN', 0.67)
                aw = win_weights.get('OT_LOSS', 0.33)
                if game.last_period_type == "SO":
                     hw = win_weights.get('SO_WIN', 0.55)
                     aw = win_weights.get('SO_LOSS', 0.45)
        elif game.away_score > game.home_score:
            hw = win_weights.get('REG_LOSS', 0.0)
            aw = win_weights.get('REG_WIN', 1.0)
            if game.last_period_type in ["OT", "SO"]:
                hw = win_weights.get('OT_LOSS', 0.33)
                aw = win_weights.get('OT_WIN', 0.67)
                if game.last_period_type == "SO":
                     hw = win_weights.get('SO_LOSS', 0.45)
                     aw = win_weights.get('SO_WIN', 0.55)

        return aw, hw

    def estimate_finish_type_probabilities(self, completed_games: List[GameResult]) -> dict:
        # Same as NHL pretty much
        total_games = len(completed_games)
        if total_games == 0:
            return {"REG": 0.75, "OT": 0.15, "SO": 0.10}

        counts = {"REG": 0, "OT": 0, "SO": 0}
        for g in completed_games:
            ctype = g.last_period_type if g.last_period_type in counts else "REG"
            counts[ctype] += 1

        return {k: v / total_games for k, v in counts.items()}

    def sample_score(self, finish_type: str, rng, home_wins: bool) -> Tuple[int, int]:
        # Dummy score sampling (used by simulation to populate standings tiebreakers if any)
        # SHL actually relies on goal difference A LOT for tiebreakers, but we might just fake it
        if finish_type == "REG":
            diff = rng.randint(1, 4)
            return (0, diff) if home_wins else (diff, 0)
        else: # OT or SO
            return (0, 1) if home_wins else (1, 0)

    def apply_simulated_game_to_records(self, records: Dict[str, dict], away_team: str, home_team: str, away_score: int, home_score: int, finish_type: str) -> None:
        if home_team not in records or away_team not in records:
            return

        h_rec = records[home_team]
        a_rec = records[away_team]

        h_rec['GP'] += 1
        a_rec['GP'] += 1

        if home_score > away_score:
            if finish_type in ["OT", "SO"]:
                h_rec['OTW'] += 1
                h_rec['Pts'] += 2
                a_rec['OTL'] += 1
                a_rec['Pts'] += 1
            else:
                h_rec['W'] += 1
                h_rec['Pts'] += 3
                a_rec['L'] += 1
        else:
            if finish_type in ["OT", "SO"]:
                a_rec['OTW'] += 1
                a_rec['Pts'] += 2
                h_rec['OTL'] += 1
                h_rec['Pts'] += 1
            else:
                a_rec['W'] += 1
                a_rec['Pts'] += 3
                h_rec['L'] += 1

    def get_playoff_column_names(self):
        return {
            'make_playoffs': 'Åttondelsfinal',
            'make_qf': 'Kvartsfinal',
            'make_sf': 'Semifinal',
            'make_final': 'Final',
            'win_champ': 'Winner'
        }

    def simulate_playoffs(self, records: list, ratings: dict, simulations: int, rng, **kwargs) -> list:
        home_ice_advantage = kwargs.get('home_ice_advantage', 33.0)
        from src.core.elo import expected_score

        stats = {r['team']: {"make_playoffs": 0, "make_qf": 0, "make_sf": 0, "make_final": 0, "win_champ": 0} for r in records}

        def win_series(t1, t2, best_of):
            if not t1:
                return t2
            if not t2:
                return t1
            wins_needed = (best_of // 2) + 1
            t1_wins, t2_wins = 0, 0
            while t1_wins < wins_needed and t2_wins < wins_needed:
                games_played = t1_wins + t2_wins
                if best_of == 3:
                    is_t1_home = games_played in [0, 2]  # 1st and 3rd games at higher seed home
                else:
                    is_t1_home = games_played in [0, 1, 4, 6]

                if is_t1_home:
                    p = expected_score(ratings[t1] + home_ice_advantage, ratings[t2])
                    if rng.random() < p:
                        t1_wins += 1
                    else:
                        t2_wins += 1
                else:
                    p = expected_score(ratings[t2] + home_ice_advantage, ratings[t1])
                    if rng.random() < p:
                        t2_wins += 1
                    else:
                        t1_wins += 1

            return t1 if t1_wins == wins_needed else t2

        def pair_highest_vs_lowest(seeded_teams):
            pairs = []
            left = 0
            right = len(seeded_teams) - 1
            while left < right:
                pairs.append((seeded_teams[left], seeded_teams[right]))
                left += 1
                right -= 1
            return pairs

        for _ in range(simulations):
            records_sorted = sorted(records, key=lambda x: (x.get('Pts', 0), x.get('W', 0)), reverse=True)
            standings_teams = [r['team'] for r in records_sorted]
            rank_map = {t: i for i, t in enumerate(standings_teams)}

            # SHL hard rules: top-6 get direct quarterfinal spots, seeds 7-10 play åttondelsfinal.
            top_six = standings_teams[:6]
            playin = standings_teams[6:10]

            # "Åttondelsfinal" column tracks teams that reach/play this round (seeds 7-10).
            for t in playin:
                stats[t]["make_playoffs"] += 1

            # Top-6 are guaranteed quarterfinals.
            qf_teams = list(top_six)
            for t in top_six:
                stats[t]["make_qf"] += 1

            # Åttondelsfinal (best-of-3): 7v10 and 8v9.
            if len(playin) == 4:
                w1 = win_series(playin[0], playin[3], 3)
                w2 = win_series(playin[1], playin[2], 3)
                qf_teams.extend([w1, w2])
                stats[w1]["make_qf"] += 1
                stats[w2]["make_qf"] += 1

            # Reseed every round: highest remaining seed plays lowest remaining seed.
            qf_seeded = sorted(qf_teams, key=lambda x: rank_map[x])
            sf_teams = []
            if len(qf_seeded) == 8:
                for higher, lower in pair_highest_vs_lowest(qf_seeded):
                    sf_teams.append(win_series(higher, lower, 7))

            for t in sf_teams:
                stats[t]["make_sf"] += 1

            sf_seeded = sorted(sf_teams, key=lambda x: rank_map[x])
            final_teams = []
            if len(sf_seeded) == 4:
                for higher, lower in pair_highest_vs_lowest(sf_seeded):
                    final_teams.append(win_series(higher, lower, 7))

            for t in final_teams:
                stats[t]["make_final"] += 1

            final_seeded = sorted(final_teams, key=lambda x: rank_map[x])
            if len(final_seeded) == 2:
                champ = win_series(final_seeded[0], final_seeded[1], 7)
                stats[champ]["win_champ"] += 1

        out = []
        for r in records:
            t = r['team']
            r_out = dict(r)
            r_out["made_playoffs"] = 1 if stats[t]["make_playoffs"] > 0 else 0
            r_out["make_qf"] = stats[t]["make_qf"] / simulations if simulations > 0 else 0
            r_out["make_sf"] = stats[t]["make_sf"] / simulations if simulations > 0 else 0
            r_out["make_final"] = stats[t]["make_final"] / simulations if simulations > 0 else 0
            r_out["win_champ"] = stats[t]["win_champ"] / simulations if simulations > 0 else 0
            out.append(r_out)
            
        return out
