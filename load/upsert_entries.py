"""races / entries テーブルへのベースデータ投入と、predictions の更新。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from load.supabase_client import upsert, Client

logger = logging.getLogger(__name__)


def upsert_races(client: Client, df_races: pd.DataFrame, retry_count: int = 3) -> None:
    """races テーブルに Upsert する。"""
    cols = [
        "race_key", "target_date", "venue", "race_no", "track_type",
        "race_distance", "track_condition", "weather", "num_horses",
        "straight_distance", "prize_money_1st", "start_time", "race_class_code",
    ]
    records = _to_records(df_races, cols)
    upsert(client, "races", records, on_conflict="race_key", retry_count=retry_count)


def upsert_entries_base(client: Client, df_entries: pd.DataFrame, retry_count: int = 3) -> None:
    """entries テーブルにベースデータ (基本情報 + 特徴量) を Upsert する。"""
    cols = [
        "entry_key", "race_key", "horse_number", "frame_number", "horse_key",
        "horse_name", "jockey_code", "jockey_name", "trainer_code", "trainer_name",
        "horse_weight", "horse_weight_diff", "carrying_weight", "horse_age", "horse_sex",
        # AI features
        "avg_finish_3", "avg_finish_5", "avg_popularity_3",
        "place_rate_track", "place_rate_course", "place_rate_distance", "turn_aptitude",
        "position_index", "position_index_rank", "predicted_running_style",
        "top5_4c_rate", "top3_finish_rate", "pci",
        "rest_weeks", "runs_since_return", "distance_change",
        "weight_correction", "weight_correction_finish",
        "win_recovery_rate", "place_recovery_rate",
        "slope_1_4f", "slope_1_1f", "slope_2_4f",
        "wood_1_4f", "wood_1_1f",
        "win_odds", "popularity_rank", "place_odds_low", "place_odds_high",
        "user_index_1", "finish_position",
        "odds_snapshot_at",
    ]
    records = _to_records(df_entries, cols)
    upsert(client, "entries", records, on_conflict="entry_key", retry_count=retry_count)


def upsert_predictions(
    client: Client,
    df_predictions: pd.DataFrame,
    retry_count: int = 3,
) -> None:
    """entries テーブルの AI 予測列を Upsert する。

    NOTE: PostgreSQL の `INSERT ... ON CONFLICT` は INSERT 試行段階で NOT NULL
    制約を評価するため、entries の必須列 (race_key, horse_number) を records に
    含めないと「null value in column race_key」エラーになる。
    そのため predictions だけ更新する場合でもこれらは送信する必要がある。
    """
    cols = [
        # NOT NULL 必須列（INSERT 経路で必要）
        "entry_key", "race_key", "horse_number",
        # 予測列
        "win_rate", "place_rate", "show_rate",
        "expected_value_win", "expected_value_place",
        "star_rating", "ai_comment",
    ]
    records = _to_records(df_predictions, cols)
    upsert(client, "entries", records, on_conflict="entry_key", retry_count=retry_count)


def _to_records(df: pd.DataFrame, cols: List[str]) -> List[Dict[str, Any]]:
    """DataFrame から指定列のみを抽出し records リストに変換する。

    NaN は Supabase の JSON 投入で `Out of range float values are not JSON compliant`
    エラーになるため None に置換する。
    float dtype のまま `.where(notna, None)` すると None が NaN に戻ってしまうため、
    一度 object 型に変換してから where で置換する必要がある。
    """
    present = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        logger.debug("[upsert] 列不足 (スキップ): %s", missing)
    sub = df[present].copy().astype(object)
    sub = sub.where(pd.notna(sub), None)
    return sub.to_dict(orient="records")
