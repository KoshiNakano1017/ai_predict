"""predictions_staging → Supabase 最終公開テーブルへの反映レイヤー。

【安全制約】
- 送信するのは AI 予測最終成果物カラムのみ。
- Auth / plan / RLS 関連テーブルには絶対に触れない。
- Upsert キー: entry_key（単独）で entries テーブルの予測列のみ更新。
- 冪等: 同一 entry_key を何度実行しても結果が変わらない。
- model_version は必須（省略不可）。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import psycopg2.extras

from db.postgres_client import get_conn
from load.supabase_client import upsert, Client

logger = logging.getLogger(__name__)

# Supabase entries テーブルに書き込む予測列のみ（それ以外は一切送らない）
_PUBLISH_COLS = [
    "entry_key",
    "win_rate",          # Supabase側の既存列名に合わせる
    "place_rate",
    "show_rate",
    "expected_value_win",
    "expected_value_place",
    "star_rating",
    "ai_comment",
]

# Supabase に渡す際の列名変換（VM内列名 → Supabase列名）
_COL_RENAME = {
    "win_prob":  "win_rate",
    "top2_prob": "place_rate",
    "top3_prob": "show_rate",
}

# 絶対に送ってはいけないテーブル（誤操作防止ガード）
_FORBIDDEN_TABLES = frozenset({
    "users", "auth", "roles", "subscriptions",
    "stripe_events", "plans", "user_roles",
})


def _guard_table(table: str) -> None:
    if table in _FORBIDDEN_TABLES:
        raise PermissionError(
            f"[publisher] 禁止テーブルへの書き込みを検出: {table} — Auth/plan系は触れません"
        )


def publish_predictions(
    client: Client,
    df_pred: pd.DataFrame,
    model_version: str,
    retry_count: int = 3,
) -> int:
    """推論結果を Supabase entries テーブルの予測列へ upsert する。

    Args:
        client: Supabase クライアント
        df_pred: 推論結果 DataFrame（win_prob/top2_prob/top3_prob または win_rate/... どちらも可）
        model_version: モデルバージョン文字列（必須）
        retry_count: リトライ回数

    Returns:
        upsert 件数

    Raises:
        ValueError: model_version が空の場合
        PermissionError: 禁止テーブルへのアクセス試行
    """
    if not model_version:
        raise ValueError("[publisher] model_version は必須です。省略できません。")

    _guard_table("entries")

    if df_pred.empty:
        logger.warning("[publisher] 推論結果が空のため Supabase 反映をスキップ")
        return 0

    # VM 内列名 → Supabase 列名に変換
    df = df_pred.rename(columns=_COL_RENAME)

    # 許可列のみ抽出（それ以外は送らない）
    present_cols = [c for c in _PUBLISH_COLS if c in df.columns]
    missing_cols = [c for c in _PUBLISH_COLS if c not in df.columns]
    if missing_cols:
        logger.debug("[publisher] 列不足（スキップ）: %s", missing_cols)

    df_pub = df[present_cols].copy()
    df_pub["inference_at"] = datetime.now(timezone.utc).isoformat()
    df_pub["model_version"] = model_version

    records = df_pub.where(pd.notna(df_pub), None).to_dict(orient="records")

    upsert(
        client,
        table="entries",
        records=records,
        on_conflict="entry_key",
        retry_count=retry_count,
    )
    logger.info("[publisher] Supabase entries 予測反映完了: %d 件 model=%s",
                len(records), model_version)
    return len(records)


def mark_published(entry_keys: list[str], inference_at: str) -> None:
    """predictions_staging の published_to_supabase フラグを立てる。

    冪等: 同じキーを複数回実行しても問題ない。
    """
    if not entry_keys:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                UPDATE predictions_staging
                SET published_to_supabase = TRUE,
                    published_at          = now()
                WHERE entry_key = %s
                  AND inference_at = %s::timestamptz
                """,
                [(k, inference_at) for k in entry_keys],
            )
    logger.info("[publisher] published フラグ更新: %d 件", len(entry_keys))


def fetch_unpublished(limit: int = 10000) -> pd.DataFrame:
    """VM DB から未反映の predictions_staging を取得する。"""
    sql = """
        SELECT
            entry_key, race_key, inference_at, model_version,
            win_prob  AS win_rate,
            top2_prob AS place_rate,
            top3_prob AS show_rate,
            expected_value_win,
            expected_value_place,
            star_rating,
            ai_comment
        FROM predictions_staging
        WHERE NOT published_to_supabase
        ORDER BY inference_at DESC
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
    return pd.DataFrame(rows)
