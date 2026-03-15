from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional, Union
from .models import GameResult

class BaseLeague(ABC):
    def get_available_seasons(self) -> Dict[str, str]:
        """Returns a dict mapping display labels to season IDs (e.g. {'2025/2026': '20252026'})."""
        return {"2025/2026": "20252026", "2024/2025": "20242025", "2023/2024": "20232024"}

    @abstractmethod
    def fetch_games(self, season: str) -> Tuple[List[GameResult], List[GameResult]]:
        """Returns completed games and remaining games for the season."""
        pass

    @abstractmethod
    def build_team_records(self, games: List[GameResult]) -> List[dict]:
        """Calculates records/standings from a list of completed games."""
        pass

    @abstractmethod
    def actual_scores(self, game: GameResult, win_weights: dict) -> Tuple[float, float]:
        """Calculates actual score updates for ELO given game results."""
        pass

    @abstractmethod
    def get_teams(self) -> List[str]:
        """Returns list of teams in the league."""
        pass

    @abstractmethod
    def team_info(self) -> dict:
        """Returns info about teams like conference, division, etc."""
        pass

    @abstractmethod
    def simulate_playoffs(self, records: List[dict], ratings: Dict[str, float], simulations: int, rng, **kwargs) -> List[dict]:
        """Runs monte carlo for playoffs"""
        pass

    @staticmethod
    def _coerce_to_date(value: Union[str, date, datetime]) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Unsupported date value: {value!r}")

        raw = value.strip()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            pass

        try:
            return date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValueError(f"Could not parse game date: {value!r}") from exc

    def sort_games_by_date(self, games: List[GameResult]) -> List[GameResult]:
        dated_games = []
        for game in games:
            dated_games.append((self._coerce_to_date(game.game_date), str(game.game_id), game))
        dated_games.sort(key=lambda item: (item[0], item[1]))
        return [game for _, _, game in dated_games]

    def split_games_by_cutoff(
        self,
        games: List[GameResult],
        cutoff_date: Optional[Union[str, date, datetime]],
    ) -> Tuple[List[GameResult], List[GameResult]]:
        dated_games = []
        for game in games:
            dated_games.append((self._coerce_to_date(game.game_date), str(game.game_id), game))
        dated_games.sort(key=lambda item: (item[0], item[1]))

        if cutoff_date is None:
            return [game for _, _, game in dated_games], []

        cutoff = self._coerce_to_date(cutoff_date)
        on_or_before_cutoff: List[GameResult] = []
        after_cutoff: List[GameResult] = []

        for game_date, _, game in dated_games:
            if game_date <= cutoff:
                on_or_before_cutoff.append(game)
            else:
                after_cutoff.append(game)

        return on_or_before_cutoff, after_cutoff

    def sorted_unique_game_dates(self, games: List[GameResult]) -> List[date]:
        return sorted({self._coerce_to_date(game.game_date) for game in games})
        
    def get_playoff_column_names(self) -> Dict[str, str]:
        """Returns a mapping of internal playoff status keys to league-specific UI column headers.
        Expected keys: make_playoffs, make_qf, make_sf, make_final, win_champ
        """
        return {
            'make_playoffs': 'Make Playoffs',
            'make_qf': 'Quarterfinals',
            'make_sf': 'Semifinals',
            'make_final': 'Finals',
            'win_champ': 'Win Championship'
        }
    
    @abstractmethod
    def apply_simulated_game_to_records(self, records: Dict[str, dict], away_team: str, home_team: str, away_score: int, home_score: int, finish_type: str) -> None:
        """Applies a future simulated game to standings"""
        pass

    @abstractmethod
    def sample_score(self, finish_type: str, rng, home_wins: bool) -> Tuple[int, int]:
        """Returns simulated (away_score, home_score)."""
        pass

    @abstractmethod   
    def estimate_finish_type_probabilities(self, completed_games: List[GameResult]) -> Dict[str, float]:
        """Estimates probability of ending in REG/OT/SO etc."""
        pass
