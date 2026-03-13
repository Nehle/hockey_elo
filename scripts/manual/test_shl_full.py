from src.leagues.shl.league import SHLLeague
from src.tools.simulator import simulate_season_and_playoffs_from_today
import pprint
import random
l = SHLLeague()
c, r = l.fetch_games("xs4m9qupsi")
ratings = {t: 1500.0 for t in l.get_teams()}

res = simulate_season_and_playoffs_from_today(
    l, c, [], ratings, 20, 33.0, 10.0,
    {"REG_WIN":1, "REG_LOSS":0, "OT_WIN":1, "OT_LOSS":0, "SO_WIN":1, "SO_LOSS":0}
)
pprint.pprint(res[:3])
