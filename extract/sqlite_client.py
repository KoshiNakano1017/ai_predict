"""CrossFactor SQLite への接続・SELECT 共通処理。

リトライ付き接続と安全な読み取りのみを担う (書き込みなし)。
"""
from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from typing import Generator, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@contextmanager
def open_db(
    db_path: str,
    timeout_sec: int = 30,
    retry_count: int = 3,
    retry_interval_sec: int = 10,
) -> Generator[sqlite3.Connection, None, None]:
    """SQLite に接続してコンテキストを返す。失敗時はリトライする。"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, retry_count + 1):
        try:
            conn = sqlite3.connect(
                db_path,
                timeout=timeout_sec,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            # 読み取り専用を強制
            conn.execute("PRAGMA query_only = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            logger.info("[sqlite] 接続成功: %s", db_path)
            try:
                yield conn
            finally:
                conn.close()
            return
        except sqlite3.OperationalError as exc:
            last_exc = exc
            logger.warning("[sqlite] 接続失敗 attempt=%d: %s", attempt, exc)
            if attempt < retry_count:
                time.sleep(retry_interval_sec)

    raise ConnectionError(f"SQLite 接続が {retry_count} 回すべて失敗しました: {last_exc}") from last_exc


def query_to_df(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
) -> pd.DataFrame:
    """SELECT クエリを実行して DataFrame を返す。"""
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    except Exception as exc:
        logger.error("[sqlite] クエリ失敗: %s", exc)
        logger.debug("[sqlite] SQL: %s / params: %s", sql, params)
        raise


def list_tables(conn: sqlite3.Connection) -> List[str]:
    """DB 内のテーブル一覧を返す (デバッグ用)。"""
    df = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )
    return df["name"].tolist()


def table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """テーブルのカラム名一覧を返す (デバッグ用)。"""
    df = pd.read_sql_query(f"PRAGMA table_info('{table}')", conn)
    return df["name"].tolist()
