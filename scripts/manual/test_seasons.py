import requests
from src.leagues.shl.league import SHLLeague

league = SHLLeague()
seasons = league.get_available_seasons()
print(seasons)
