# -*- coding: utf-8 -*-
"""キャッシュ済み出馬表 HTML から CSV を再生成する（ネット叩かない）。

scrape_jra.py がネット越しに叩いた HTML を scripts/raw_html/jra_sp/ に保存している。
これらを元に、過去走特徴量を含む新フォーマットの CSV を一括再生成する。

使い方:
  python scripts/rebuild_csv_from_cache.py --date 20260523
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# scrape_jra の副作用 (sys.stdout wrap) より前に import
from scrape_jra import (
    parse_shutuba, compute_features, write_csv,
    RaceRef, VENUE_CODE,
)

CACHE_DIR = ROOT / "scripts" / "raw_html" / "jra_sp"
DEFAULT_OUT = ROOT / "scripts" / "data"

# キャッシュファイル名: sw01dde0105202602090120260523_09_shutuba_東京_01.html
# ファイル名の "shutuba_<venue>_<race_no>" を拾う
NAME_RE = re.compile(r"shutuba_(\S+?)_(\d+)\.html$")


def main() -> int:
    p = argparse.ArgumentParser(description="キャッシュ HTML から CSV 再生成")
    p.add_argument("--date", required=True, help="開催日 YYYYMMDD")
    p.add_argument("--output", default=str(DEFAULT_OUT))
    args = p.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(CACHE_DIR.glob("*shutuba*.html"))
    if not files:
        print(f"[ERROR] キャッシュなし: {CACHE_DIR}")
        return 1

    # ファイル名内の日付（cname 内の {date}）でフィルタ
    target_files = [f for f in files if args.date in f.name]
    print(f"対象 HTML: {len(target_files)} / 全 {len(files)}")

    total_with_past = 0
    total_horses = 0
    rebuilt = 0

    for f in target_files:
        m = NAME_RE.search(f.name)
        if not m:
            continue
        venue = m.group(1)
        race_no = int(m.group(2))

        html = f.read_text(encoding="utf-8")
        meta, entries = parse_shutuba(html)
        if not entries:
            print(f"  [WARN] {f.name}: 0 頭")
            continue

        # race_distance / track_type は parse_shutuba メタからは取れないので
        # 過去走の最頻値 or info_text から推定する。簡易的に entries の features 計算は
        # 各馬の出走実績から「同条件」を比較するので、レース条件不明時は不一致扱い (None)。
        race_distance = 0
        track_type = ""
        # info_text から「ダ1600」「芝2400」を抽出
        info = meta.get("info_text", "")
        m_dist = re.search(r"(芝|ダ(?:ート)?|障)\s*(\d+)\s*m", info) or re.search(r"(\d+)\s*m\s*(芝|ダート|障)", info)
        if m_dist:
            if m_dist.group(1).isdigit():
                race_distance = int(m_dist.group(1))
                track_type = m_dist.group(2)
            else:
                track_type = m_dist.group(1).replace("ダ", "ダート").replace("ダートート", "ダート")
                race_distance = int(m_dist.group(2))

        n_with_past = 0
        for e in entries:
            e.features = compute_features(
                past_runs=e.past_runs or [],
                current_track_type=track_type or None,
                current_venue=venue,
                current_distance=race_distance or None,
            )
            if e.features.n_past > 0:
                n_with_past += 1
        total_with_past += n_with_past
        total_horses += len(entries)

        # RaceRef を組み立てる（write_csv が必要とする最低限）
        rr = RaceRef(
            cname=f.stem.split("_")[0] if "_" in f.stem else "",
            race_no=race_no, distance=race_distance, track_type=track_type,
            num_horses=len(entries), race_name=meta.get("race_name", f"{race_no}R"),
            venue=venue, date=args.date,
        )

        csv_name = f"jra_{args.date}_{venue}_{race_no:02d}.csv"
        out = out_dir / csv_name
        write_csv(out, rr, meta, entries)
        rebuilt += 1
        print(f"  {venue} {race_no:2d}R: {len(entries)} 頭 (過去走あり {n_with_past}) -> {csv_name}")

    print()
    print(f"=== 再生成完了 ===")
    print(f"  CSV files: {rebuilt}")
    print(f"  総出走馬: {total_horses}")
    print(f"  過去走あり: {total_with_past} / {total_horses} ({total_with_past * 100 // max(total_horses, 1)}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
