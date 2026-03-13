import requests
from typing import List, Dict, Tuple, Set
from src.core.models import GameResult
import concurrent.futures
from .constants import TEAMS

API_BASE = "https://api-web.nhle.com/v1"
TIMEOUT = 20

def get_season_teams_and_info(season: str) -> Tuple[List[str], Dict[str, dict]]:
    year = season[4:]
    team_list = []
    team_info = {}
    
    # Try a few dates during the season to capture all active teams
    dates_to_try = [f"{year}-04-15", f"{year}-04-01", f"{year}-03-15", f"{year}-03-01", f"{year}-02-15"]
    
    for date_str in dates_to_try:
        url = f"{API_BASE}/standings/{date_str}"
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get("standings", [])
            if data and len(data) > 0:
                for t in data:
                    abbrev = t["teamAbbrev"]["default"]
                    team_list.append(abbrev)
                    conf_name = t.get("conferenceName", "Unknown")
                    if conf_name in ["Eastern", "Prince of Wales", "Wales", "Wales Conference"]: conf_name = "East"
                    if conf_name in ["Western", "Clarence Campbell", "Campbell", "Campbell Conference"]: conf_name = "West"
                    
                    # Some early years didn't even have conferences or used different names, but map them just in case
                    team_info[abbrev] = {
                        "conference": conf_name,
                        "division": t.get("divisionName", "Unknown")
                    }
                return team_list, team_info
        except Exception:
            continue

    # fallback
    for t in TEAMS:
        team_info[t] = {"conference": "Unknown", "division": "Unknown"}
    return TEAMS, team_info

def get_season_teams(season: str) -> List[str]:
    teams, _ = get_season_teams_and_info(season)
    return teams

def fetch_team_schedule(team: str, season: str) -> List[dict]:
    url = f"{API_BASE}/club-schedule-season/{team}/{season}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list): return data
        if hasattr(data, 'get'): return data.get("games", [])
    except Exception:
        pass
    return []

def fetch_all_games_raw(season: str) -> List[dict]:
    deduped: Dict[int, dict] = {}
    teams = get_season_teams(season)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_team_schedule, t, season): t for t in teams}
        for future in concurrent.futures.as_completed(futures):
            for game in future.result():
                deduped[int(game["id"])] = game

    return sorted(deduped.values(), key=lambda g: (str(g.get("gameDate", "")), int(g.get("id", 0))))

def is_completed_regular_season_game(game: dict) -> bool:
    if game.get("gameType") != 2:
        return False

    state = str(game.get("gameState", "")).upper()
    schedule_state = str(game.get("gameScheduleState", "")).upper()
    completed_states = {"FINAL", "OFF"}

    return state in completed_states or schedule_state in completed_states

def extract_last_period_type(game: dict) -> str:
    outcome = game.get("gameOutcome", {}) or {}

    value = outcome.get("lastPeriodType")
    if isinstance(value, str) and value.strip():
        return value.strip().upper()

    for key in ("overtime", "periodType", "resultType"):
        value = outcome.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()

    return "UNKNOWN"

def team_abbrev(team_obj: dict) -> str:
    abbrev = team_obj.get("abbrev")
    if isinstance(abbrev, dict):
        return abbrev.get("default") or abbrev.get("fr") or ""
    return str(abbrev)

def parse_game(game: dict) -> GameResult:
    away = game["awayTeam"]
    home = game["homeTeam"]

    away_score = away.get("score")
    home_score = home.get("score")

    return GameResult(
        game_id=int(game["id"]),
        game_date=str(game["gameDate"]),
        away_team=team_abbrev(away),
        home_team=team_abbrev(home),
        away_score=int(away_score) if away_score is not None else 0,
        home_score=int(home_score) if home_score is not None else 0,
        last_period_type=extract_last_period_type(game),
    )

def split_completed_and_remaining_games(season: str) -> Tuple[List[GameResult], List[GameResult], List[str], Dict[str, dict]]:
    raw_games = fetch_all_games_raw(season)

    completed: List[GameResult] = []
    remaining: List[GameResult] = []

    teams, team_info = get_season_teams_and_info(season)

    for game in raw_games:
        if game.get("gameType") != 2:
            continue

        parsed = parse_game(game)

        if is_completed_regular_season_game(game):
            completed.append(parsed)
        else:
            remaining.append(parsed)

    completed.sort(key=lambda g: (g.game_date, g.game_id))
    remaining.sort(key=lambda g: (g.game_date, g.game_id))
    return completed, remaining, teams, team_info
