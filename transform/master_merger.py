"""マスタテーブルから名称列をフォールバック補完するヘルパー。

JV馬毎レース情報EX には騎手名 / 調教師名が直接格納されているが、
古いレコードや特殊ケースで欠損する場合があるため、マスタ値で穴埋めする。
"""
from __future__ import annotations

import pandas as pd


def merge_master_name(
    df_entries: pd.DataFrame,
    df_master: pd.DataFrame,
    key: str,
    name_col: str,
) -> pd.DataFrame:
    """マスタテーブルから ``name_col`` をフォールバック補完して返す。

    Args:
        df_entries: 出走馬データ。``key`` 列を含む。
        df_master: マスタデータ。``key`` と ``name_col`` を含む。
        key: 結合キー (例: ``"jockey_code"`` / ``"trainer_code"``)。
        name_col: 補完する名称列 (例: ``"jockey_name"``)。

    Returns:
        補完後の DataFrame。元データに値があればそれを優先し、
        欠損時のみマスタ値で埋める。マスタが空 / キー欠落時は無加工で返す。
    """
    if df_master.empty or key not in df_entries.columns or key not in df_master.columns:
        return df_entries
    if name_col not in df_master.columns:
        return df_entries

    merged = df_entries.merge(
        df_master[[key, name_col]].drop_duplicates(subset=[key]),
        on=key,
        how="left",
        suffixes=("", "_master"),
    )

    master_col = f"{name_col}_master"
    if master_col in merged.columns:
        if name_col not in df_entries.columns:
            merged[name_col] = merged[master_col]
        else:
            merged[name_col] = merged[name_col].fillna(merged[master_col])
        merged = merged.drop(columns=[master_col])
    return merged
