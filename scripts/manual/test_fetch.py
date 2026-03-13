from src.leagues.shl.league import SHLLeague

league = SHLLeague()
c, r = league.fetch_games("qbL-2hVFK643r") # 1995/1996
print(len(c))
print(league.get_teams())
