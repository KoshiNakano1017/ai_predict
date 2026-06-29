# -*- coding: utf-8 -*-
"""JRA 公式 sp 版の doAction 遷移を実証する一回限りの探査スクリプト。

トップ → 出馬表開催選択 → 開催1件選択 → レース一覧 → 出馬表 を辿り、
各段階の CNAME を出力する。
"""
from __future__ import annotations

import io
import re
import sys
import time
from pathlib import Path

import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "scripts" / "raw_html" / "jra_explore"
RAW.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
INTERVAL = 2.5
BASE = "https://sp.jra.jp"


def post_doaction(session: requests.Session, path: str, cname: str, save_name: str) -> str:
    url = f"{BASE}{path}"
    print(f"[POST] {url}  cname={cname}")
    resp = session.post(
        url,
        data={"cname": cname},
        headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.9", "Referer": BASE + "/"},
        timeout=15,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "shift_jis"
    save = RAW / save_name
    save.write_text(resp.text, encoding="utf-8")
    print(f"  -> saved {save} ({len(resp.text)} chars)")
    time.sleep(INTERVAL)
    return resp.text


def extract_doactions(html: str, action: str = "/JRADB/accessD.html") -> list[tuple[str, str]]:
    pat = re.compile(
        r"doAction\(['\"]" + re.escape(action) + r"['\"],\s*['\"]([^'\"]+)['\"]\)"
        r"[^<]*?>\s*([^<]+?)\s*<",
        re.DOTALL,
    )
    return pat.findall(html)


def main() -> int:
    s = requests.Session()
    s.get(BASE + "/", headers={"User-Agent": UA}, timeout=15)
    time.sleep(INTERVAL)

    # Step1: 出馬表 開催選択ページ
    html1 = post_doaction(s, "/JRADB/accessD.html", "sw01dli00/80", "01_kaisai_select.html")
    kaisai_actions = extract_doactions(html1, "/JRADB/accessD.html")
    print(f"\n[Step1] 開催選択候補: {len(kaisai_actions)} 件")
    for cname, label in kaisai_actions[:15]:
        print(f"  {cname:<40s}  {label}")

    if not kaisai_actions:
        print("[ERROR] 開催候補が抽出できませんでした")
        return 1

    # Step2: 「東京 5/23」を選択 → レース一覧
    venues = ["東京", "京都", "新潟", "中山", "阪神", "中京", "札幌", "函館", "福島", "小倉"]
    target = next(((c, l) for c, l in kaisai_actions if l in venues), None)
    if not target:
        print("[ERROR] 競馬場を含む開催候補が見つかりません")
        return 1
    target_cname, target_label = target
    print(f"\n[Step2] 選択: {target_label} ({target_cname})")
    html2 = post_doaction(s, "/JRADB/accessD.html", target_cname, "02_race_select.html")
    race_actions = extract_doactions(html2, "/JRADB/accessD.html")
    print(f"\n[Step2] レース選択候補: {len(race_actions)} 件")
    for cname, label in race_actions[:20]:
        print(f"  {cname:<40s}  {label}")

    if not race_actions:
        print("[WARN] レース候補が抽出できませんでした (HTML 構造を確認)")
        return 0

    # Step3: R番号らしきラベル（"1R" "2R"...）を持つもの を選択
    race_target = next(((c, l) for c, l in race_actions if "R" in l and l != target_label), None)
    if not race_target:
        race_target = next((rc for rc in race_actions if rc[0] != target_cname and rc[0] != "sw01dli00/80"), None)
    if not race_target:
        print("[ERROR] レース候補が見つかりません")
        return 1
    race_cname, race_label = race_target
    print(f"\n[Step3] 選択: {race_label} ({race_cname})")
    html3 = post_doaction(s, "/JRADB/accessD.html", race_cname, "03_shutuba.html")
    print(f"\n[Step3] HTML サイズ: {len(html3)} chars  / <tr 出現: {html3.count('<tr')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
