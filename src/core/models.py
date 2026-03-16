from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

@dataclass
class GameResult:
    game_id: Any
    game_date: str
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    last_period_type: str  # e.g., REG / OT / SO / UNKNOWN
    game_type: str = "REG"  # "REG" = regular season, "PLAYOFF" = post-season

@dataclass
class PlayoffSeed:
    team: str
    conference: str
    division: str
    points: int
    wins: int
    rw: int
    gd: int
    gf: int
    seed_label: str
