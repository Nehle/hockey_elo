import re

with open("patch.py", "r") as f:
    old_str = f.read()

new_str = """    def get_playoff_column_names(self):
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
        
        for _ in range(simulations):
            records_sorted = sorted(records, key=lambda x: (x.get('Pts', 0), x.get('W', 0)), reverse=True)
            standings_teams = [r['team'] for r in records_sorted]
            rank_map = {t: i for i, t in enumerate(standings_teams)}
            
            def win_series(t1, t2, best_of):
                if not t1: return t2
                if not t2: return t1
                wins_needed = (best_of // 2) + 1
                t1_wins, t2_wins = 0, 0
                while t1_wins < wins_needed and t2_wins < wins_needed:
                    games_played = t1_wins + t2_wins
                    if best_of == 3:
                        is_t1_home = games_played in [0, 2] # 1st and 3rd gm at home
                    else:
                        is_t1_home = games_played in [0, 1, 4, 6]
                    if is_t1_home:
                        p = expected_score(ratings[t1] + home_ice_advantage, ratings[t2])
                        if rng.random() < p: t1_wins += 1
                        else: t2_wins += 1
                    else:
                        p = expected_score(ratings[t2] + home_ice_advantage, ratings[t1])
                        if rng.random() < p: t2_wins += 1
                        else: t1_wins += 1
                return t1 if t1_wins == wins_needed else t2

            for t in standings_teams[:10]: stats[t]["make_playoffs"] += 1
                
            qf_teams = standings_teams[:6]
            playin = standings_teams[6:10]
            
            if len(playin) == 4:
                w1 = win_series(playin[0], playin[3], 3)
                w2 = win_series(playin[1], playin[2], 3)
                qf_teams.extend([w1, w2])
                
            qf_teams.sort(key=lambda x: rank_map[x])
            for t in qf_teams: stats[t]["make_qf"] += 1
                
            sf_teams = []
            if len(qf_teams) == 8:
                sf_teams.extend([
                    win_series(qf_teams[0], qf_teams[7], 7),
                    win_series(qf_teams[1], qf_teams[6], 7),
                    win_series(qf_teams[2], qf_teams[5], 7),
                    win_series(qf_teams[3], qf_teams[4], 7)
                ])
                
            sf_teams.sort(key=lambda x: rank_map[x])
            for t in sf_teams: stats[t]["make_sf"] += 1
                
            final_teams = []
            if len(sf_teams) == 4:
                final_teams.extend([
                    win_series(sf_teams[0], sf_teams[3], 7),
                    win_series(sf_teams[1], sf_teams[2], 7)
                ])
                
            final_teams.sort(key=lambda x: rank_map[x])
            for t in final_teams: stats[t]["make_final"] += 1
                
            if len(final_teams) == 2:
                champ = win_series(final_teams[0], final_teams[1], 7)
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
"""

with open("src/leagues/shl/league.py", "r") as f:
    content = f.read()

new_content = content.replace(old_str, new_str)

with open("src/leagues/shl/league.py", "w") as f:
    f.write(new_content)
    
print("Replaced!")
