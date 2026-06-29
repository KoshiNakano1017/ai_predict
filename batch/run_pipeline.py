"""メインパイプライン。CLI から実行する。

使い方:
  python batch/run_pipeline.py --mode daily_evening --target-date 2026-03-30
  python batch/run_pipeline.py --mode pre_race       --target-date 2026-03-30
  python batch/run_pipeline.py --mode backfill       --from 2018-01-01 --to 2025-12-31
  python batch/run_pipeline.py --mode retry_failed   --target-date 2026-03-30

フロー (12_抽出スクリプト設計書.md §6 準拠):
  1. バッチ起動 / 設定読込
  2. SQLite 接続確認
  3. 対象レースの決定
  4. レース基本情報抽出
  5. 出走馬情報抽出
  6. マスタ情報結合
  7. オッズ情報抽出
  8. 欠損補完・型変換・特徴量マッピング
  9. race_key / entry_key 生成 (extract 段階で付与済み)
  10. バリデーション
  11. 中間ファイル保存 (runs/YYYYMMDD_HHMM/)
  12. Web表示ベースデータを Supabase 投入
  13. 推論スクリプト実行
  14. 推論結果を Supabase 投入
  15. GCS バックアップ (Phase 1-E)
  16. ログ出力
  17. 異常時メール通知
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

# プロジェクトルートを sys.path に追加
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from batch import config as cfg_module, logging_util, mailer
from extract import sqlite_client, race_selector, extract_races, extract_entries
from extract import extract_odds, extract_payouts, extract_masters
from transform import validators, normalizer, odds_selector as odds_sel
from transform.master_merger import merge_master_name
from load import supabase_client as sb, upsert_entries, checkpoint_store
from inference import run_inference

logger: logging.Logger = logging.getLogger("pipeline")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CrossFactor AI バッチパイプライン")
    p.add_argument("--mode", required=True,
                   choices=["daily_evening", "race_day_morning", "pre_race", "backfill", "retry_failed"])
    p.add_argument("--target-date", default=None, help="YYYY-MM-DD 形式の対象日")
    p.add_argument("--from", dest="from_date", default=None, help="バックフィル開始日 (YYYY-MM-DD)")
    p.add_argument("--to", dest="to_date", default=None, help="バックフィル終了日 (YYYY-MM-DD)")
    p.add_argument("--config", default=None, help="設定ファイルパス")
    p.add_argument("--dry-run", action="store_true", help="Supabase 投入をスキップ (動作確認用)")
    p.add_argument("--use-cached-data", action="store_true",
                   help="runs/ の最新中間ファイルを使用して推論のみ実行 (フェイルオーバー用)")
    return p.parse_args()


def _resolve_target_date(args: argparse.Namespace) -> str:
    if args.target_date:
        return args.target_date
    return date.today().isoformat()


def _save_parquet(df: pd.DataFrame, run_dir: Path, name: str) -> Path:
    path = run_dir / f"{name}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info("[pipeline] 中間ファイル保存: %s (%d 行)", path, len(df))
    return path


def _load_latest_cached(run_base_dir: str, name: str) -> pd.DataFrame:
    """runs/ 配下の最新ディレクトリから parquet を読み込む (フェイルオーバー用)。"""
    base = Path(run_base_dir)
    dirs = sorted(base.glob("*"), reverse=True)
    for d in dirs:
        p = d / f"{name}.parquet"
        if p.exists():
            return pd.read_parquet(p)
    raise FileNotFoundError(f"キャッシュ {name}.parquet が見つかりません: {base}")


def run_once(target_date: str, mode: str, cfg, dry_run: bool, use_cached: bool) -> None:
    """1日分のパイプラインを実行する。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir = Path(cfg.batch.run_dir) / f"{target_date.replace('-', '')}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(Path(cfg.batch.log_dir) / f"batch_{target_date}_{mode}_{ts}.log")

    checkpoint = checkpoint_store.CheckpointStore(cfg.batch.checkpoint_file)

    # ── フェイルオーバー用: キャッシュから features.parquet を読み込んで推論だけ実行 ──
    if use_cached:
        logger.info("[pipeline] use-cached-data: 推論のみ実行します")
        df_entries = _load_latest_cached(cfg.batch.run_dir, "features")
        _run_inference_and_upload(df_entries, cfg, dry_run, run_dir, log_file, mode, target_date)
        return

    # ── 通常フロー ──
    processed_keys = checkpoint.get_processed_keys()

    with sqlite_client.open_db(
        cfg.sqlite.path,
        timeout_sec=cfg.sqlite.timeout_sec,
        retry_count=cfg.sqlite.retry_count,
        retry_interval_sec=cfg.sqlite.retry_interval_sec,
    ) as conn:
        # Step 3-4: レース抽出
        df_races = extract_races.extract(conn, target_date)
        if df_races.empty:
            logger.warning("[pipeline] 対象レースなし: %s", target_date)
            return

        df_races = race_selector.filter_diff(df_races, processed_keys, mode)
        if df_races.empty:
            logger.info("[pipeline] 差分なし: 全レース処理済み")
            return

        race_keys = df_races["race_key"].tolist()
        _save_parquet(df_races, run_dir, "races")

        # Step 5: 出走馬抽出
        df_entries = extract_entries.extract(conn, race_keys, df_races)
        if df_entries.empty:
            logger.error("[pipeline] 出走馬抽出結果が空です")
            raise ValueError("出走馬抽出結果が空です")

        # Step 6: マスタ結合
        # 馬名・騎手名・調教師名は JV馬毎レース情報EX から既に extract 済み (feature_mapper参照)。
        # マスタは「馬齢算出のための生年月日・性別」と「名称が欠損した場合のフォールバック」用途で結合する。
        horse_keys = df_entries["horse_key"].dropna().unique().tolist()
        df_horse = extract_masters.fetch_horse_master(conn, horse_keys)
        df_jockey = extract_masters.fetch_jockey_stats(conn, race_keys)
        df_trainer = extract_masters.fetch_trainer_stats(conn)

        if not df_horse.empty:
            df_entries = df_entries.merge(df_horse[["horse_key", "birth_date", "horse_sex"]],
                                          on="horse_key", how="left")

        df_entries = merge_master_name(
            df_entries, df_jockey, key="jockey_code", name_col="jockey_name"
        )
        df_entries = merge_master_name(
            df_entries, df_trainer, key="trainer_code", name_col="trainer_name"
        )

        # Step 7: オッズ抽出
        df_odds_raw = extract_odds.extract(conn, race_keys, df_races)

        # Step 8: オッズ締め切り直前選択・マージ
        if not df_odds_raw.empty:
            df_odds_latest = odds_sel.select_latest_odds(
                df_odds_raw, race_key_col="race_key", published_at_col="odds_published_at"
            )
            df_odds_latest = df_odds_latest.rename(
                columns={"odds_published_at": "odds_snapshot_at"}
            )
            merge_cols = ["race_key", "horse_number", "win_odds", "place_odds_low",
                          "place_odds_high", "odds_snapshot_at"]
            df_entries = df_entries.merge(
                df_odds_latest[[c for c in merge_cols if c in df_odds_latest.columns]],
                on=["race_key", "horse_number"],
                how="left",
            )

    # 人気順 (win_odds が小さいほど人気)
    if "win_odds" in df_entries.columns:
        df_entries["popularity_rank"] = (
            df_entries.groupby("race_key")["win_odds"]
            .rank(method="min", ascending=True)
            .astype("Int64")
        )

    # 馬齢計算
    df_entries = normalizer.calc_horse_age(df_entries, target_date)

    # 欠損補完・エンコーディング
    df_entries = normalizer.fill_missing(df_entries)
    df_entries = normalizer.encode_categoricals(df_entries)

    # Step 10: バリデーション
    validators.run_all(df_races, df_entries)

    # Step 11: 中間ファイル保存
    _save_parquet(df_entries, run_dir, "features")

    # Step 12: Supabase ベースデータ投入
    if not dry_run:
        client = sb.get_client(cfg.supabase.url, cfg.supabase.service_role_key)
        upsert_entries.upsert_races(client, df_races, cfg.supabase.retry_count)
        upsert_entries.upsert_entries_base(client, df_entries, cfg.supabase.retry_count)
        logger.info("[pipeline] supabase_base_upload_success")
    else:
        logger.info("[pipeline] dry-run: Supabase 投入をスキップ")

    # Step 13-14: 推論・予測投入
    _run_inference_and_upload(df_entries, cfg, dry_run, run_dir, log_file, mode, target_date)

    # チェックポイント更新
    checkpoint.mark_done(race_keys, target_date)

    # Step 15: GCS バックアップ (Phase 1-E 実装後に有効化)
    # GCS_BUCKET 環境変数が設定されている場合のみ実行する
    gcs_bucket = os.getenv("GCS_BUCKET")
    if gcs_bucket and not dry_run:
        try:
            from backup.gcs_sync import upload_run_dir
            upload_run_dir(str(run_dir), gcs_bucket)
        except Exception as exc:
            logger.warning("[pipeline] GCS バックアップ失敗 (続行): %s", exc)


def _run_inference_and_upload(df_entries, cfg, dry_run, run_dir, log_file, mode, target_date):
    """推論を実行して Supabase に投入する。失敗時はベースデータを保持して通知する。"""
    try:
        df_pred = run_inference.run(
            df_entries,
            model_dir=cfg.inference.model_dir,
            win_model_name=cfg.inference.win_model,
            top2_model_name=cfg.inference.top2_model,
            top3_model_name=cfg.inference.top3_model,
        )
        if df_pred is None:
            raise RuntimeError("推論結果が None です (モデルファイル未存在か推論エラー)")

        df_pred = run_inference.assign_star_ratings(
            df_pred,
            star_ev_threshold=cfg.inference.star_ev_threshold,
            triangle_ev_threshold=cfg.inference.triangle_ev_threshold,
            longshot_popularity_rank=cfg.inference.longshot_popularity_rank,
            risky_favorite_rank=cfg.inference.risky_favorite_rank,
        )
        _save_parquet(df_pred, run_dir, "predictions")

        if not dry_run:
            client = sb.get_client(cfg.supabase.url, cfg.supabase.service_role_key)
            upsert_entries.upsert_predictions(client, df_pred, cfg.supabase.retry_count)
            logger.info("[pipeline] supabase_predictions_upload_success")

    except Exception as exc:
        logger.error("[inference] 推論/投入失敗: %s", exc)
        logger.error(traceback.format_exc())
        # ベースデータは保持し、予測結果のみ未更新として通知
        mailer.send_error(
            smtp_host=cfg.mail.smtp_host,
            smtp_port=cfg.mail.smtp_port,
            username=cfg.mail.username,
            password=cfg.mail.password,
            mail_from=cfg.mail.mail_from,
            to=cfg.mail.to,
            mode=mode,
            target_date=target_date,
            failed_step="inference",
            error_message=str(exc),
            log_file=log_file,
        )


def main() -> None:
    args = parse_args()
    target_date = _resolve_target_date(args)
    cfg = cfg_module.load(config_path=args.config)

    # ロガー初期化
    global logger
    logger = logging_util.setup(cfg.batch.log_dir, args.mode, target_date)

    try:
        if args.mode == "backfill":
            from_date = date.fromisoformat(args.from_date)
            to_date = date.fromisoformat(args.to_date)
            cur = from_date
            while cur <= to_date:
                logger.info("[pipeline] backfill: %s", cur.isoformat())
                run_once(cur.isoformat(), args.mode, cfg, args.dry_run, args.use_cached_data)
                cur += timedelta(days=1)
        else:
            run_once(target_date, args.mode, cfg, args.dry_run, args.use_cached_data)
    except Exception as exc:
        logger.error("[pipeline] 致命的エラー: %s", exc)
        logger.error(traceback.format_exc())
        mailer.send_error(
            smtp_host=cfg.mail.smtp_host,
            smtp_port=cfg.mail.smtp_port,
            username=cfg.mail.username,
            password=cfg.mail.password,
            mail_from=cfg.mail.mail_from,
            to=cfg.mail.to,
            mode=args.mode,
            target_date=target_date,
            failed_step="pipeline",
            error_message=str(exc),
            log_file="",
        )
        sys.exit(1)

    logger.info("[pipeline] 正常完了")


if __name__ == "__main__":
    main()
