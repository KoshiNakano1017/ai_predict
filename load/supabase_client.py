"""Supabase REST API への Upsert 共通処理。リトライ付き。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client(url: str, service_role_key: str) -> Client:
    global _client
    if _client is None:
        _client = create_client(url, service_role_key)
    return _client


def upsert(
    client: Client,
    table: str,
    records: List[Dict[str, Any]],
    on_conflict: str,
    retry_count: int = 3,
    retry_intervals: List[int] = None,
) -> None:
    """テーブルに records を Upsert する。失敗時はリトライする。

    Args:
        client: Supabase クライアント
        table: テーブル名
        records: upsert するレコードのリスト
        on_conflict: 競合時の更新キー列名 (e.g. "race_key" or "entry_key")
        retry_count: リトライ回数 (デフォルト 3)
        retry_intervals: 各リトライ間の待機秒数 (デフォルト [5, 15, 30])
    """
    if not records:
        return

    if retry_intervals is None:
        retry_intervals = [5, 15, 30]

    last_exc: Exception | None = None
    for attempt in range(1, retry_count + 1):
        try:
            response = (
                client.table(table)
                .upsert(records, on_conflict=on_conflict)
                .execute()
            )
            logger.info(
                "[supabase] upsert_success table=%s count=%d",
                table,
                len(records),
            )
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "[supabase] upsert_failed table=%s attempt=%d: %s",
                table, attempt, exc,
            )
            if attempt < retry_count:
                wait = retry_intervals[min(attempt - 1, len(retry_intervals) - 1)]
                time.sleep(wait)

    raise RuntimeError(
        f"Supabase upsert が {retry_count} 回すべて失敗しました: table={table}"
    ) from last_exc
