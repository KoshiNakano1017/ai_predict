# -*- coding: utf-8 -*-
"""JRA スクレデータ (scripts/data/jra_*.csv) から mock CrossFactor SQLite を生成する。

目的:
  - CrossFactor 実データ受領前に、batch/run_pipeline.py の疎通テストを行う。
  - 既存の extract/ transform/ パイプラインが想定する JRA-VAN schema を
    真似た SQLite を作り、スキーマ mismatch やバグを先に発見する。

注意:
  - CrossFactor 独自指標 (pci, position_index, weight_correction 等) は
    再現不可能なため、NULL または 0 で埋める。
  - 学習・推論精度は出ない。あくまで「パイプラインが空走するか」の確認用。
  - 受領後は本物の CrossFactor SQLite に切り替えるため、本ファイルは
    開発検証用途のみで利用する。

使い方:
  # 5/23 の全レース CSV を読んで mock DB を作成
  python scripts/build_mock_crossfactor_db.py \\
    --csv-glob "scripts/data/jra_20260523_*.csv" \\
    --out C:/CrossFactor/data/mock_crossfactor.db

  # config.yaml の sqlite.path を上記出力先に書き換えてから
  python -m batch.run_pipeline --mode daily_evening --target-date 2026-05-23 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import glob as glob_mod
import io
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

VENUE_CODE = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10",
}
TRACK_TYPE_CODE = {"芝": "1", "ダート": "2", "障": "3", "障害": "3"}
SEX_CODE = {"牡": "1", "牝": "2", "騸": "3", "セ": "3"}


# ============================================================
# CSV 読み込み
# ============================================================
@dataclass
class RaceCsv:
    meta: dict[str, str]
    entries: list[dict[str, str]]


def parse_csv(path: Path) -> RaceCsv:
    """scrape_jra.py 出力 CSV を読む。"""
    meta: dict[str, str] = {}
    csv_lines: list[str] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                kv = s[1:].strip()
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    meta[k.strip()] = v.strip()
            else:
                csv_lines.append(line)

    reader = csv.DictReader(csv_lines)
    entries = [{k.strip(): (v.strip() if v else "") for k, v in row.items() if k} for row in reader]
    return RaceCsv(meta=meta, entries=entries)


# ============================================================
# JRA-VAN schema へのマッピング
# ============================================================
def race_key_parts(meta: dict[str, str]) -> dict[str, str]:
    """meta の race_key を分解して JV 列に必要な部品を返す。

    race_key = YYYYMMDD + 競馬場(2) + 開催回(2) + 開催日目(2) + R(2) = 16桁
    """
    rk = meta.get("race_key", "")
    if len(rk) != 16:
        raise ValueError(f"race_key 長さが不正: {rk!r}")
    return {
        "kai_nen": rk[0:4],
        "kai_tsuki_hi": rk[4:8],
        "keibajo": rk[8:10],
        "kai": rk[10:12],
        "nichi_me": rk[12:14],
        "race_no": rk[14:16],
    }


def to_jv_race_row(rcsv: RaceCsv) -> dict:
    """JVレース詳細EX の 1 行を組み立てる（日本語キー）。"""
    m = rcsv.meta
    p = race_key_parts(m)

    track_type_code = TRACK_TYPE_CODE.get(m.get("track_type", "芝"), "1")
    track_condition_code = "1"  # 良 (取得していないので固定値)

    return {
        "開催年": p["kai_nen"],
        "開催月日": p["kai_tsuki_hi"],
        "競馬場": p["keibajo"],
        "開催回": p["kai"],
        "開催日目": p["nichi_me"],
        "番号": p["race_no"],
        "距離": m.get("race_distance", "0"),
        "（芝ダ）区分": track_type_code,
        "芝馬場状態": track_condition_code if track_type_code == "1" else "",
        "ダ馬場状態": track_condition_code if track_type_code == "2" else "",
        "天候": "1",  # 晴 (取得していないので固定値)
        "競走種別": "",  # クラスコード未取得
        "競走条件": "",
        "出走頭数": str(len(rcsv.entries)),
        "G前直線距離": "0",  # 競馬場別固定値だが未取得
        "本賞金1": "0",
        "発走時刻": (m.get("start_time") or "0000").replace(":", "").zfill(4),
    }


def _csv_to_jv_value(v: str, scale: float = 1.0) -> str:
    """CSV の特徴量値（空 or 数値文字列）を JV 形式の文字列に変換する。

    空・None・"-"・"None" は "0" を返す。scale 倍して整数または小数に。
    """
    if v in (None, "", "-", "None"):
        return "0"
    try:
        f = float(v)
        # 連対率系（0-1）はそのまま小数で持つ
        if scale == 1.0:
            return f"{f:.4f}"
        return str(int(f * scale))
    except (ValueError, TypeError):
        return "0"


def to_jv_entry_rows(rcsv: RaceCsv) -> list[dict]:
    """JV馬毎レース情報EX の N 行を組み立てる（日本語キー）。

    CrossFactor 独自指標は基本 NULL/0 埋め。
    JRA スクレで取れる過去走特徴量（avg_finish_*, avg_popularity_3,
    place_rate_*, top5_4c_rate）は実値で埋める。
    """
    m = rcsv.meta
    p = race_key_parts(m)
    out: list[dict] = []

    for ent in rcsv.entries:
        horse_no = ent.get("horse_number", "0")
        horse_name = ent.get("horse_name", "")
        sex = ent.get("horse_sex", "")
        # 血統登録番号: 馬名ベースで安定したダミー ID（10桁数値風）
        # 馬名衝突は基本起きないが、起きたら別レース扱いになるだけ（影響軽微）
        horse_key = f"M{abs(hash(horse_name)) % (10**9):09d}" if horse_name else f"M{p['kai_nen']}{horse_no.zfill(5)}"
        try:
            weight = int(ent["horse_weight"]) if ent.get("horse_weight") else None
        except (ValueError, TypeError):
            weight = None
        try:
            weight_diff = int(ent["horse_weight_diff"]) if ent.get("horse_weight_diff") not in ("", None) else 0
        except (ValueError, TypeError):
            weight_diff = 0
        try:
            carrying = float(ent["carrying_weight"]) if ent.get("carrying_weight") else 0.0
        except (ValueError, TypeError):
            carrying = 0.0

        row = {
            # キー類
            "開催年": p["kai_nen"],
            "開催月日": p["kai_tsuki_hi"],
            "競馬場": p["keibajo"],
            "開催回": p["kai"],
            "開催日目": p["nichi_me"],
            "番号": p["race_no"],
            "馬番": str(horse_no).zfill(2),
            "枠番": str(ent.get("frame_number", "0")),
            # 馬・人
            "血統登録番号": horse_key,
            "馬名": horse_name,
            "騎手名": ent.get("jockey_name", ""),
            "調教師": "",  # 調教師コード（取得していない）
            "調教師名": ent.get("trainer_name", ""),
            "斤量": f"{int(carrying * 10):04d}" if carrying else "0000",  # JV-VAN形式 (0.1kg単位)
            "馬体重": str(weight or 0),
            "馬体重増減": str(weight_diff),
            "乗り": "",  # 騎手コード（未取得）
            "確定着順": "",  # 学習用ラベル（未来レースなのでNULL）

            # 過去走から計算済み（JRA スクレ取得分）
            "平均着順_前3走": _csv_to_jv_value(ent.get("avg_finish_3")),
            "平均着順_前5走": _csv_to_jv_value(ent.get("avg_finish_5")),
            "平均人気_前3走": _csv_to_jv_value(ent.get("avg_popularity_3")),
            "着度数P_馬場適性": _csv_to_jv_value(ent.get("place_rate_track")),
            "着度数P_競馬場": _csv_to_jv_value(ent.get("place_rate_course")),
            "着度数P_同距離": _csv_to_jv_value(ent.get("place_rate_distance")),
            "4角5番手内率": _csv_to_jv_value(ent.get("top5_4c_rate")),
            # CrossFactor 独自指標：取得不可なので 0 埋め
            "着度数P_回り適性": "0",
            "位置取り指数": "0",
            "位置取り指数順位": "0",
            "予想脚質": "0",
            "上がり3位内率": "0",
            "PCI": "0",
            "休養週数": "0",
            "休養後何走目": "0",
            "距離増減": "0",
            "斤量補正値": "0",
            "斤量補正値_上がり": "0",
            "競走馬単勝回収率": "0",
            "競走馬複勝回収率": "0",
            "坂路_直近1_4F合計": "0",
            "坂路_直近1_1F": "0",
            "坂路_直近2_4F合計": "0",
            "_直近1_4F合計": "0",  # ウッドチップ
            "_直近1_1F": "0",
            "USER_指数1": "0",
            "USER_指数2": "0",
            "USER_指数3": "0",

            # 補完用情報（horse master と紐付け）
            "_horse_sex_for_master": sex,
            "_horse_age_for_master": ent.get("horse_age", ""),
            "_win_odds": ent.get("win_odds", ""),
        }
        out.append(row)
    return out


def to_jv_odds_rows(jv_entries: list[dict], target_date_yyyymmdd: str) -> list[dict]:
    """JVオッズ_単複枠 の行を組み立てる。

    出馬表時点のオッズ（締切前）を 1 スナップショットだけ生成する。
    """
    rows = []
    for e in jv_entries:
        win_odds = e.get("_win_odds", "")
        if not win_odds:
            continue
        try:
            odds_x10 = int(float(win_odds) * 10)
        except (ValueError, TypeError):
            continue
        rows.append({
            "開催年": e["開催年"],
            "開催月日": e["開催月日"],
            "競馬場": e["競馬場"],
            "開催回": e["開催回"],
            "開催日目": e["開催日目"],
            "番号": e["番号"],
            "馬番": e["馬番"],
            "発表月日時分": f"{target_date_yyyymmdd}0900",  # 9:00 仮値
            "単勝オッズ": str(odds_x10),
            "複勝オッズ下": str(int(odds_x10 * 0.3)),  # 暫定（実値ではない）
            "複勝オッズ上": str(int(odds_x10 * 0.5)),
        })
    return rows


def to_jv_horse_master_rows(jv_entries: list[dict]) -> list[dict]:
    """JV競走馬マスタ。生年月日と性別をダミーで埋める。"""
    rows = []
    seen = set()
    for e in jv_entries:
        hk = e["血統登録番号"]
        if hk in seen:
            continue
        seen.add(hk)
        sex = e.get("_horse_sex_for_master", "")
        try:
            age = int(e.get("_horse_age_for_master") or 0)
        except (ValueError, TypeError):
            age = 0
        kai_nen = int(e["開催年"])
        # 馬齢は 0 ベース計算: 開催年 - 馬齢 - 1 = 生まれ年 (ざっくり)
        birth_year = kai_nen - age if age > 0 else kai_nen - 3
        rows.append({
            "血統登録番号": hk,
            "馬名": e.get("馬名", ""),
            "生年月日": f"{birth_year}0401",  # 仮の誕生日
            "性別": SEX_CODE.get(sex, "1"),
        })
    return rows


def to_jv_jockey_master_rows(jv_entries: list[dict]) -> list[dict]:
    """JV騎手マスタ。"""
    rows = []
    seen = set()
    for e in jv_entries:
        name = e.get("騎手名", "")
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({
            "騎手コード": f"K{abs(hash(name)) % 100000:05d}",
            "騎手名": name,
        })
    return rows


def to_jv_trainer_master_rows(jv_entries: list[dict]) -> list[dict]:
    """JV調教師マスタ。"""
    rows = []
    seen = set()
    for e in jv_entries:
        name = e.get("調教師名", "")
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({
            "調教師コード": f"T{abs(hash(name)) % 100000:05d}",
            "調教師名": name,
        })
    return rows


# ============================================================
# SQLite スキーマ定義
# ============================================================
JV_SCHEMA: dict[str, list[str]] = {
    "JVレース詳細EX": [
        "開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号",
        "距離", "（芝ダ）区分", "芝馬場状態", "ダ馬場状態", "天候",
        "競走種別", "競走条件", "出走頭数", "G前直線距離",
        "本賞金1", "発走時刻",
    ],
    "JV馬毎レース情報EX": [
        "開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号", "馬番", "枠番",
        "血統登録番号", "馬名", "騎手名", "調教師", "調教師名",
        "斤量", "馬体重", "馬体重増減", "乗り", "確定着順",
        "平均着順_前3走", "平均着順_前5走", "平均人気_前3走",
        "着度数P_馬場適性", "着度数P_競馬場", "着度数P_同距離", "着度数P_回り適性",
        "位置取り指数", "位置取り指数順位", "予想脚質",
        "4角5番手内率", "上がり3位内率", "PCI",
        "休養週数", "休養後何走目", "距離増減",
        "斤量補正値", "斤量補正値_上がり",
        "競走馬単勝回収率", "競走馬複勝回収率",
        "坂路_直近1_4F合計", "坂路_直近1_1F", "坂路_直近2_4F合計",
        "_直近1_4F合計", "_直近1_1F",
        "USER_指数1", "USER_指数2", "USER_指数3",
    ],
    "JVオッズ_単複枠": [
        "開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号", "馬番",
        "発表月日時分", "単勝オッズ", "複勝オッズ下", "複勝オッズ上",
    ],
    "JV競走馬マスタ": [
        "血統登録番号", "馬名", "生年月日", "性別",
    ],
    "JV騎手マスタ": [
        "騎手コード", "騎手名",
    ],
    "JV調教師マスタ": [
        "調教師コード", "調教師名",
    ],
}

# 主キー定義（重複 INSERT 防止用、実 CrossFactor とは厳密一致しない）
JV_PRIMARY_KEYS: dict[str, list[str]] = {
    "JVレース詳細EX": ["開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号"],
    "JV馬毎レース情報EX": ["開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号", "馬番"],
    "JVオッズ_単複枠": ["開催年", "開催月日", "競馬場", "開催回", "開催日目", "番号", "馬番", "発表月日時分"],
    "JV競走馬マスタ": ["血統登録番号"],
    "JV騎手マスタ": ["騎手コード"],
    "JV調教師マスタ": ["調教師コード"],
}


def create_schema(conn: sqlite3.Connection) -> None:
    """全テーブルを CREATE する（既存があれば DROP）。"""
    cur = conn.cursor()
    for table, cols in JV_SCHEMA.items():
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
        col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
        pks = JV_PRIMARY_KEYS.get(table, [])
        if pks:
            pk_def = ", PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pks) + ")"
        else:
            pk_def = ""
        cur.execute(f'CREATE TABLE "{table}" ({col_defs}{pk_def})')
    conn.commit()


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    """INSERT OR REPLACE で全行投入。"""
    if not rows:
        return 0
    cols = JV_SCHEMA[table]
    cur = conn.cursor()
    placeholders = ", ".join("?" * len(cols))
    col_quoted = ", ".join(f'"{c}"' for c in cols)
    sql = f'INSERT OR REPLACE INTO "{table}" ({col_quoted}) VALUES ({placeholders})'
    cnt = 0
    for r in rows:
        # JV_SCHEMA に含まれる列のみ抽出（_ 接頭の補助フィールドを除外）
        values = tuple(r.get(c, "") for c in cols)
        cur.execute(sql, values)
        cnt += 1
    conn.commit()
    return cnt


# ============================================================
# main
# ============================================================
def main() -> int:
    p = argparse.ArgumentParser(description="JRA スクレ CSV から mock CrossFactor SQLite を生成")
    p.add_argument("--csv-glob", required=True, help='CSV パターン (例: "scripts/data/jra_20260523_*.csv")')
    p.add_argument("--out", required=True, help="出力 SQLite ファイルパス")
    args = p.parse_args()

    csv_files = sorted(Path(p) for p in glob_mod.glob(args.csv_glob))
    if not csv_files:
        print(f"[ERROR] CSV ファイルが見つかりません: {args.csv_glob}")
        return 1

    print(f"=== {len(csv_files)} 個の CSV を処理 ===")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    create_schema(conn)
    print(f"  schema 作成: {out_path}")

    # 全 CSV を集約
    all_races: list[dict] = []
    all_entries: list[dict] = []
    all_odds: list[dict] = []

    for fp in csv_files:
        rcsv = parse_csv(fp)
        race_row = to_jv_race_row(rcsv)
        entry_rows = to_jv_entry_rows(rcsv)
        target_date = re.sub(r"\D", "", rcsv.meta.get("target_date", ""))[:8]
        odds_rows = to_jv_odds_rows(entry_rows, target_date)

        all_races.append(race_row)
        all_entries.extend(entry_rows)
        all_odds.extend(odds_rows)

    horse_rows = to_jv_horse_master_rows(all_entries)
    jockey_rows = to_jv_jockey_master_rows(all_entries)
    trainer_rows = to_jv_trainer_master_rows(all_entries)

    # 投入
    n_race = insert_rows(conn, "JVレース詳細EX", all_races)
    n_entry = insert_rows(conn, "JV馬毎レース情報EX", all_entries)
    n_odds = insert_rows(conn, "JVオッズ_単複枠", all_odds)
    n_horse = insert_rows(conn, "JV競走馬マスタ", horse_rows)
    n_jockey = insert_rows(conn, "JV騎手マスタ", jockey_rows)
    n_trainer = insert_rows(conn, "JV調教師マスタ", trainer_rows)

    conn.close()

    print()
    print(f"=== 完了 ===")
    print(f"  JVレース詳細EX        : {n_race} 行")
    print(f"  JV馬毎レース情報EX    : {n_entry} 行")
    print(f"  JVオッズ_単複枠       : {n_odds} 行")
    print(f"  JV競走馬マスタ        : {n_horse} 行")
    print(f"  JV騎手マスタ          : {n_jockey} 行")
    print(f"  JV調教師マスタ        : {n_trainer} 行")
    print()
    print(f"出力: {out_path.absolute()}")
    print()
    print(f"次のステップ:")
    print(f"  1. config.yaml の sqlite.path を以下に変更:")
    print(f"     path: \"{out_path.absolute().as_posix()}\"")
    print(f"  2. パイプライン空走テスト:")
    print(f"     python -m batch.run_pipeline --mode daily_evening --target-date 2026-05-23 --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
