from src.leagues.nhl.fetcher import fetch_all_games_raw

raw = fetch_all_games_raw("20232024")
print("Total games:", len(raw))

teams = set()
for g in raw:
    teams.add(g["homeTeam"].get("abbrev", {}).get("default") or g["homeTeam"]["abbrev"])
    teams.add(g["awayTeam"].get("abbrev", {}).get("default") or g["awayTeam"]["abbrev"])

print("Found teams:", len(teams))
print("Missing:", [t for t in teams if t == "ARI"])
