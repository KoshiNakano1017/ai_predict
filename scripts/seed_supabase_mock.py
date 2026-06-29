# -*- coding: utf-8 -*-
"""Supabase races / entries テーブルにフロント表示用のモックデータを投入する。

E2E テスト用途:
  CrossFactor SQLite + 学習済みモデルが揃う前に、
  フロント (Next.js) の SupabaseRaceRepository 経路を実 DB で検証する。

実行例:
  python scripts/seed_supabase_mock.py                  # 今日の日付で投入
  python scripts/seed_supabase_mock.py 2026-05-20       # 任意の日付
  python scripts/seed_supabase_mock.py --clear-only     # その日付のデータ削除のみ

UPSERT なので何度実行しても安全。
"""
from __future__ import annotations

import argparse
import io
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# Windows cp932 コンソールでも絵文字を出力できるように標準出力を UTF-8 に
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

# .env を探索: ROOT/.env (バッチ用) → source/.env.local (NEXT_PUBLIC_*)
for env_path in [ROOT / ".env", ROOT / "source" / ".env.local"]:
    if env_path.exists():
        load_dotenv(env_path, override=False)

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を環境変数で設定してください")
    print(f"  探索パス: {ROOT}/.env, {ROOT}/source/.env.local")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("[ERROR] supabase が必要です: pip install supabase", file=sys.stderr)
    sys.exit(1)


# ============================================================
# モックデータ定義
# ============================================================
VENUES = ["東京", "中山", "阪神", "中京", "福島"]
TRACK_TYPES = ["芝", "ダート"]

# 馬名辞書（実在馬名と被らない架空のもの）
HORSE_NAMES = [
    "サンプルホース", "テストランナー", "ダンジャーポップ", "ミステリーウィン",
    "ノーマルランナー", "スティディペース", "ロイヤルプリンス", "エースファイター",
    "ダークホースキング", "サンライズクイーン", "オーシャンブルー", "スプリントキング",
    "ファイナルアンサー", "フェイバリット", "トップレート", "ポピュラーチョイス",
    "グリーンフラッシュ", "ミッドナイトスター", "クイックスター", "アンダードッグ",
    "ロングオッズ", "モーニンググロー", "ライジングサン", "フォグウォーカー",
    "シークレットスター", "ブラックスワン", "ゴールデンクラウン", "シルバーアロー",
    "クリムゾンルージュ", "アズールデイズ", "エメラルドナイト", "プラチナホープ",
    "サファイアウィンド", "ルビーフレイム", "ダイヤモンドラッシュ", "オパールミラージュ",
    "ペリドットライト", "アメジストドリーム", "トパーズエンパイア", "シトリンエンジェル",
]

JOCKEYS = [
    "武豊", "ルメール", "川田", "松山", "横山武", "戸崎", "三浦", "福永",
    "デムーロ", "岩田", "藤岡佑", "横山典", "田辺", "石川", "鮫島駿",
]

TRAINERS = [
    "藤原英", "国枝", "矢作", "友道", "中内田", "尾関", "高野", "斉藤崇",
]

AI_COMMENTS_BY_RATING = {
    "★": [
        "展開が向きやすく好条件",
        "距離適性が高く安定感あり",
        "前走内容良好で期待大",
        "好調キープでメンバー最上位",
    ],
    "▲": [
        "適性は申し分なく対抗筆頭",
        "実績上位、馬券圏内有力",
        "近走安定、堅実な走り",
    ],
    "⚠": [
        "オッズに対し期待値低め",
        "前走から状態不安",
        "枠順不利、過剰人気の可能性",
        "距離適性に疑問符",
    ],
    "◆": [
        "オッズ妙味あり、激走に期待",
        "条件好転、伏兵筆頭",
        "前走から大幅変身の余地",
    ],
}


@dataclass
class RaceSpec:
    venue: str
    race_no: int
    track_type: str
    race_distance: int
    start_time: str  # HHMM
    num_horses: int


def make_race_key(target_date: date, venue: str, race_no: int) -> str:
    """16桁: YYYYMMDD + 競馬場コード(2桁) + 回(1桁) + 日目(1桁) + R番号(2桁) + 予備(2桁)"""
    venue_codes = {"東京": "05", "中山": "06", "阪神": "09", "中京": "07", "福島": "03"}
    return f"{target_date.strftime('%Y%m%d')}{venue_codes.get(venue, '99')}11{race_no:02d}00"


def make_entry_key(race_key: str, horse_no: int) -> str:
    """18桁 = race_key(16) + 馬番(2)"""
    return f"{race_key}{horse_no:02d}"


def generate_race_specs() -> list[RaceSpec]:
    """1日分のレース構成を生成。

    各会場とも 1R〜12R の完全な番組を作る（フロントの一覧で 1R から欠けなく
    並ぶようにするため）。以前は 1/8/10/11R など飛び飛びだったため、特定会場の
    1R が表示されない不具合があった。
    """
    specs: list[RaceSpec] = []
    times = [
        "09:50", "10:25", "11:00", "11:35", "12:10", "12:45",
        "13:20", "13:55", "14:30", "15:05", "15:40", "16:15",
    ]
    distances_turf = [1200, 1400, 1600, 1800, 2000, 2400]
    distances_dirt = [1200, 1400, 1700, 1800]

    venues = ["中山", "東京", "阪神", "中京"]
    races_per_venue = 12

    for venue in venues:
        for race_no in range(1, races_per_venue + 1):
            # 番組の中盤以降は芝中心、序盤はダート多めにして変化をつける
            track_type = "芝" if race_no % 2 == 0 else "ダート"
            dist = random.choice(distances_turf if track_type == "芝" else distances_dirt)
            specs.append(RaceSpec(
                venue=venue,
                race_no=race_no,
                track_type=track_type,
                race_distance=dist,
                start_time=times[(race_no - 1) % len(times)],
                num_horses=random.randint(10, 16),
            ))
    return specs


def generate_entries_for_race(race_key: str, num_horses: int) -> list[dict]:
    """1レース分の出走馬データ。star_rating の分布を要件通りに作る。"""
    horses = random.sample(HORSE_NAMES, num_horses)
    jockeys = random.sample(JOCKEYS, num_horses) if num_horses <= len(JOCKEYS) else [random.choice(JOCKEYS) for _ in range(num_horses)]

    # オッズを 単勝1.5〜80倍 で生成
    odds_pool = sorted([round(random.uniform(1.5, 4.0), 1) for _ in range(2)] +
                       [round(random.uniform(4.0, 12.0), 1) for _ in range(num_horses // 2)] +
                       [round(random.uniform(12.0, 80.0), 1) for _ in range(num_horses - 2 - num_horses // 2)])
    if len(odds_pool) < num_horses:
        odds_pool += [round(random.uniform(20.0, 80.0), 1) for _ in range(num_horses - len(odds_pool))]
    random.shuffle(odds_pool)

    # 1レースに必ず ★1, ▲1〜2, ⚠1, ◆1 を配置（残りは None）
    ratings: list[Optional[str]] = [None] * num_horses
    rating_assignments = ["★", "▲", "▲", "⚠", "◆"]
    if num_horses < 5:
        rating_assignments = rating_assignments[:num_horses]
    indices = random.sample(range(num_horses), len(rating_assignments))
    for idx, r in zip(indices, rating_assignments):
        ratings[idx] = r

    entries = []
    for i in range(num_horses):
        horse_no = i + 1
        rating = ratings[i]
        odds = odds_pool[i]
        popularity = sorted(odds_pool).index(odds) + 1

        # 予測値: ★は40%前後、▲は20%前後、⚠は人気上位だが期待値低い、◆は人気下位だが期待値高い、Noneは平均
        if rating == "★":
            win_rate = round(random.uniform(28.0, 45.0), 1)
            expected_value_win = round(random.uniform(1.10, 1.40), 2)
        elif rating == "▲":
            win_rate = round(random.uniform(15.0, 25.0), 1)
            expected_value_win = round(random.uniform(1.05, 1.20), 2)
        elif rating == "⚠":
            win_rate = round(random.uniform(8.0, 18.0), 1)
            expected_value_win = round(random.uniform(0.70, 0.95), 2)
        elif rating == "◆":
            win_rate = round(random.uniform(4.0, 10.0), 1)
            expected_value_win = round(random.uniform(1.20, 1.60), 2)
        else:
            win_rate = round(random.uniform(2.0, 12.0), 1)
            expected_value_win = round(random.uniform(0.80, 1.05), 2)

        place_rate = min(round(win_rate * 1.6, 1), 70.0)
        show_rate = min(round(win_rate * 2.2, 1), 85.0)
        expected_value_place = round(expected_value_win * 0.95, 2)

        ai_comment = None
        if rating in AI_COMMENTS_BY_RATING:
            ai_comment = random.choice(AI_COMMENTS_BY_RATING[rating])

        entries.append({
            "entry_key": make_entry_key(race_key, horse_no),
            "race_key": race_key,
            "horse_number": horse_no,
            "frame_number": (horse_no - 1) // 2 + 1,
            "horse_key": f"H{random.randint(2018, 2022)}{random.randint(100000, 999999)}",
            "horse_name": horses[i],
            "jockey_code": f"J{random.randint(1, 99):03d}",
            "jockey_name": jockeys[i % len(jockeys)],
            "trainer_code": f"T{random.randint(1, 99):03d}",
            "trainer_name": random.choice(TRAINERS),
            "horse_weight": random.randint(440, 520),
            "horse_weight_diff": random.randint(-8, 8),
            "carrying_weight": round(random.uniform(54.0, 58.0), 1),
            "horse_age": random.randint(3, 7),
            "horse_sex": random.choice(["牡", "牝", "セ"]),
            "win_odds": odds,
            "popularity_rank": popularity,
            "place_odds_low": round(odds * 0.3, 1),
            "place_odds_high": round(odds * 0.5, 1),
            "win_rate": win_rate,
            "place_rate": place_rate,
            "show_rate": show_rate,
            "expected_value_win": expected_value_win,
            "expected_value_place": expected_value_place,
            "star_rating": rating,
            "ai_comment": ai_comment,
        })

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Supabase mock seeder for E2E testing")
    parser.add_argument("target_date", nargs="?", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--clear-only", action="store_true", help="削除のみ実行")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    if args.target_date:
        target_date = date.fromisoformat(args.target_date)
    else:
        target_date = date.today()

    # 日付ごとに異なるデータが生成されるように、シードに日付文字列を足し合わせる
    # こうしないと、どの日付を指定しても全く同じモックデータ(馬名やオッズなど)が生成されてしまう
    seed_val = args.seed + sum(ord(c) for c in target_date.isoformat())
    random.seed(seed_val)

    print(f"[seed] Supabase URL: {SUPABASE_URL}")
    print(f"[seed] Target date: {target_date.isoformat()}")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 既存データを削除（同じ日付）
    race_specs = generate_race_specs()
    race_keys = [make_race_key(target_date, s.venue, s.race_no) for s in race_specs]

    print(f"[seed] 既存データ削除 (target_date={target_date.isoformat()})")
    sb.table("entries").delete().in_("race_key", race_keys).execute()
    sb.table("races").delete().in_("race_key", race_keys).execute()

    if args.clear_only:
        print("[seed] --clear-only 指定のため終了")
        return 0

    # races 投入
    races_data = []
    for s in race_specs:
        race_key = make_race_key(target_date, s.venue, s.race_no)
        races_data.append({
            "race_key": race_key,
            "target_date": target_date.isoformat(),
            "venue": s.venue,
            "race_no": s.race_no,
            "track_type": s.track_type,
            "race_distance": s.race_distance,
            "track_condition": "良",
            "weather": "晴",
            "num_horses": s.num_horses,
            "straight_distance": 525 if s.venue == "東京" else 310,
            "prize_money_1st": 4000 if s.race_no >= 10 else 800,
            "start_time": s.start_time,
            "race_class_code": "G3" if s.race_no == 11 else "OP" if s.race_no >= 10 else "1勝C",
        })

    res = sb.table("races").upsert(races_data).execute()
    print(f"[seed] races 投入: {len(res.data)} 件")

    # entries 投入
    all_entries = []
    for s, race_key in zip(race_specs, race_keys):
        all_entries.extend(generate_entries_for_race(race_key, s.num_horses))

    res = sb.table("entries").upsert(all_entries).execute()
    print(f"[seed] entries 投入: {len(res.data)} 件")

    # 統計
    star_count = sum(1 for e in all_entries if e["star_rating"] == "★")
    triangle_count = sum(1 for e in all_entries if e["star_rating"] == "▲")
    caution_count = sum(1 for e in all_entries if e["star_rating"] == "⚠")
    diamond_count = sum(1 for e in all_entries if e["star_rating"] == "◆")
    print(f"[seed] star_rating 分布: ★={star_count}, ▲={triangle_count}, ⚠={caution_count}, ◆={diamond_count}")

    print(f"[seed] 完了。フロントから https://{SUPABASE_URL.replace('https://', '')}/rest/v1/races?target_date=eq.{target_date.isoformat()} で確認可能")
    return 0


if __name__ == "__main__":
    sys.exit(main())
