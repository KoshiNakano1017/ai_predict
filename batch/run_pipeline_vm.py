"""GCP VM 用 メインパイプライン（2段化ETL）。

新フロー:
  1. SQLite → VM Postgres raw_races / raw_entries
  2. VMで特徴量生成 → features
  3. VMで推論 → predictions_staging
  4. predictions_staging → Supabase（予測列のみ upsert）

Web表示用ベースデータ（races/entries基本情報）は既存の run_pipeline.py から
引き続き Supabase に投入する。このスクリプトは AI 推論結果のみ担当する。

使い方:
  python batch/run_pipeline_vm.py --mode daily_evening --target-date 2026-03-30
  python batch/run_pipeline_vm.py --mode pre_race       --target-date 2026-03-30
  python batch/run_pipeline_vm.py --mode backfill       --from 2018-01-01 --to 2025-12-31
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from batch import config as cfg_module, logging_util, mailer
from extract import sqlite_client, race_selector, extract_races, extract_entries
from extract import extract_odds, extract_masters
from transform import validators, normalizer, odds_selector as odds_sel
from transform.master_merger import merge_master_name
from load import supabase_client as sb, upsert_entries, checkpoint_store
from load import vm_loader, supabase_publisher
from inference import run_inference
from db import postgres_client as pg

logger: logging.Logger = logging.getLogger("pipeline_vm")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CrossFactor AI バッチ（VM 2段化ETL）")
    p.add_argument("--mode", required=True,
                   choices=["daily_evening", "race_day_morning", "pre_race",
                            "backfill", "retry_failed"])
    p.add_argument("--target-date", default=None, help="YYYY-MM-DD 形式の対象日")
    p.add_argument("--from", dest="from_date", default=None)
    p.add_argument("--to",   dest="to_date",   default=None)
    p.add_argument("--config", default=None)
    p.add_argument("--dry-run", action="store_true", help="DB/Supabase 投入をスキップ")
    p.add_argument("--skip-base-upload", action="store_true",
                   help="Supabase ベースデータ(races/entries)投入をスキップ")
    return p.parse_args()


def _resolve_target_date(args: argparse.Namespace) -> str:
    return args.target_date or date.today().isoformat()


def _save_parquet(df: pd.DataFrame, run_dir: Path, name: str) -> Path:
    path = run_dir / f"{name}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info("[pipeline_vm] 中間ファイル保存: %s (%d 行)", path, len(df))
    return path


def run_once(
    target_date: str,
    mode: str,
    cfg,
    dry_run: bool,
    skip_base_upload: bool,
) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir = Path(cfg.batch.run_dir) / f"{target_date.replace('-', '')}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(Path(cfg.batch.log_dir) / f"vm_{target_date}_{mode}_{ts}.log")
    model_version = cfg.inference.model_version

    checkpoint = checkpoint_store.CheckpointStore(cfg.batch.checkpoint_file)
    processed_keys = checkpoint.get_processed_keys()

    # ── Step 1: SQLite 抽出 ──────────────────────────────
    with sqlite_client.open_db(
        cfg.sqlite.path,
        timeout_sec=cfg.sqlite.timeout_sec,
        retry_count=cfg.sqlite.retry_count,
        retry_interval_sec=cfg.sqlite.retry_interval_sec,
    ) as conn:
        df_races = extract_races.extract(conn, target_date)
        if df_races.empty:
            logger.warning("[pipeline_vm] 対象レースなし: %s", target_date)
            return

        df_races = race_selector.filter_diff(df_races, processed_keys, mode)
        if df_races.empty:
            logger.info("[pipeline_vm] 差分なし: 全レース処理済み")
            return

        race_keys = df_races["race_key"].tolist()
        _save_parquet(df_races, run_dir, "races")

        df_entries = extract_entries.extract(conn, race_keys, df_races)
        if df_entries.empty:
            raise ValueError("出走馬抽出結果が空です")

        horse_keys = df_entries["horse_key"].dropna().unique().tolist()
        df_horse   = extract_masters.fetch_horse_master(conn, horse_keys)
        df_jockey  = extract_masters.fetch_jockey_stats(conn, race_keys)
        df_trainer = extract_masters.fetch_trainer_stats(conn)

        if not df_horse.empty:
            df_entries = df_entries.merge(
                df_horse[["horse_key", "birth_date", "horse_sex"]],
                on="horse_key", how="left",
            )
        df_entries = merge_master_name(df_entries, df_jockey,  "jockey_code",  "jockey_name")
        df_entries = merge_master_name(df_entries, df_trainer, "trainer_code", "trainer_name")

        df_odds_raw = extract_odds.extract(conn, race_keys, df_races)

    if not df_odds_raw.empty:
        df_odds_latest = odds_sel.select_latest_odds(
            df_odds_raw, race_key_col="race_key", published_at_col="odds_published_at"
        ).rename(columns={"odds_published_at": "odds_snapshot_at"})
        merge_cols = ["race_key", "horse_number", "win_odds", "place_odds_low",
                      "place_odds_high", "odds_snapshot_at"]
        df_entries = df_entries.merge(
            df_odds_latest[[c for c in merge_cols if c in df_odds_latest.columns]],
            on=["race_key", "horse_number"], how="left",
        )

    if "win_odds" in df_entries.columns:
        df_entries["popularity_rank"] = (
            df_entries.groupby("race_key")["win_odds"]
            .rank(method="min", ascending=True)
            .astype("Int64")
        )

    df_entries = normalizer.calc_horse_age(df_entries, target_date)
    df_entries = normalizer.fill_missing(df_entries)
    df_entries = normalizer.encode_categoricals(df_entries)
    validators.run_all(df_races, df_entries)

    _save_parquet(df_entries, run_dir, "features")

    # ── Step 2: VM Postgres へ raw_* / features 投入 ─────
    job_id: int | None = None
    rows_raw_races = rows_raw_entries = rows_features = 0
    rows_predictions = rows_published = 0

    if not dry_run:
        job_id = vm_loader.mark_job_start(
            job_name=mode,
            target_date=target_date,
            mode=mode,
            model_version=model_version,
            log_path=log_file,
        )
        rows_raw_races   = vm_loader.load_raw_races(df_races)
        rows_raw_entries = vm_loader.load_raw_entries(df_entries)
        rows_features    = vm_loader.load_features(df_entries)
        logger.info("[pipeline_vm] VM DB 投入完了: races=%d entries=%d features=%d",
                    rows_raw_races, rows_raw_entries, rows_features)

    # ── Step 3: Supabase ベースデータ投入（races / entries 基本情報）──
    if not dry_run and not skip_base_upload:
        sb_client = sb.get_client(cfg.supabase.url, cfg.supabase.service_role_key)
        upsert_entries.upsert_races(sb_client, df_races, cfg.supabase.retry_count)
        upsert_entries.upsert_entries_base(sb_client, df_entries, cfg.supabase.retry_count)
        logger.info("[pipeline_vm] Supabase ベースデータ投入完了")

    # ── Step 4: 推論 ─────────────────────────────────────
    df_pred = run_inference.run(
        df_entries,
        model_dir=cfg.inference.model_dir,
        win_model_name=cfg.inference.win_model,
        top2_model_name=cfg.inference.top2_model,
        top3_model_name=cfg.inference.top3_model,
    )
    if df_pred is None:
        raise RuntimeError("推論結果が None (モデル未存在または推論エラー)")

    df_pred = run_inference.assign_star_ratings(
        df_pred,
        star_ev_threshold=cfg.inference.star_ev_threshold,
        triangle_ev_threshold=cfg.inference.triangle_ev_threshold,
        longshot_popularity_rank=cfg.inference.longshot_popularity_rank,
        risky_favorite_rank=cfg.inference.risky_favorite_rank,
    )
    _save_parquet(df_pred, run_dir, "predictions")

    # ── Step 5: VM predictions_staging 投入 ──────────────
    if not dry_run:
        rows_predictions = vm_loader.load_predictions_staging(df_pred, model_version)
        logger.info("[pipeline_vm] predictions_staging 投入完了: %d 件", rows_predictions)

    # ── Step 6: Supabase へ最終成果物（予測列のみ）upsert ──
    if not dry_run:
        sb_client = sb.get_client(cfg.supabase.url, cfg.supabase.service_role_key)
        inference_at = datetime.utcnow().isoformat()
        rows_published = supabase_publisher.publish_predictions(
            sb_client, df_pred, model_version=model_version,
            retry_count=cfg.supabase.retry_count,
        )
        supabase_publisher.mark_published(
            df_pred["entry_key"].tolist(), inference_at
        )
        logger.info("[pipeline_vm] Supabase 予測反映完了: %d 件", rows_published)

    # ── Step 7: GCS バックアップ ──────────────────────────
    gcs_bucket = os.getenv("GCS_BUCKET")
    if gcs_bucket and not dry_run:
        try:
            from backup.gcs_sync import upload_run_dir
            upload_run_dir(str(run_dir), gcs_bucket)
        except Exception as exc:
            logger.warning("[pipeline_vm] GCS バックアップ失敗 (続行): %s", exc)

    # ── Finalize ──────────────────────────────────────────
    checkpoint.mark_done(race_keys, target_date)

    if job_id is not None:
        vm_loader.mark_job_done(
            job_id, status="success",
            rows_raw_races=rows_raw_races,
            rows_raw_entries=rows_raw_entries,
            rows_features=rows_features,
            rows_predictions=rows_predictions,
            rows_published=rows_published,
        )


def main() -> None:
    args = parse_args()
    target_date = _resolve_target_date(args)
    cfg = cfg_module.load(config_path=args.config)

    # VM DB 接続プール初期化
    os.environ.setdefault("AI_DB_HOST",     cfg.vm_db.host)
    os.environ.setdefault("AI_DB_PORT",     str(cfg.vm_db.port))
    os.environ.setdefault("AI_DB_NAME",     cfg.vm_db.dbname)
    os.environ.setdefault("AI_DB_USER",     cfg.vm_db.user)
    os.environ.setdefault("AI_DB_PASSWORD", cfg.vm_db.password)
    if cfg.vm_db.dsn:
        os.environ["AI_DB_DSN"] = cfg.vm_db.dsn
    pg.init_pool()

    global logger
    logger = logging_util.setup(cfg.batch.log_dir, args.mode, target_date)

    try:
        if args.mode == "backfill":
            from_date = date.fromisoformat(args.from_date)
            to_date   = date.fromisoformat(args.to_date)
            cur = from_date
            while cur <= to_date:
                logger.info("[pipeline_vm] backfill: %s", cur.isoformat())
                run_once(cur.isoformat(), args.mode, cfg, args.dry_run, args.skip_base_upload)
                cur += timedelta(days=1)
        else:
            run_once(target_date, args.mode, cfg, args.dry_run, args.skip_base_upload)

    except Exception as exc:
        logger.error("[pipeline_vm] 致命的エラー: %s", exc)
        logger.error(traceback.format_exc())

        # job_runs に失敗を記録（best effort）
        try:
            vm_loader.mark_job_done(
                job_id=-1, status="failed", error_message=str(exc)[:2000]
            )
        except Exception:
            pass

        mailer.send_error(
            smtp_host=cfg.mail.smtp_host,
            smtp_port=cfg.mail.smtp_port,
            username=cfg.mail.username,
            password=cfg.mail.password,
            mail_from=cfg.mail.mail_from,
            to=cfg.mail.to,
            mode=args.mode,
            target_date=target_date,
            failed_step="pipeline_vm",
            error_message=str(exc),
            log_file="",
        )
        pg.close_pool()
        sys.exit(1)

    pg.close_pool()
    logger.info("[pipeline_vm] 正常完了")


if __name__ == "__main__":
    main()
