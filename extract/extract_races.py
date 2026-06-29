"""JVレース詳細EX からレース基本情報を抽出し race_key を付与する。"""
from __future__ import annotations

import logging

import pandas as pd

from extract.sqlite_client import query_to_df
from transform.key_builder import build_race_key
from transform.feature_mapper import map_race_columns

logger = logging.getLogger(__name__)

TABLE = "JVレース詳細EX"


def extract(conn, target_date: str) -> pd.DataFrame:
    """対象日のレース情報を抽出して内部列名に変換し race_key を付与する。"""
    date_str = target_date.replace("-", "")
    year = date_str[:4]
    mmdd = date_str[4:]

    sql = f"""
        SELECT *
        FROM [{TABLE}]
        WHERE 開催年 = ? AND 開催月日 = ?
        ORDER BY 競馬場, 番号
    """
    raw = query_to_df(conn, sql, (year, mmdd))
    if raw.empty:
        logger.warning("[extract_races] 対象日レースなし: %s", target_date)
        return raw

    rows = []
    for _, row in raw.iterrows():
        mapped = map_race_columns(dict(row))
        mapped["target_date"] = target_date

        race_key = build_race_key(
            kai_nen=row.get("開催年", year),
            kai_tsuki_hi=row.get("開催月日", mmdd),
            keibajo=row.get("競馬場", ""),
            kai=row.get("開催回", ""),
            nichi_me=row.get("開催日目", ""),
            race_no=row.get("番号", ""),
        )
        mapped["race_key"] = race_key
        rows.append(mapped)

    df = pd.DataFrame(rows)
    logger.info("[extract_races] 抽出完了 count=%d", len(df))
    return df
