from src.leagues.shl.league import SHLLeague
from src.core.elo import calculate_elo, build_elo_rankings
import random

league = SHLLeague()
completed, remaining = league.fetch_games("xs4m9qupsi")
# Use same params as app
win_weights = {
    'REG_WIN': 1.0, 'REG_LOSS': 0.0,
    'OT_WIN': 0.67, 'OT_LOSS': 0.33,
    'SO_WIN': 0.55, 'SO_LOSS': 0.45
}
ratings, _, _ = calculate_elo(league, completed, 1500, 20.0, 33.0, win_weights)

from src.tools.simulator import simulate_season_and_playoffs_from_today
res = simulate_season_and_playoffs_from_today(league, completed, remaining, ratings, 50, 33.0, 20.0, win_weights)

for r in res[:5]:
    print(r["team"], r["cup_prob"])
