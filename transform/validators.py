"""バリデーション: 件数・主キー重複・必須列・型チェック。

ハード必須列が1件でも欠損したら ValueError を上げる。
重要特徴量の欠損率がしきい値を超えたら ValueError を上げる。
補助特徴量の欠損は WARNING に留めてパイプラインを継続する。
"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)

# --- 列種別定義 (12_抽出スクリプト設計書.md §11.3) ---
HARD_REQUIRED = ["race_key", "entry_key", "horse_key", "horse_number"]
IMPORTANT_FEATURES = ["win_odds", "avg_finish_3"]
IMPORTANT_MISSING_THRESHOLD = 0.30  # 欠損率30%超で失敗


def check_race_count(df: pd.DataFrame, min_count: int = 1) -> None:
    if len(df) < min_count:
        raise ValueError(f"レース抽出件数が {min_count} 件未満です: {len(df)} 件")
    logger.info("[validators] races_count=%d", len(df))


def check_entry_count(df_entries: pd.DataFrame, df_races: pd.DataFrame) -> None:
    if len(df_entries) == 0:
        raise ValueError("出走馬抽出件数が 0 件です")
    # 出走頭数との乖離チェック
    if "num_horses" in df_races.columns and "race_key" in df_races.columns:
        # SQLite 由来で str のことがあるため数値化してから比較する
        expected_series = pd.to_numeric(
            df_races.set_index("race_key")["num_horses"], errors="coerce"
        )
        expected = expected_series.to_dict()
        actual = df_entries.groupby("race_key").size().to_dict()
        for rk, exp in expected.items():
            if pd.isna(exp):
                continue
            exp_int = int(exp)
            act = int(actual.get(rk, 0))
            if exp_int and abs(act - exp_int) > 2:
                logger.warning(
                    "[validators] 出走頭数乖離: race_key=%s expected=%d actual=%d",
                    rk, exp_int, act,
                )
    logger.info("[validators] entries_count=%d", len(df_entries))


def check_duplicate_keys(df: pd.DataFrame, key_col: str) -> None:
    dupes = df[df.duplicated(subset=[key_col])]
    if not dupes.empty:
        raise ValueError(f"{key_col} に {len(dupes)} 件の重複があります: {dupes[key_col].tolist()[:5]}")


def check_hard_required(df: pd.DataFrame) -> None:
    for col in HARD_REQUIRED:
        if col not in df.columns:
            raise ValueError(f"ハード必須列 {col!r} が存在しません")
        missing = df[col].isna().sum()
        if missing > 0:
            raise ValueError(f"ハード必須列 {col!r} に {missing} 件の欠損があります")


def check_important_features(df: pd.DataFrame) -> None:
    n = len(df)
    if n == 0:
        return
    for col in IMPORTANT_FEATURES:
        if col not in df.columns:
            logger.warning("[validators] 重要特徴量 %s が列に存在しません", col)
            continue
        missing_rate = df[col].isna().sum() / n
        if missing_rate > IMPORTANT_MISSING_THRESHOLD:
            raise ValueError(
                f"重要特徴量 {col!r} の欠損率が {missing_rate:.1%} で閾値 {IMPORTANT_MISSING_THRESHOLD:.0%} を超えています"
            )
        if missing_rate > 0:
            logger.warning("[validators] missing_feature col=%s rate=%.1f%%", col, missing_rate * 100)


def check_dtypes(df: pd.DataFrame, numeric_cols: List[str]) -> None:
    for col in numeric_cols:
        if col not in df.columns:
            continue
        non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
        if non_numeric.any():
            logger.warning("[validators] 数値列 %s に文字列混入: %d 件", col, non_numeric.sum())


def run_all(
    df_races: pd.DataFrame,
    df_entries: pd.DataFrame,
) -> None:
    """全バリデーションを実行する。エラーがあれば例外を上げる。"""
    check_race_count(df_races)
    check_entry_count(df_entries, df_races)
    check_duplicate_keys(df_races, "race_key")
    check_duplicate_keys(df_entries, "entry_key")
    check_hard_required(df_entries)
    check_important_features(df_entries)
    numeric_cols = ["win_odds", "avg_finish_3", "avg_finish_5", "horse_weight", "carrying_weight"]
    check_dtypes(df_entries, numeric_cols)
    logger.info("[validators] 全バリデーション通過")
