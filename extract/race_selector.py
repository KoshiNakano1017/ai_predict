"""対象レースの絞り込みと差分判定。

対象日の JRA レース (地方競馬除外) を選定する。
"""
from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

from extract.sqlite_client import query_to_df

logger = logging.getLogger(__name__)

# JRA 競馬場コード (01-10)。これ以外は地方競馬として除外する。
JRA_KEIBAJO_CODES = {f"{i:02d}" for i in range(1, 11)}

# テーブル名 (CrossFactor SQLite の実テーブル名に合わせること)
TABLE_RACE = "JVレース詳細EX"
TABLE_SCHEDULE = "JV開催スケジュール"


def get_target_races(
    conn,
    target_date: str,  # YYYY-MM-DD 形式
    mode: str,
) -> pd.DataFrame:
    """対象日の JRA レース一覧を返す。

    Args:
        conn: SQLite 接続
        target_date: 対象日 (YYYY-MM-DD)
        mode: バッチモード

    Returns:
        対象レース DataFrame (race_key 付き)
    """
    # YYYY-MM-DD -> YYYYMMDD
    date_str = target_date.replace("-", "")
    year = date_str[:4]
    mmdd = date_str[4:]

    sql = f"""
        SELECT *
        FROM [{TABLE_RACE}]
        WHERE 開催年 = ? AND 開催月日 = ?
        ORDER BY 競馬場, 番号
    """
    df = query_to_df(conn, sql, (year, mmdd))

    if df.empty:
        logger.warning("[race_selector] 対象日レースなし: %s", target_date)
        return df

    # 地方競馬除外: 競馬場コードが JRA 以外
    df["keibajo_str"] = df["競馬場"].astype(str).str.zfill(2)
    before = len(df)
    df = df[df["keibajo_str"].isin(JRA_KEIBAJO_CODES)].reset_index(drop=True)
    excluded = before - len(df)
    if excluded:
        logger.info("[race_selector] 地方競馬除外: %d 件", excluded)

    logger.info("[race_selector] races_selected count=%d target_date=%s", len(df), target_date)
    return df


def filter_diff(
    df_races: pd.DataFrame,
    processed_race_keys: set,
    mode: str,
) -> pd.DataFrame:
    """差分更新: チェックポイントで処理済みの race_key を除外する。

    retry_failed モードでは全件対象にする。
    """
    if mode == "retry_failed":
        logger.info("[race_selector] retry_failed モード: 全 %d 件を対象にします", len(df_races))
        return df_races

    if not processed_race_keys:
        return df_races

    before = len(df_races)
    df_races = df_races[~df_races["race_key"].isin(processed_race_keys)].reset_index(drop=True)
    skipped = before - len(df_races)
    if skipped:
        logger.info("[race_selector] 差分: %d 件はチェックポイント済みでスキップ", skipped)
    return df_races
