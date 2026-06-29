"""SQLite から抽出した DataFrame を VM 内 PostgreSQL の raw_* テーブルへ投入する。

冪等保証: INSERT ... ON CONFLICT (primary_key) DO UPDATE SET ... で実現。
重複実行しても結果が変わらない。
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import psycopg2.extras

from db.postgres_client import get_conn

logger = logging.getLogger(__name__)

# Supabase へ送らない VM 専用の races 列（SQLiteと共通の基本列のみ）
_RACE_COLS = [
    "race_key", "target_date", "venue", "race_no", "track_type",
    "race_distance", "track_condition", "weather", "num_horses",
    "straight_distance", "prize_money_1st", "start_time", "race_class_code",
]

_ENTRY_COLS = [
    "entry_key", "race_key", "horse_number", "frame_number", "horse_key",
    "horse_name", "jockey_code", "jockey_name", "trainer_code", "trainer_name",
    "horse_weight", "horse_weight_diff", "carrying_weight", "horse_age", "horse_sex",
    "avg_finish_3", "avg_finish_5", "avg_popularity_3",
    "place_rate_track", "place_rate_course", "place_rate_distance",
    "turn_aptitude", "position_index", "position_index_rank", "predicted_running_style",
    "top5_4c_rate", "top3_finish_rate", "pci",
    "rest_weeks", "runs_since_return", "distance_change",
    "weight_correction", "weight_correction_finish",
    "win_recovery_rate", "place_recovery_rate",
    "slope_1_4f", "slope_1_1f", "slope_2_4f",
    "wood_1_4f", "wood_1_1f",
    "win_odds", "popularity_rank", "place_odds_low", "place_odds_high",
    "odds_snapshot_at",
    "jockey_win_rate_all", "jockey_win_rate_course", "trainer_win_rate_all",
    "jockey_change", "user_index_1", "finish_position",
]


def _df_to_records(df: pd.DataFrame, cols: list[str]) -> list[dict[str, Any]]:
    """指定列のみを抽出して records リストに変換（欠損列はスキップ）。"""
    present = [c for c in cols if c in df.columns]
    missing = set(cols) - set(present)
    if missing:
        logger.debug("[vm_loader] 列不足（スキップ）: %s", sorted(missing))
    sub = df[present].where(pd.notna(df[present]), None)
    return sub.to_dict(orient="records")


def _upsert_batch(
    cur: Any,
    table: str,
    records: list[dict[str, Any]],
    pk: str | list[str],
) -> int:
    """psycopg2 で execute_values を使った高速 upsert。"""
    if not records:
        return 0

    cols = list(records[0].keys())
    pks = [pk] if isinstance(pk, str) else pk
    update_cols = [c for c in cols if c not in pks]

    col_list = ", ".join(f'"{c}"' for c in cols)
    placeholder = "(" + ", ".join(["%s"] * len(cols)) + ")"
    conflict_target = ", ".join(f'"{c}"' for c in pks)
    updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)

    sql = (
        f'INSERT INTO {table} ({col_list}) VALUES %s '
        f'ON CONFLICT ({conflict_target}) DO UPDATE SET {updates}'
    )
    values = [tuple(r.get(c) for c in cols) for r in records]
    psycopg2.extras.execute_values(cur, sql, values, template=placeholder)
    return len(records)


def load_raw_races(df_races: pd.DataFrame) -> int:
    """raw_races テーブルへ upsert する。投入件数を返す。"""
    records = _df_to_records(df_races, _RACE_COLS)
    if not records:
        logger.warning("[vm_loader] raw_races: 投入対象なし")
        return 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            count = _upsert_batch(cur, "raw_races", records, pk="race_key")

    logger.info("[vm_loader] raw_races upsert 完了: %d 件", count)
    return count


def load_raw_entries(df_entries: pd.DataFrame) -> int:
    """raw_entries テーブルへ upsert する。投入件数を返す。"""
    records = _df_to_records(df_entries, _ENTRY_COLS)
    if not records:
        logger.warning("[vm_loader] raw_entries: 投入対象なし")
        return 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            count = _upsert_batch(cur, "raw_entries", records, pk="entry_key")

    logger.info("[vm_loader] raw_entries upsert 完了: %d 件", count)
    return count


def load_features(df_entries: pd.DataFrame) -> int:
    """features テーブルへ特徴量 JSONB を upsert する。

    feature_data に全列を JSON として格納するため、推論コードとの疎結合を保つ。
    """
    if df_entries.empty:
        return 0

    records = []
    for _, row in df_entries.iterrows():
        records.append({
            "entry_key": row["entry_key"],
            "race_key": row["race_key"],
            "feature_data": row.drop(["entry_key", "race_key"]).where(
                pd.notna(row.drop(["entry_key", "race_key"])), None
            ).to_dict(),
        })

    with get_conn() as conn:
        with conn.cursor() as cur:
            cols = ["entry_key", "race_key", "feature_data"]
            col_list = ", ".join(f'"{c}"' for c in cols)
            sql = (
                f'INSERT INTO features ({col_list}) VALUES %s '
                f'ON CONFLICT (entry_key) DO UPDATE SET '
                f'"race_key" = EXCLUDED."race_key", '
                f'"feature_data" = EXCLUDED."feature_data", '
                f'"updated_at" = now()'
            )
            values = [
                (r["entry_key"], r["race_key"],
                 psycopg2.extras.Json(r["feature_data"]))
                for r in records
            ]
            psycopg2.extras.execute_values(cur, sql, values)

    logger.info("[vm_loader] features upsert 完了: %d 件", len(records))
    return len(records)


def load_predictions_staging(df_pred: pd.DataFrame, model_version: str) -> int:
    """predictions_staging テーブルへ推論結果を upsert する。"""
    if df_pred.empty:
        return 0

    col_map = {
        "win_rate": "win_prob",
        "place_rate": "top2_prob",
        "show_rate": "top3_prob",
    }
    df = df_pred.rename(columns=col_map)

    cols = [
        "entry_key", "race_key", "model_version",
        "win_prob", "top2_prob", "top3_prob",
        "expected_value_win", "expected_value_place",
        "star_rating", "ai_comment",
    ]
    records = _df_to_records(df, cols)
    for r in records:
        r["model_version"] = model_version

    with get_conn() as conn:
        with conn.cursor() as cur:
            count = _upsert_batch(
                cur, "predictions_staging", records,
                pk=["entry_key", "inference_at"],
            )

    logger.info("[vm_loader] predictions_staging upsert 完了: %d 件", count)
    return count


def mark_job_start(job_name: str, target_date: str, mode: str, model_version: str, log_path: str) -> int:
    """job_runs に実行開始レコードを挿入し、id を返す。"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_runs (job_name, target_date, mode, model_version, log_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (job_name, target_date, mode, model_version, log_path),
            )
            row = cur.fetchone()
    job_id = row[0]
    logger.info("[vm_loader] job_runs 開始登録: id=%d", job_id)
    return job_id


def mark_job_done(
    job_id: int,
    status: str,
    rows_raw_races: int = 0,
    rows_raw_entries: int = 0,
    rows_features: int = 0,
    rows_predictions: int = 0,
    rows_published: int = 0,
    error_message: str | None = None,
) -> None:
    """job_runs の完了情報を更新する。"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE job_runs SET
                    finished_at      = now(),
                    status           = %s,
                    rows_raw_races   = %s,
                    rows_raw_entries = %s,
                    rows_features    = %s,
                    rows_predictions = %s,
                    rows_published   = %s,
                    error_message    = %s
                WHERE id = %s
                """,
                (status, rows_raw_races, rows_raw_entries, rows_features,
                 rows_predictions, rows_published, error_message, job_id),
            )
    logger.info("[vm_loader] job_runs 更新: id=%d status=%s", job_id, status)
