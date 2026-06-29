"""transform/feature_mapper.py のユニットテスト。"""
from transform.feature_mapper import (
    map_race_columns, map_entry_columns, map_odds_columns,
    KEIBAJO_CODE_MAP, TRACK_TYPE_MAP,
)


def test_map_race_columns_basic():
    row = {
        "開催年": "2026",
        "開催月日": "0330",
        "競馬場": "05",
        "距離": 1600,
        "（芝ダ）区分": "1",
        "芝馬場状態": "1",
        "天候": "1",
        "出走頭数": 16,
    }
    result = map_race_columns(row)
    assert result["race_distance"] == 1600
    assert result["track_type"] == "芝"
    assert result["venue"] == "東京"
    assert result["track_condition"] == "良"


def test_map_race_columns_dirt():
    row = {"（芝ダ）区分": "2", "競馬場": "09", "芝馬場状態": None, "ダ馬場状態": "2"}
    result = map_race_columns(row)
    assert result["track_type"] == "ダート"
    assert result["venue"] == "阪神"
    assert result["track_condition"] == "稍重"


def test_map_entry_columns():
    row = {
        "血統登録番号": "ABC123",
        "馬番": 3,
        "枠番": 2,
        "斤量": 55.0,
        "馬体重": 480,
        "馬体重増減": 4,
        "平均着順_前3走": 2.3,
        "PCI": 52.1,
    }
    result = map_entry_columns(row)
    assert result["horse_key"] == "ABC123"
    assert result["horse_number"] == 3
    assert result["avg_finish_3"] == 2.3
    assert result["pci"] == 52.1


def test_map_entry_columns_includes_names():
    """JV馬毎レース情報EX に格納されている馬名・騎手名・調教師名・調教師コードを取得できる。

    08_CrossFactor_DB定義書.md JV馬毎レース情報EX:
      17=馬名 / 24=調教師(コード) / 153=騎手名 / 154=調教師名
    """
    row = {
        "血統登録番号": "ABC123",
        "馬番": 1,
        "馬名": "サンプルホース",
        "騎手名": "武豊",
        "調教師": "01001",
        "調教師名": "山田太郎",
    }
    result = map_entry_columns(row)
    assert result["horse_name"] == "サンプルホース"
    assert result["jockey_name"] == "武豊"
    assert result["trainer_code"] == "01001"
    assert result["trainer_name"] == "山田太郎"


def test_map_odds_columns_conversion():
    """DB定義書 JV馬毎レース情報EX「単勝。÷10で入れる。」に従い、DB値を 10 で割る。

    例: DB値 "150" -> 15.0 倍 / DB値 "35" -> 3.5 倍
    """
    row = {
        "発表月日時分": "202603301130",
        "単勝オッズ": "150",
        "複勝オッズ下": "35",
        "複勝オッズ上": "50",
    }
    result = map_odds_columns(row)
    assert result["win_odds"] == 15.0
    assert result["place_odds_low"] == 3.5
    assert result["place_odds_high"] == 5.0


def test_map_odds_columns_invalid_value_returns_none():
    row = {"発表月日時分": "202603301130", "単勝オッズ": "abc"}
    result = map_odds_columns(row)
    assert result["win_odds"] is None
