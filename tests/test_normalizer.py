"""transform/normalizer.py のユニットテスト。

要件定義書 §16.1 の「欠損補完ルールが正しいか」に対応する。
"""
import pandas as pd
import pytest

from transform.normalizer import (
    fill_missing,
    encode_categoricals,
    calc_horse_age,
)


def test_fill_missing_training_columns_add_missing_flag():
    """調教データが欠損している場合は -999 で埋め、_missing フラグを立てる。"""
    df = pd.DataFrame({
        "slope_1_4f": [52.3, None, 51.8],
        "slope_1_1f": [12.1, 12.5, None],
    })
    result = fill_missing(df)

    assert result.loc[0, "slope_1_4f"] == 52.3
    assert result.loc[1, "slope_1_4f"] == -999
    assert result.loc[2, "slope_1_4f"] == 51.8

    assert result.loc[0, "slope_1_4f_missing"] == 0
    assert result.loc[1, "slope_1_4f_missing"] == 1
    assert result.loc[2, "slope_1_4f_missing"] == 0

    assert result.loc[2, "slope_1_1f_missing"] == 1


def test_fill_missing_debut_horse_uses_mean_and_flags():
    """過去成績の欠損 (デビュー戦) は平均値で埋め、is_debut フラグを立てる。"""
    df = pd.DataFrame({
        "avg_finish_3": [3.0, 5.0, None],
        "avg_finish_5": [4.0, 6.0, None],
        "avg_popularity_3": [2.0, 4.0, None],
    })
    result = fill_missing(df)

    assert result.loc[2, "avg_finish_3"] == pytest.approx(4.0)
    assert result.loc[2, "avg_finish_5"] == pytest.approx(5.0)
    assert result.loc[0, "is_debut"] == 0
    assert result.loc[2, "is_debut"] == 1


def test_fill_missing_aptitude_columns_filled_with_zero():
    """適性スコア・回収率の欠損は 0 で補完する。"""
    df = pd.DataFrame({
        "place_rate_track": [0.6, None],
        "win_recovery_rate": [None, 1.2],
    })
    result = fill_missing(df)
    assert result.loc[1, "place_rate_track"] == 0
    assert result.loc[0, "win_recovery_rate"] == 0


def test_encode_categoricals_running_style():
    df = pd.DataFrame({"predicted_running_style": ["逃", "先", "差", "追", None]})
    result = encode_categoricals(df)
    assert list(result["predicted_running_style"]) == [1, 2, 3, 4, 0]


def test_encode_categoricals_track_condition_and_type():
    df = pd.DataFrame({
        "track_condition": ["良", "稍重", "重", "不良"],
        "track_type": ["芝", "ダート", "障害", "芝"],
        "horse_sex": ["牡", "牝", "騸", None],
    })
    result = encode_categoricals(df)
    assert list(result["track_condition"]) == [0, 1, 2, 3]
    assert list(result["track_type"]) == [0, 1, 2, 0]
    assert list(result["horse_sex"]) == [0, 1, 2, 0]


def test_calc_horse_age_basic():
    df = pd.DataFrame({"birth_date": ["20230401", "20210315"]})
    result = calc_horse_age(df, "2026-04-01")
    assert result.loc[0, "horse_age"] == 3
    assert result.loc[1, "horse_age"] == 5


def test_calc_horse_age_missing_column_is_safe():
    """birth_date 列がない場合は何もせず返す。"""
    df = pd.DataFrame({"horse_key": ["A"]})
    result = calc_horse_age(df, "2026-04-01")
    assert "horse_age" not in result.columns


def test_calc_horse_age_invalid_value_returns_none():
    df = pd.DataFrame({"birth_date": ["bad-date"]})
    result = calc_horse_age(df, "2026-04-01")
    assert pd.isna(result.loc[0, "horse_age"])
