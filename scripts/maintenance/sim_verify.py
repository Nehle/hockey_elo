from src.leagues.shl.league import SHLLeague
import random
l = SHLLeague()
c, r = l.fetch_games("xs4m9qupsi")
records = l.build_team_records(c)
ratings = {t: 1500.0 for t in l.get_teams()}

res = l.simulate_playoffs(records, ratings, 100, random.Random(42))
print("Stats for top 3 teams:")
for r in res[:3]:
    print(r['team'], r['made_playoffs'], r['make_qf'], r['make_sf'], r['make_final'], r['win_champ'])

