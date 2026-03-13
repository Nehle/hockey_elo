from src.leagues.nhl.league import NHLLeague
league = NHLLeague()
c, r = league.fetch_games("20232024")
teams = league.get_teams()
print("Teams loaded:", len(teams))
print("Is ARI loaded?:", "ARI" in teams)
