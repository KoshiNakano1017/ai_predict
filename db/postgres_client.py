"""VM 内 PostgreSQL への接続管理。

psycopg2 の接続プールを使い、スレッドセーフに接続を再利用する。
環境変数 AI_DB_DSN（または個別変数）から接続情報を取得する。

使い方:
    from db.postgres_client import get_conn, execute_migration

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg2
from psycopg2 import pool as pg_pool

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None


def _build_dsn() -> str:
    """環境変数から DSN 文字列を構築する。AI_DB_DSN が設定されていればそのまま使う。"""
    dsn = os.getenv("AI_DB_DSN")
    if dsn:
        return dsn
    host = os.getenv("AI_DB_HOST", "localhost")
    port = os.getenv("AI_DB_PORT", "5432")
    dbname = os.getenv("AI_DB_NAME", "keiba_ai")
    user = os.getenv("AI_DB_USER", "ai_runner")
    password = os.getenv("AI_DB_PASSWORD", "")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def init_pool(minconn: int = 1, maxconn: int = 5) -> None:
    """接続プールを初期化する。アプリ起動時に一度だけ呼ぶ。"""
    global _pool
    if _pool is not None:
        return
    dsn = _build_dsn()
    _pool = pg_pool.ThreadedConnectionPool(minconn, maxconn, dsn)
    logger.info("[postgres] 接続プール初期化完了 (min=%d max=%d)", minconn, maxconn)


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    if _pool is None:
        init_pool()
    return _pool  # type: ignore[return-value]


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """コンテキストマネージャ経由で接続を取得する。

    commit は呼び出し側で行うこと。例外時は自動 rollback する。
    """
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def execute_migration(sql_path: str | Path) -> None:
    """DDL ファイルを読み込んで実行する（冪等）。"""
    sql = Path(sql_path).read_text(encoding="utf-8")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("[postgres] マイグレーション適用完了: %s", sql_path)


def close_pool() -> None:
    """接続プールを閉じる。プロセス終了時に呼ぶ。"""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("[postgres] 接続プール終了")
