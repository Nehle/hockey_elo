from src.leagues.shl.league import SHLLeague
from src.core.elo import calculate_elo, build_elo_rankings

league = SHLLeague()
completed, remaining = league.fetch_games("20252026")
# Use same params as app
win_weights = {
    'REG_WIN': 1.0, 'REG_LOSS': 0.0,
    'OT_WIN': 0.67, 'OT_LOSS': 0.33,
    'SO_WIN': 0.55, 'SO_LOSS': 0.45
}
ratings, _, _ = calculate_elo(league, completed, 1500, 20.0, 33.0, win_weights)
rankings = build_elo_rankings(ratings)

records = league.build_team_records(completed)

for team_rec in records[:5]:
    team = team_rec['team']
    pts = team_rec['Pts']
    print(f"{team} - Pts: {pts} - ELO: {ratings[team]:.2f}")

print("\nBottom 5:")
for team_rec in records[-5:]:
    team = team_rec['team']
    pts = team_rec['Pts']
    print(f"{team} - Pts: {pts} - ELO: {ratings[team]:.2f}")
