from typing import List, Dict, Tuple
from src.core.league import BaseLeague
from src.core.models import GameResult, PlayoffSeed
from src.core.elo import elo_win_prob
from .fetcher import split_completed_and_remaining_games

class NHLLeague(BaseLeague):
    def __init__(self):
        super().__init__()
        self._teams = []
        self._team_info = {}

    def get_available_seasons(self) -> Dict[str, str]:
        # NHL has seasons back to 1917, but we can populate back to 1980
        # excluding the 2004-2005 lockout season where no games were played
        return {f"{y}/{y+1}": f"{y}{y+1}" for y in range(2025, 1979, -1) if y != 2004}

    def fetch_games(self, season: str) -> Tuple[List[GameResult], List[GameResult]]:
        completed, remaining, teams, team_info = split_completed_and_remaining_games(season)
        self._teams = teams
        self._team_info = team_info
        return completed, remaining

    def get_teams(self) -> List[str]:
        return self._teams

    def team_info(self) -> dict:
        return self._team_info

    def actual_scores(self, game: GameResult, win_weights: dict) -> Tuple[float, float]:
        away_won = game.away_score > game.home_score

        if game.last_period_type == "OT":
            w, l = win_weights['OT_WIN'], win_weights['OT_LOSS']
        elif game.last_period_type == "SO":
            w, l = win_weights['SO_WIN'], win_weights['SO_LOSS']
        else:
            w, l = win_weights['REG_WIN'], win_weights['REG_LOSS']

        if away_won:
            return w, l
        else:
            return l, w

    def sample_score(self, finish_type: str, rng, home_wins: bool) -> Tuple[int, int]:
        if finish_type == "REG":
            winning_score = rng.choice([2, 3, 4, 5, 6])
            losing_score = max(0, winning_score - rng.choice([1, 2, 3]))
            if losing_score >= winning_score:
                losing_score = winning_score - 1
        elif finish_type == "OT":
            losing_score = rng.choice([1, 2, 3, 4, 5])
            winning_score = losing_score + 1
        else:
            losing_score = rng.choice([1, 2, 3, 4, 5])
            winning_score = losing_score + 1

        if home_wins:
            return losing_score, winning_score
        return winning_score, losing_score

    def estimate_finish_type_probabilities(self, completed_games: List[GameResult]) -> Dict[str, float]:
        counts = {"REG": 0, "OT": 0, "SO": 0}
        for game in completed_games:
            if game.last_period_type == "OT":
                counts["OT"] += 1
            elif game.last_period_type == "SO":
                counts["SO"] += 1
            else:
                counts["REG"] += 1

        total = sum(counts.values())
        if total == 0:
            return {"REG": 0.75, "OT": 0.17, "SO": 0.08}

        return {
            "REG": counts["REG"] / total,
            "OT": counts["OT"] / total,
            "SO": counts["SO"] / total,
        }

    def build_team_records(self, games: List[GameResult]) -> List[dict]:
        records: Dict[str, dict] = {}
        for team in self._teams:
            if team not in self._team_info:
                self._team_info[team] = {"conference": "Unknown", "division": "Unknown"}
            records[team] = {
                "team": team,
                "conference": self._team_info[team]["conference"],
                "division": self._team_info[team]["division"],
                "GP": 0, "W": 0, "L": 0, "OTL": 0,
                "RW": 0, "OTW": 0, "SOW": 0, "SOL": 0,
                "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
            }

        for game in games:
            for t in (game.away_team, game.home_team):
                if t not in records:
                    self._teams.append(t)
                    self._team_info[t] = {"conference": "Unknown", "division": "Unknown"}
                    records[t] = {
                        "team": t,
                        "conference": "Unknown",
                        "division": "Unknown",
                        "GP": 0, "W": 0, "L": 0, "OTL": 0,
                        "RW": 0, "OTW": 0, "SOW": 0, "SOL": 0,
                        "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
                    }

            away = records[game.away_team]
            home = records[game.home_team]

            away["GP"] += 1
            home["GP"] += 1

            away["GF"] += game.away_score
            away["GA"] += game.home_score
            home["GF"] += game.home_score
            home["GA"] += game.away_score

            is_ot = game.last_period_type == "OT"
            is_so = game.last_period_type == "SO"

            away_won = game.away_score > game.home_score
            home_won = game.home_score > game.away_score

            if away_won:
                away["W"] += 1
                if is_ot or is_so:
                    home["OTL"] += 1
                else:
                    home["L"] += 1

                if is_ot:
                    away["OTW"] += 1
                elif is_so:
                    away["SOW"] += 1
                    home["SOL"] += 1
                else:
                    away["RW"] += 1
            elif home_won:
                home["W"] += 1
                if is_ot or is_so:
                    away["OTL"] += 1
                else:
                    away["L"] += 1

                if is_ot:
                    home["OTW"] += 1
                elif is_so:
                    home["SOW"] += 1
                    away["SOL"] += 1
                else:
                    home["RW"] += 1

        for rec in records.values():
            rec["Pts"] = 2 * rec["W"] + rec["OTL"]
            rec["GD"] = rec["GF"] - rec["GA"]

        standings = sorted(
            records.values(),
            key=lambda r: (r["Pts"], r["W"], r["RW"], r["GD"], r["GF"]),
            reverse=True,
        )

        conference_groups = {}
        division_groups: Dict[str, List[dict]] = {}

        for idx, rec in enumerate(standings, start=1):
            rec["standings_rank"] = idx
            conference_groups.setdefault(rec["conference"], []).append(rec)
            division_groups.setdefault(rec["division"], []).append(rec)

        for _, rows in conference_groups.items():
            for idx, rec in enumerate(rows, start=1):
                rec["conference_rank"] = idx

        for _, rows in division_groups.items():
            rows_sorted = sorted(
                rows,
                key=lambda r: (r["Pts"], r["W"], r["RW"], r["GD"], r["GF"]),
                reverse=True,
            )
            for idx, rec in enumerate(rows_sorted, start=1):
                rec["division_rank"] = idx

        return standings

    def apply_simulated_game_to_records(self, records: Dict[str, dict], away_team: str, home_team: str, away_score: int, home_score: int, finish_type: str) -> None:
        away = records[away_team]
        home = records[home_team]

        away["GP"] += 1
        home["GP"] += 1
        away["GF"] += away_score
        away["GA"] += home_score
        home["GF"] += home_score
        home["GA"] += away_score

        away_won = away_score > home_score

        if away_won:
            away["W"] += 1
            if finish_type in {"OT", "SO"}:
                home["OTL"] += 1
            else:
                home["L"] += 1

            if finish_type == "OT":
                away["OTW"] += 1
            elif finish_type == "SO":
                away["SOW"] += 1
                home["SOL"] += 1
            else:
                away["RW"] += 1
        else:
            home["W"] += 1
            if finish_type in {"OT", "SO"}:
                away["OTL"] += 1
            else:
                away["L"] += 1

            if finish_type == "OT":
                home["OTW"] += 1
            elif finish_type == "SO":
                home["SOW"] += 1
                away["SOL"] += 1
            else:
                home["RW"] += 1

        away["Pts"] = 2 * away["W"] + away["OTL"]
        home["Pts"] = 2 * home["W"] + home["OTL"]
        away["GD"] = away["GF"] - away["GA"]
        home["GD"] = home["GF"] - home["GA"]

    def _team_sort_key(self, team: str, records_map: Dict[str, dict]) -> Tuple[int, int, int, int, int]:
        r = records_map[team]
        return (r["Pts"], r["W"], r["RW"], r["GD"], r["GF"])

    def _get_conference_playoff_seeds(self, records: List[dict], conference: str) -> Dict[str, PlayoffSeed]:
        conf_rows = [r for r in records if r["conference"] == conference]
        if not conf_rows:
            return {}

        divs = {}
        for r in conf_rows:
            divs.setdefault(r["division"], []).append(r)
        
        for d in divs:
            divs[d] = sorted(divs[d], key=lambda r: self._team_sort_key(r["team"], {row["team"]: row for row in records}), reverse=True)
            
        div_keys = list(divs.keys())
        
        # Determine our two primary division pools
        if len(div_keys) >= 2:
            d1_name, d2_name = div_keys[0], div_keys[1]
            # Prioritize matching modern NHL if possible
            if "Atlantic" in div_keys and "Metropolitan" in div_keys:
                d1_name, d2_name = "Atlantic", "Metropolitan"
            elif "Central" in div_keys and "Pacific" in div_keys:
                d1_name, d2_name = "Central", "Pacific"
            d1, d2 = divs[d1_name], divs[d2_name]
        else:
            all_sorted = sorted(conf_rows, key=lambda r: self._team_sort_key(r["team"], {row["team"]: row for row in records}), reverse=True)
            d1_name, d2_name = "DivA", "DivB"
            d1 = all_sorted[0::2]
            d2 = all_sorted[1::2]
            
        # Fallback if too few teams
        if len(d1) < 3 or len(d2) < 3:
            all_sorted = sorted(d1 + d2, key=lambda r: self._team_sort_key(r["team"], {row["team"]: row for row in records}), reverse=True)
            if len(all_sorted) < 8:
                return {} # Too few teams to form 8-seed conference
            d1 = all_sorted[:len(all_sorted)//2]
            d2 = all_sorted[len(all_sorted)//2:]

        d1_top3 = d1[:3]
        d2_top3 = d2[:3]

        wild_card_pool = sorted(d1[3:] + d2[3:], key=lambda r: self._team_sort_key(r["team"], {row["team"]: row for row in records}), reverse=True)
        # Ensure we have at least 2 wild cards
        if len(wild_card_pool) < 2:
            return {}
            
        wc1, wc2 = wild_card_pool[:2]

        d1_winner = d1_top3[0]
        d2_winner = d2_top3[0]

        if self._team_sort_key(d1_winner["team"], {row["team"]: row for row in records}) >= self._team_sort_key(d2_winner["team"], {row["team"]: row for row in records}):
            d1_wc = wc2
            d2_wc = wc1
        else:
            d1_wc = wc1
            d2_wc = wc2

        seeds_raw = [
            (d1_top3[0], "Div1_1"), (d1_top3[1], "Div1_2"), (d1_top3[2], "Div1_3"),
            (d2_top3[0], "Div2_1"), (d2_top3[1], "Div2_2"), (d2_top3[2], "Div2_3"),
            (d1_wc, "WC-assigned_1"), (d2_wc, "WC-assigned_2"),
        ]

        out: Dict[str, PlayoffSeed] = {}
        for row, label in seeds_raw:
            out[row["team"]] = PlayoffSeed(
                team=row["team"], conference=row["conference"], division=row["division"],
                points=row["Pts"], wins=row["W"], rw=row["RW"], gd=row["GD"], gf=row["GF"],
                seed_label=label,
            )
        return out

    def _build_playoff_bracket(self, records: List[dict]) -> Dict[str, List[Tuple[str, str]]]:
        east = self._get_conference_playoff_seeds(records, "East")
        west = self._get_conference_playoff_seeds(records, "West")

        def conf_round(conf_seeds: Dict[str, PlayoffSeed]) -> List[Tuple[str, str]]:
            if not conf_seeds:
                return []
                
            div1 = sorted([s for s in conf_seeds.values() if s.seed_label.startswith("Div1_")], key=lambda s: (s.points, s.wins, s.rw, s.gd, s.gf), reverse=True)
            div2 = sorted([s for s in conf_seeds.values() if s.seed_label.startswith("Div2_")], key=lambda s: (s.points, s.wins, s.rw, s.gd, s.gf), reverse=True)
            
            wc_assigned_1 = [s for s in conf_seeds.values() if s.seed_label == "WC-assigned_1"][0]
            wc_assigned_2 = [s for s in conf_seeds.values() if s.seed_label == "WC-assigned_2"][0]

            div1_winner = div1[0]
            div2_winner = div2[0]
            
            return [
                (div1_winner.team, wc_assigned_1.team), 
                (div2_winner.team, wc_assigned_2.team), 
                (div1[1].team, div1[2].team), 
                (div2[1].team, div2[2].team)
            ]

        return {
            "East_R1": conf_round(east),
            "West_R1": conf_round(west),
        }

    def _simulate_series(self, higher_seed: str, lower_seed: str, ratings: Dict[str, float], rng, home_ice_advantage: float) -> str:
        home_pattern = [higher_seed, higher_seed, lower_seed, lower_seed, higher_seed, lower_seed, higher_seed]
        wins = {higher_seed: 0, lower_seed: 0}
        for home_team in home_pattern:
            away_team = lower_seed if home_team == higher_seed else higher_seed
            p_home = elo_win_prob(home_team, away_team, ratings, home_ice_advantage, neutral=False)
            if rng.random() < p_home:
                wins[home_team] += 1
            else:
                wins[away_team] += 1
            if wins[higher_seed] == 4:
                return higher_seed
            if wins[lower_seed] == 4:
                return lower_seed
        return higher_seed

    def simulate_playoffs(self, records: List[dict], ratings: Dict[str, float], simulations: int, rng, **kwargs) -> List[dict]:
        records_map = {r["team"]: r for r in records}
        bracket = self._build_playoff_bracket(records)
        home_ice = kwargs.get('home_ice_advantage', 33.0)

        stats = {team: {"team": team, "conference": self._team_info[team]["conference"], "division": self._team_info[team]["division"], "round2": 0, "conf_final": 0, "stanley_final": 0, "cup": 0} for team in self._teams}

        for _ in range(simulations):
            east_r1_winners = []
            west_r1_winners = []

            for a, b in bracket["East_R1"]:
                higher, lower = (a, b) if self._team_sort_key(a, records_map) >= self._team_sort_key(b, records_map) else (b, a)
                winner = self._simulate_series(higher, lower, ratings, rng, home_ice)
                east_r1_winners.append(winner)
                stats[winner]["round2"] += 1

            for a, b in bracket["West_R1"]:
                higher, lower = (a, b) if self._team_sort_key(a, records_map) >= self._team_sort_key(b, records_map) else (b, a)
                winner = self._simulate_series(higher, lower, ratings, rng, home_ice)
                west_r1_winners.append(winner)
                stats[winner]["round2"] += 1

            # CF
            east_div1_h, east_div1_l = (east_r1_winners[0], east_r1_winners[2]) if self._team_sort_key(east_r1_winners[0], records_map) >= self._team_sort_key(east_r1_winners[2], records_map) else (east_r1_winners[2], east_r1_winners[0])
            east_div2_h, east_div2_l = (east_r1_winners[1], east_r1_winners[3]) if self._team_sort_key(east_r1_winners[1], records_map) >= self._team_sort_key(east_r1_winners[3], records_map) else (east_r1_winners[3], east_r1_winners[1])
            west_div1_h, west_div1_l = (west_r1_winners[0], west_r1_winners[2]) if self._team_sort_key(west_r1_winners[0], records_map) >= self._team_sort_key(west_r1_winners[2], records_map) else (west_r1_winners[2], west_r1_winners[0])
            west_div2_h, west_div2_l = (west_r1_winners[1], west_r1_winners[3]) if self._team_sort_key(west_r1_winners[1], records_map) >= self._team_sort_key(west_r1_winners[3], records_map) else (west_r1_winners[3], west_r1_winners[1])

            east_cf1 = self._simulate_series(east_div1_h, east_div1_l, ratings, rng, home_ice)
            east_cf2 = self._simulate_series(east_div2_h, east_div2_l, ratings, rng, home_ice)
            west_cf1 = self._simulate_series(west_div1_h, west_div1_l, ratings, rng, home_ice)
            west_cf2 = self._simulate_series(west_div2_h, west_div2_l, ratings, rng, home_ice)

            stats[east_cf1]["conf_final"] += 1
            stats[east_cf2]["conf_final"] += 1
            stats[west_cf1]["conf_final"] += 1
            stats[west_cf2]["conf_final"] += 1

            east_h, east_l = (east_cf1, east_cf2) if self._team_sort_key(east_cf1, records_map) >= self._team_sort_key(east_cf2, records_map) else (east_cf2, east_cf1)
            west_h, west_l = (west_cf1, west_cf2) if self._team_sort_key(west_cf1, records_map) >= self._team_sort_key(west_cf2, records_map) else (west_cf2, west_cf1)

            east_champ = self._simulate_series(east_h, east_l, ratings, rng, home_ice)
            west_champ = self._simulate_series(west_h, west_l, ratings, rng, home_ice)

            stats[east_champ]["stanley_final"] += 1
            stats[west_champ]["stanley_final"] += 1

            final_h, final_l = (east_champ, west_champ) if self._team_sort_key(east_champ, records_map) >= self._team_sort_key(west_champ, records_map) else (west_champ, east_champ)
            cup_winner = self._simulate_series(final_h, final_l, ratings, rng, home_ice)
            stats[cup_winner]["cup"] += 1

        playoff_teams = {seed.team for conf in ("East", "West") for seed in self._get_conference_playoff_seeds(records, conf).values()}
        out = []
        for team in self._teams:
            s = stats[team]
            out.append({
                "team": team, "conference": self._team_info[team]["conference"], "division": self._team_info[team]["division"],
                "elo": round(ratings[team], 2), "made_playoffs": 1 if team in playoff_teams else 0,
                "make_qf": s["round2"] / simulations, "make_sf": s["conf_final"] / simulations,
                "make_final": s["stanley_final"] / simulations, "win_champ": s["cup"] / simulations,
            })
        return out
        
    def get_playoff_column_names(self) -> Dict[str, str]:
        return {
            'make_playoffs': 'Make Playoffs',
            'make_qf': 'Round 2',
            'make_sf': 'Conference Finals',
            'make_final': 'Stanley Cup Finals',
            'win_champ': 'Win Championship'
        }
