import random
from src.leagues.shl.league import SHLLeague

l = SHLLeague()
c, r = l.fetch_games("xs4m9qupsi")
records = l.build_team_records(c)
ratings = {t: 1500.0 for t in l.get_teams()}

res = l.simulate_playoffs(records, ratings, 1, random.Random(42))
print("Results from simulate_playoffs:")
try:
    print(res[0])
except Exception as e:
    print(e)
