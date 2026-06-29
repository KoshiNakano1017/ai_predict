"""transform/odds_selector.py のユニットテスト。"""
import pandas as pd
import pytest
from transform.odds_selector import select_latest_odds


def _make_odds(data):
    return pd.DataFrame(data)


def test_select_latest_basic():
    df = _make_odds({
        "race_key": ["AAA", "AAA", "BBB", "BBB"],
        "horse_number": [1, 1, 2, 2],
        "odds_published_at": ["202603301100", "202603301130", "202603301100", "202603301120"],
        "win_odds": [3.0, 3.2, 5.0, 4.8],
    })
    result = select_latest_odds(df)
    assert len(result) == 2
    aaa = result[result["race_key"] == "AAA"].iloc[0]
    assert aaa["odds_published_at"] == "202603301130"
    assert aaa["win_odds"] == 3.2


def test_select_latest_empty():
    df = pd.DataFrame(columns=["race_key", "odds_published_at", "win_odds"])
    result = select_latest_odds(df)
    assert result.empty


def test_select_latest_single_race():
    df = _make_odds({
        "race_key": ["AAA"],
        "horse_number": [1],
        "odds_published_at": ["202603301100"],
        "win_odds": [2.5],
    })
    result = select_latest_odds(df)
    assert len(result) == 1
