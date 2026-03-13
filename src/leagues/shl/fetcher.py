import requests
import time
from typing import List, Tuple, Dict
from src.core.models import GameResult
from functools import lru_cache

@lru_cache(maxsize=1)
def get_shl_seasons() -> Dict[str, str]:
    url = f"https://www.shl.se/api/sports-v2/season-series-game-types-filter?series=qQ9-bb0bzEWUk&_t={int(time.time())}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        seasons = {}
        for s in data.get("season", []):
            uuid = s.get("uuid")
            names = s.get("names", [])
            translation = s.get("code")
            for n in names:
                if n.get("language") == "sv":
                    translation = n.get("translation")
                    break
            if uuid and translation:
                seasons[translation] = uuid
        return seasons
    except Exception:
        # Fallback cache if request fails
        return {"2025/2026": "xs4m9qupsi", "2024/2025": "qeb-73bZkIm9A"}

def fetch_shl_games(season_uuid: str = "xs4m9qupsi") -> Tuple[List[GameResult], List[GameResult], List[str], Dict]:
    game_types = ["qQ9-af37Ti40B", "qQ9-7debq38kX", "qRf-347BaDIOc"]
    games_data = []

    for gt in game_types:
        url = f"https://www.shl.se/api/sports-v2/game-schedule?seasonUuid={season_uuid}&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid={gt}&gamePlace=all&played=all&_t={int(time.time())}"
        
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        games_data.extend(data.get("gameInfo", []))
    
    # Sort games by startDateTime chronologically just in case types overlap weirdly
    games_data.sort(key=lambda x: x.get("startDateTime", ""))
    
    completed_games = []
    remaining_games = []
    out_team_info = {}
    
    for g in games_data:
        ht = g.get("homeTeamInfo", {})
        at = g.get("awayTeamInfo", {})
        home_team = ht.get("code")
        away_team = at.get("code")
        
        if not home_team or not away_team:
            continue
            
        if home_team not in out_team_info:
            out_team_info[home_team] = {
                "name": ht.get("names", {}).get("long", home_team),
                "conference": "SHL",
                "division": "SHL"
            }
        if away_team not in out_team_info:
            out_team_info[away_team] = {
                "name": at.get("names", {}).get("long", away_team),
                "conference": "SHL",
                "division": "SHL"
            }
            
        date_str = g.get("startDateTime", "")
        # You could also use rawStartDateTime for parsing
        game_id = g.get("uuid", "")
        state = g.get("state", "pre-game")
        
        is_completed = (state == "post-game")
        
        if is_completed:
            home_score = ht.get("score", 0)
            away_score = at.get("score", 0)
            
            # Use safety fallback to 0 if it returns 'N/A' incorrectly, though state should guard this
            if not isinstance(home_score, int):
                try: home_score = int(home_score)
                except ValueError: home_score = 0
            if not isinstance(away_score, int):
                try: away_score = int(away_score)
                except ValueError: away_score = 0
                
            so = g.get("shootout", False)
            ot = g.get("overtime", False)
            
            decided_in = "REG"
            if so:
                decided_in = "SO"
            elif ot:
                decided_in = "OT"
                
            game_obj = GameResult(
                game_id=game_id,
                game_date=date_str,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                last_period_type=decided_in
            )
            completed_games.append(game_obj)
        else:
            game_obj = GameResult(
                game_id=game_id,
                game_date=date_str,
                home_team=home_team,
                away_team=away_team,
                home_score=0,
                away_score=0,
                last_period_type="UNKNOWN"
            )
            remaining_games.append(game_obj)
            
    completed_games.sort(key=lambda g: g.game_date)
    remaining_games.sort(key=lambda g: g.game_date)
    
    teams = list(out_team_info.keys())
            
    return completed_games, remaining_games, teams, out_team_info
