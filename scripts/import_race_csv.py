# -*- coding: utf-8 -*-
"""手動入力 CSV から Supabase races / entries に投入するユーティリティ。

実レース運用フロー (個人利用・段階1):
  1. JRA公式 or netkeiba を目で見て、scripts/data/race_*.csv に手入力
  2. このスクリプトを実行 → Supabase races/entries に upsert
  3. 自動的にシンプル予測ロジックで star_rating / win_rate / expected_value_win を付与
  4. localhost:3000 のフロントから表示確認

CSV フォーマット (1ファイル = 1レース):
  ヘッダー行（# で始まる）でレースメタを定義し、その下に出馬データを並べる。

例 (scripts/data/race_20260524_tokyo_11.csv):
  # race_key: 2026052405111100
  # target_date: 2026-05-24
  # venue: 東京
  # race_no: 11
  # race_name: ダービー (任意)
  # track_type: 芝
  # race_distance: 2400
  # start_time: 15:40
  # track_condition: 良
  # weather: 晴
  horse_number,horse_name,jockey_name,trainer_name,horse_weight,horse_weight_diff,carrying_weight,horse_age,horse_sex,win_odds
  1,サンプル馬1,武豊,藤原英,486,2,57.0,4,牡,2.5
  2,...
  ...

実行例:
  python scripts/import_race_csv.py scripts/data/race_20260524_tokyo_11.csv
  python scripts/import_race_csv.py scripts/data/*.csv          # 複数一括
  python scripts/import_race_csv.py --dry-run scripts/data/race_xx.csv  # 投入なし
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import os
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] python-dotenv が必要です: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

for env_path in [ROOT / ".env", ROOT / "source" / ".env.local"]:
    if env_path.exists():
        load_dotenv(env_path, override=False)

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を設定してください")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("[ERROR] supabase が必要です: pip install supabase", file=sys.stderr)
    sys.exit(1)


# ============================================================
# CSV パーサ
# ============================================================
def parse_race_csv(path: Path) -> tuple[dict, list[dict]]:
    """1 つの CSV ファイルからレースメタと出走馬データを取り出す。"""
    meta: dict = {}
    entries: list[dict] = []

    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    csv_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            # # key: value 形式
            kv = s[1:].strip()
            if ":" in kv:
                k, v = kv.split(":", 1)
                meta[k.strip()] = v.strip()
        else:
            csv_lines.append(line)

    if not csv_lines:
        raise ValueError(f"{path}: 出走馬データの行がありません")

    reader = csv.DictReader(csv_lines)
    for row in reader:
        # 空白除去 + 数値カラム変換
        ent = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
        entries.append(ent)

    # 必須メタチェック
    required_meta = ["race_key", "target_date", "venue", "race_no", "track_type", "race_distance"]
    missing = [k for k in required_meta if k not in meta]
    if missing:
        raise ValueError(f"{path}: 必須メタ {missing} が不足")

    return meta, entries


# ============================================================
# シンプル予測ロジック
#   オッズベースで本命/対抗/危険人気/穴を機械的に割り当てる。
#   AI モデル未学習状態でもひとまず "それっぽい" 予測を提供。
# ============================================================
def attach_simple_predictions(entries: list[dict]) -> list[dict]:
    """odds をもとに star_rating / win_rate / expected_value_win を付与する。

    ロジック (レース単位で最大件数を絞る):
      - ★ = 1頭 : EV最高 (本命)
      - ▲ = 最大2頭 : EV2-3位 (対抗)
      - ⚠ = 最大1頭 : 人気上位だが EV < 0.9 の過剰人気
      - ◆ = 最大2頭 : 人気下位(7位以下) で EV > 1.15 の穴妙味
    win_rate, ev は控除率25%考慮のオッズ反転から仮算出。
    """
    # popularity_rank を odds 昇順で計算
    sorted_idx = sorted(range(len(entries)), key=lambda i: float(entries[i].get("win_odds") or 999))
    for rank, i in enumerate(sorted_idx, start=1):
        entries[i]["popularity_rank"] = rank

    # 各馬の素の win_rate / ev を計算
    for ent in entries:
        try:
            odds = float(ent.get("win_odds") or 0)
        except (ValueError, TypeError):
            odds = 0.0
        pop = ent.get("popularity_rank", 99)

        # 暗黙勝率 (オッズ反転 × 控除率補正)
        implied_win = (0.75 / odds * 100) if odds > 0 else 0.0
        # AI補正: 人気上位はやや割引、人気下位はやや上振れの仮想 AI 評価
        # 期待値 = (implied_win * factor / 100) * odds = 0.75 * factor
        # ◆ の条件 EV >= 1.05 を満たすには factor >= 1.4 が必要。
        # 人気薄(7位以下)の期待値を底上げし、オッズ妙味を強調する設計に変更。
        if pop <= 2:
            ai_win = implied_win * 0.92
        elif pop <= 4:
            ai_win = implied_win * 0.98
        elif pop <= 6:
            ai_win = implied_win * 1.05
        elif pop <= 10:
            ai_win = implied_win * 1.45  # 期待値 1.08 前後
        else:
            ai_win = implied_win * 1.60  # 期待値 1.20 前後

        ai_win = round(ai_win, 1)
        ev = round((ai_win / 100) * odds, 2) if odds > 0 else 0.0

        ent["_odds"] = odds
        ent["_pop"] = pop
        ent["win_rate"] = ai_win
        ent["place_rate"] = min(round(ai_win * 1.7, 1), 80.0)
        ent["show_rate"] = min(round(ai_win * 2.3, 1), 90.0)
        ent["expected_value_win"] = ev
        ent["expected_value_place"] = round(ev * 0.95, 2)
        ent["star_rating"] = None
        ent["ai_comment"] = None

    # ─── star_rating をレース単位で割り当て ───
    # 1) ★ : EV 降順 1位
    by_ev_desc = sorted(entries, key=lambda e: e["expected_value_win"], reverse=True)
    if by_ev_desc:
        top = by_ev_desc[0]
        top["star_rating"] = "★"
        top["ai_comment"] = f"AI本命。期待値{top['expected_value_win']:.2f}でメンバー最上位評価。"

    # 2) ▲ : ★以外で EV >= 1.0 を上位2頭
    triangle_candidates = [e for e in by_ev_desc[1:] if e["expected_value_win"] >= 1.0][:2]
    for t in triangle_candidates:
        t["star_rating"] = "▲"
        t["ai_comment"] = f"対抗。{t['_pop']}番人気・期待値{t['expected_value_win']:.2f}。"

    # 3) ⚠ : 1〜3番人気で EV < 0.9 の最も妙味薄な1頭
    risky = [e for e in entries if e["star_rating"] is None and e["_pop"] <= 3 and e["expected_value_win"] < 0.9]
    if risky:
        risky.sort(key=lambda e: e["expected_value_win"])
        worst = risky[0]
        worst["star_rating"] = "⚠"
        worst["ai_comment"] = f"{worst['_pop']}番人気だが期待値{worst['expected_value_win']:.2f}で妙味薄。過剰人気の可能性。"

    # 4) ◆ : 7番人気以下 + EV >= 1.05 の上位2頭 (穴妙味)
    longshots = [e for e in entries if e["star_rating"] is None and e["_pop"] >= 7 and e["expected_value_win"] >= 1.05]
    longshots.sort(key=lambda e: e["expected_value_win"], reverse=True)
    for ls in longshots[:2]:
        ls["star_rating"] = "◆"
        ls["ai_comment"] = f"{ls['_pop']}番人気の穴妙味。期待値{ls['expected_value_win']:.2f}、激走に注意。"

    # 一時カラムをクリーン
    for ent in entries:
        ent.pop("_odds", None)
        ent.pop("_pop", None)

    return entries


# ============================================================
# Supabase 投入
# ============================================================
def build_race_row(meta: dict, num_horses: int) -> dict:
    return {
        "race_key": meta["race_key"],
        "target_date": meta["target_date"],
        "venue": meta["venue"],
        "race_no": int(meta["race_no"]),
        "track_type": meta["track_type"],
        "race_distance": int(meta["race_distance"]),
        "track_condition": meta.get("track_condition", "良"),
        "weather": meta.get("weather", "晴"),
        "num_horses": num_horses,
        "straight_distance": int(meta["straight_distance"]) if "straight_distance" in meta else None,
        "prize_money_1st": int(meta["prize_money_1st"]) if "prize_money_1st" in meta else None,
        "start_time": meta.get("start_time"),
        "race_class_code": meta.get("race_class_code"),
    }


def build_entry_rows(race_key: str, entries: list[dict]) -> list[dict]:
    rows = []
    for ent in entries:
        horse_no = int(ent.get("horse_number") or 0)

        def num(key, conv=float, default=None):
            v = ent.get(key, "")
            if v in (None, ""):
                return default
            try:
                return conv(v)
            except (ValueError, TypeError):
                return default

        rows.append({
            "entry_key": f"{race_key}{horse_no:02d}",
            "race_key": race_key,
            "horse_number": horse_no,
            "frame_number": num("frame_number", int) or ((horse_no - 1) // 2 + 1),
            "horse_key": ent.get("horse_key") or None,
            "horse_name": ent.get("horse_name") or None,
            "jockey_code": ent.get("jockey_code") or None,
            "jockey_name": ent.get("jockey_name") or None,
            "trainer_code": ent.get("trainer_code") or None,
            "trainer_name": ent.get("trainer_name") or None,
            "horse_weight": num("horse_weight", int),
            "horse_weight_diff": num("horse_weight_diff", int),
            "carrying_weight": num("carrying_weight", float),
            "horse_age": num("horse_age", int),
            "horse_sex": ent.get("horse_sex") or None,
            "win_odds": num("win_odds", float),
            "popularity_rank": num("popularity_rank", int),
            "win_rate": num("win_rate", float),
            "place_rate": num("place_rate", float),
            "show_rate": num("show_rate", float),
            "expected_value_win": num("expected_value_win", float),
            "expected_value_place": num("expected_value_place", float),
            "star_rating": ent.get("star_rating") or None,
            "ai_comment": ent.get("ai_comment") or None,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV から Supabase へレースデータを投入する")
    parser.add_argument("csv_paths", nargs="+", help="CSV ファイル (ワイルドカード可)")
    parser.add_argument("--dry-run", action="store_true", help="投入せず検証のみ")
    parser.add_argument("--no-predict", action="store_true", help="自動予測付与をしない (CSV内の値をそのまま使う)")
    args = parser.parse_args()

    # ワイルドカード展開
    files: list[Path] = []
    for p in args.csv_paths:
        expanded = glob.glob(p)
        if expanded:
            for fp in expanded:
                files.append(Path(fp))
        else:
            files.append(Path(p))

    if not files:
        print("[ERROR] CSV ファイルが見つかりません")
        return 1

    sb = create_client(SUPABASE_URL, SUPABASE_KEY) if not args.dry_run else None
    total_races = total_entries = 0

    for fp in files:
        if not fp.exists():
            print(f"[skip] {fp} が存在しません")
            continue
        try:
            meta, entries = parse_race_csv(fp)
        except Exception as e:
            print(f"[ERROR] {fp}: {e}")
            continue

        if not args.no_predict:
            entries = attach_simple_predictions(entries)

        race_row = build_race_row(meta, num_horses=len(entries))
        entry_rows = build_entry_rows(meta["race_key"], entries)

        print(f"\n=== {fp.name} ===")
        print(f"  race_key: {meta['race_key']}")
        print(f"  {meta['venue']}{meta['race_no']}R {meta.get('track_type')}{meta.get('race_distance')}m, {len(entries)}頭")

        # 星マーク分布
        ratings = [e["star_rating"] for e in entries]
        print(f"  star_rating: ★={ratings.count('★')}, ▲={ratings.count('▲')}, ⚠={ratings.count('⚠')}, ◆={ratings.count('◆')}")

        if args.dry_run:
            print(f"  [dry-run] race row: {race_row}")
            print(f"  [dry-run] 先頭 entry: {entry_rows[0] if entry_rows else 'なし'}")
            continue

        # 投入
        sb.table("races").upsert(race_row).execute()
        # entries は親レコード後に投入
        # 既存削除→新規投入で確実に同期
        sb.table("entries").delete().eq("race_key", meta["race_key"]).execute()
        sb.table("entries").upsert(entry_rows).execute()
        total_races += 1
        total_entries += len(entry_rows)
        print(f"  [OK] races=1, entries={len(entry_rows)} 投入")

    print(f"\n=== 完了: races={total_races}, entries={total_entries} ===")
    if not args.dry_run:
        date_filter = meta.get("target_date", "")
        print(f"確認URL: http://localhost:3000/  (date_selector で {date_filter} を選択)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
