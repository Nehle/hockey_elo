import requests

url = "https://www.shl.se/api/sports-v2/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B&gamePlace=all&played=all"
resp = requests.get(url, timeout=15).json()

games = resp.get("gameInfo", [])
print(f"Total games: {len(games)}")

teams = {}
for g in games:
    ht = g.get("homeTeamInfo", {})
    at = g.get("awayTeamInfo", {})
    hc = ht.get("code")
    ac = at.get("code")
    if hc and hc not in teams:
        teams[hc] = ht.get("names", {}).get("long", hc)
    if ac and ac not in teams:
        teams[ac] = at.get("names", {}).get("long", ac)

print(f"Teams: {len(teams)}")

