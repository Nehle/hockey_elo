import os

import pytest

from src.leagues.nhl.league import NHLLeague
from src.leagues.shl.league import SHLLeague


RUN_NETWORK_TESTS = os.getenv("RUN_NETWORK_TESTS") == "1"
pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(not RUN_NETWORK_TESTS, reason="Set RUN_NETWORK_TESTS=1 to run network smoke tests."),
]


def test_nhl_fetch_games_smoke():
    league = NHLLeague()
    completed, remaining = league.fetch_games("20232024")
    assert len(completed) > 0
    assert len(completed) + len(remaining) > 0
    assert len(league.get_teams()) >= 30


def test_shl_season_and_fetch_smoke():
    league = SHLLeague()
    seasons = league.get_available_seasons()
    assert seasons

    first_season_id = next(iter(seasons.values()))
    completed, remaining = league.fetch_games(first_season_id)
    assert len(completed) + len(remaining) > 0
    assert len(league.get_teams()) > 0
