# -*- coding: utf-8 -*-
"""netkeiba HTML 取得ユーティリティ（構造調査・raw 保存用）。

規約評価書 (docs/Logs/20260523_netkeiba_スクレイピング規約評価.md) のルール:
  - リクエスト間隔: 2秒以上
  - 取得した raw HTML は scripts/raw_html/ に保存
  - 個人利用の開発検証目的のみ
  - 会員限定領域は触らない
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path
from typing import Optional

import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "scripts" / "raw_html"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_INTERVAL_SEC = 2.5


def fetch(url: str, save_path: Path) -> str:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[fetch] {url}")
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.9"},
        timeout=15,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "euc-jp"
    save_path.write_text(resp.text, encoding="utf-8")
    print(f"  -> saved {save_path} ({len(resp.text)} chars)")
    time.sleep(REQUEST_INTERVAL_SEC)
    return resp.text


def fetch_race_list(kaisai_date: str) -> Path:
    url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}"
    out = RAW_DIR / "race_list" / f"{kaisai_date}.html"
    fetch(url, out)
    return out


def fetch_shutuba(race_id: str) -> Path:
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    out = RAW_DIR / "shutuba" / f"{race_id}.html"
    fetch(url, out)
    return out


def fetch_race_meta(race_id: str) -> Optional[Path]:
    """発走時刻・コース情報が動的部にある場合の代替: ?race_id= を結果ページに当てる。"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    out = RAW_DIR / "result" / f"{race_id}.html"
    try:
        fetch(url, out)
        return out
    except requests.HTTPError as e:
        print(f"  [skip] result page not found: {e}")
        return None


def fetch_db_race(race_id: str) -> Path:
    """db.netkeiba.com のレース詳細ページ（SSR、出走馬テーブル含む）を取得する。"""
    url = f"https://db.netkeiba.com/race/{race_id}/"
    out = RAW_DIR / "db_race" / f"{race_id}.html"
    fetch(url, out)
    return out


def fetch_db_race_shutuba(race_id: str) -> Optional[Path]:
    """未来レースの出馬表（SSR）。db.netkeiba.com の shutuba 互換 URL を試す。"""
    url = f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}"
    out = RAW_DIR / "shutuba_past" / f"{race_id}.html"
    try:
        fetch(url, out)
        return out
    except requests.HTTPError as e:
        print(f"  [skip] shutuba_past not found: {e}")
        return None


def fetch_jra_sp(cname: str, label: str = "") -> Path:
    """JRA 公式スマホ版 (sp.jra.jp) の出馬表/結果ページを取得。

    cname 例: 'sw01dde1003202601040220260419/32'
      - sw01 = スマホ版識別
      - dde / dse / oze = 出馬表/レース結果/オッズ など
      - 後続は開催・日付・レース番号エンコード
    """
    url = f"https://sp.jra.jp/JRADB/accessD.html?CNAME={cname}"
    safe = cname.replace("/", "_")
    suffix = f"_{label}" if label else ""
    out = RAW_DIR / "jra_sp" / f"{safe}{suffix}.html"
    fetch(url, out)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="netkeiba HTML 取得（構造調査用）")
    p.add_argument("--date", help="開催日 YYYYMMDD (例: 20260523)")
    p.add_argument("--race-id", help="出馬表の race_id (例: 202505030911)")
    p.add_argument("--with-result", action="store_true", help="result.html も取得（過去レース時）")
    p.add_argument("--db", action="store_true", help="db.netkeiba.com の SSR ページも取得")
    p.add_argument("--shutuba-past", action="store_true", help="shutuba_past.html (SSR) も取得")
    p.add_argument("--jra-sp-cname", help="JRA sp版 出馬表 CNAME (例: sw01dde.../32)")
    args = p.parse_args()

    if not args.date and not args.race_id and not args.jra_sp_cname:
        p.error("--date / --race-id / --jra-sp-cname のいずれか必須")

    if args.jra_sp_cname:
        fetch_jra_sp(args.jra_sp_cname)

    if args.date:
        fetch_race_list(args.date)

    if args.race_id:
        fetch_shutuba(args.race_id)
        if args.with_result:
            fetch_race_meta(args.race_id)
        if args.db:
            fetch_db_race(args.race_id)
        if args.shutuba_past:
            fetch_db_race_shutuba(args.race_id)

    print("\n=== 完了 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
