"""締め切り直前オッズの選択ロジック。

JVオッズ_単複枠 から発表月日時分 が最大のレコードを選択する。
バックテスト時は「結果確定前の最終時点オッズ」を使い、事後オッズを使わないこと。
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def select_latest_odds(
    df_odds: pd.DataFrame,
    race_key_col: str = "race_key",
    published_at_col: str = "odds_published_at",
    horse_no_col: str = "horse_number",
) -> pd.DataFrame:
    """race_key ごとに発表月日時分が最大のオッズ行を **馬番ごとに** 選択して返す。

    JVオッズ_単複枠 は (race_key, horse_number, published_at) のキー構造のため
    race_key だけで drop_duplicates するとレース1行に潰れて全馬のオッズが消える。

    Args:
        df_odds: オッズデータ (race_key, horse_number, odds_published_at, win_odds, ... を含む)
        race_key_col: レースキー列名
        published_at_col: 発表日時列名 (YYYYMMDDHHMM 形式の文字列 or 整数)
        horse_no_col: 馬番列名

    Returns:
        race_key x 馬番 ごとに1行に絞ったオッズ DataFrame
    """
    if df_odds.empty:
        return df_odds

    # 発表日時を文字列として比較 (YYYYMMDDHHMM は辞書順 = 時刻順)
    df = df_odds.copy()
    df[published_at_col] = df[published_at_col].astype(str)

    # race_key ごとに最大 published_at を持つ行のみ残す
    idx = df.groupby(race_key_col)[published_at_col].transform("max") == df[published_at_col]
    latest = df[idx]

    # 馬番がある場合は (race_key, horse_number) で重複排除、なければ race_key
    if horse_no_col in latest.columns:
        result = latest.drop_duplicates(subset=[race_key_col, horse_no_col])
    else:
        result = latest.drop_duplicates(subset=[race_key_col])

    skipped = df[~idx][race_key_col].nunique()
    if skipped:
        logger.info("[odds_selector] %d レースは古い時点のオッズ行をスキップしました", skipped)

    return result.reset_index(drop=True)


def validate_odds_before_result(
    df_odds: pd.DataFrame,
    df_results: pd.DataFrame,
    published_at_col: str = "odds_published_at",
    result_at_col: str = "result_at",
    race_key_col: str = "race_key",
) -> pd.DataFrame:
    """選択したオッズが結果確定後のものでないことを検証する (バックテスト用)。

    レース結果確定日時より後に発表されたオッズを警告し除外する。
    """
    if result_at_col not in df_results.columns:
        logger.debug("[odds_selector] result_at 列がないためオッズ時点検証をスキップ")
        return df_odds

    merged = df_odds.merge(
        df_results[[race_key_col, result_at_col]],
        on=race_key_col,
        how="left",
    )
    merged[published_at_col] = merged[published_at_col].astype(str)
    merged[result_at_col] = merged[result_at_col].astype(str)

    leaked = merged[merged[published_at_col] > merged[result_at_col]]
    if not leaked.empty:
        logger.warning(
            "[odds_selector] データリーク検知: %d 件のオッズが結果確定後の時点です。除外します。",
            len(leaked),
        )
        df_odds = df_odds[~df_odds[race_key_col].isin(leaked[race_key_col])]

    return df_odds
