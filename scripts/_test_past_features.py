# -*- coding: utf-8 -*-
"""保存済み出馬表 HTML から過去走 → 特徴量計算が動くかをローカル検証する。

ネット越しに取得せず、scripts/raw_html/jra_sp/*shutuba* を入力にする。
"""
from __future__ import annotations

import sys, io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# scrape_jra import 時に sys.stdout を wrap する副作用があるため、import を先に行う
from scrape_jra import parse_shutuba, compute_features


def _fmt(v):
    if v is None:
        return "  -  "
    if isinstance(v, float):
        return f"{v:5.2f}"
    return f"{v:5}"

# サンプル: 東京1R, 5R, 11R を見比べる
samples = [
    (r"scripts\raw_html\jra_sp\sw01dde0105202602090120260523_09_shutuba_東京_01.html", "東京", 1, "ダート", 1600),
    (r"scripts\raw_html\jra_sp\sw01dde0105202602091120260523_5B_shutuba_東京_11.html", "東京", 11, "芝", 2400),
]

for path_str, venue, race_no, track_type, distance in samples:
    path = ROOT / path_str
    if not path.exists():
        print(f"NOT FOUND: {path}")
        continue
    html = path.read_text(encoding="utf-8")
    meta, entries = parse_shutuba(html)
    print(f"=== {venue} {race_no}R ({track_type}{distance}m) ===")
    print(f"  entries: {len(entries)}")

    has_past = 0
    for e in entries:
        e.features = compute_features(
            past_runs=e.past_runs or [],
            current_track_type=track_type,
            current_venue=venue,
            current_distance=distance,
        )
        if e.features.n_past > 0:
            has_past += 1
    print(f"  過去走あり: {has_past}/{len(entries)}")

    # 上位 5 頭の特徴量を表示
    print(f"  サンプル馬の特徴量:")
    for e in entries[:5]:
        f = e.features
        print(f"    {e.horse_number:2d} {e.horse_name:14s} | "
              f"past={f.n_past} avg3={_fmt(f.avg_finish_3)} avg5={_fmt(f.avg_finish_5)} "
              f"pop3={_fmt(f.avg_popularity_3)} pTrk={_fmt(f.place_rate_track)} "
              f"pCrs={_fmt(f.place_rate_course)} pDst={_fmt(f.place_rate_distance)} "
              f"4c5={_fmt(f.top5_4c_rate)}")
    print()
