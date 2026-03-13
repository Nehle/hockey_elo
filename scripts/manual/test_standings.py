import requests

def get_teams_from_standings(season: str):
    date_str = f"{season[4:]}-04-01"
    url = f"https://api-web.nhle.com/v1/standings/{date_str}"
    data = requests.get(url).json()
    teams = []
    team_info = {}
    for st in data.get("standings", []):
        abbrev = st.get("teamAbbrev", {}).get("default")
        teams.append(abbrev)
        team_info[abbrev] = {
            "conference": st.get("conferenceName", "Unknown"),
            "division": st.get("divisionName", "Unknown")
        }
    return teams, team_info

t, t_info = get_teams_from_standings("20232024")
print("Teams count:", len(t))
print("ARI in teams?", "ARI" in t)
print("ARI info:", t_info.get("ARI"))
