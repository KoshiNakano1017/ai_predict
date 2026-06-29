"""マスタテーブル (競走馬・騎手・調教師) から補完情報を取得する。"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from extract.sqlite_client import query_to_df

logger = logging.getLogger(__name__)

TABLE_HORSE = "JV競走馬マスタ"
TABLE_JOCKEY = "JV騎手マスタ"
TABLE_TRAINER = "JV調教師マスタ"


def fetch_horse_master(conn, horse_keys: List[str]) -> pd.DataFrame:
    """競走馬マスタから生年月日・性別を取得する。"""
    if not horse_keys:
        return pd.DataFrame()

    placeholders = ",".join("?" * len(horse_keys))
    sql = f"""
        SELECT 血統登録番号, 生年月日, 性別
        FROM [{TABLE_HORSE}]
        WHERE 血統登録番号 IN ({placeholders})
    """
    df = query_to_df(conn, sql, tuple(horse_keys))
    df = df.rename(columns={"血統登録番号": "horse_key", "生年月日": "birth_date", "性別": "horse_sex_code"})

    from transform.feature_mapper import SEX_MAP
    df["horse_sex"] = df["horse_sex_code"].astype(str).map(SEX_MAP)
    logger.info("[extract_masters] 競走馬マスタ: %d 件", len(df))
    return df


def fetch_jockey_stats(conn, race_keys: List[str]) -> pd.DataFrame:
    """騎手成績から勝率を計算する。

    >> 将来: JV馬毎の実績から競馬場×騎手の勝率を集計する予定。
       MVP では騎手マスタの基本情報取得に留める。
    """
    # MVP: 騎手名のみ取得 (勝率は JV馬毎の過去実績から集計が必要 - Phase 1.5)
    sql = f"SELECT 騎手コード, 騎手名 FROM [{TABLE_JOCKEY}]"
    try:
        df = query_to_df(conn, sql)
        df = df.rename(columns={"騎手コード": "jockey_code", "騎手名": "jockey_name"})
        return df
    except Exception as exc:
        logger.warning("[extract_masters] 騎手マスタ取得失敗: %s", exc)
        return pd.DataFrame()


def fetch_trainer_stats(conn) -> pd.DataFrame:
    """調教師成績から勝率を取得する。

    >> 将来: 調教師の競馬場別・コース別勝率を集計する予定。
    """
    sql = f"SELECT 調教師コード, 調教師名 FROM [{TABLE_TRAINER}]"
    try:
        df = query_to_df(conn, sql)
        df = df.rename(columns={"調教師コード": "trainer_code", "調教師名": "trainer_name"})
        return df
    except Exception as exc:
        logger.warning("[extract_masters] 調教師マスタ取得失敗: %s", exc)
        return pd.DataFrame()
