# -*- coding: utf-8 -*-
"""JRA 公式スマホ版 (sp.jra.jp) から出馬表を取得して CSV に変換する。

規約:
  JRA 公式は政府関係機関で公開情報。robots.txt も全許可方針。
  ただし高頻度アクセスは控え、リクエスト間隔 2.5 秒以上とする。

使い方:
  # 当日(2026-05-23)の東京1Rのみを取得
  python scripts/scrape_jra.py --date 20260523 --venue 東京 --race 1

  # 当日の東京全レース
  python scripts/scrape_jra.py --date 20260523 --venue 東京

  # 当日の全競馬場・全レース（鈍速）
  python scripts/scrape_jra.py --date 20260523

  # 既存の import_race_csv.py で投入（同じCSVフォーマット）
  python scripts/import_race_csv.py scripts/data/jra_20260523_*.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "scripts" / "data"
RAW_DIR = ROOT / "scripts" / "raw_html" / "jra_sp"
RAW_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
INTERVAL_SEC = 2.5
BASE = "https://sp.jra.jp"
ENTRY_CNAME = "sw01dli00/80"  # 出馬表トップ

VENUE_CODE = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10",
}


# ============================================================
# データクラス
# ============================================================
@dataclass
class KaisaiRef:
    """1 開催（venue × date）への参照。"""
    cname: str        # sw01drl00052026020920260523/26
    venue: str        # 東京
    date: str         # 20260523
    label: str        # 元 HTML 上のラベル


@dataclass
class RaceRef:
    """1 レース（R）への参照。"""
    cname: str            # sw01dde0105202602090120260523/09
    race_no: int          # 1〜12
    distance: int         # 1600
    track_type: str       # 芝 / ダート / 障害
    num_horses: int       # 出走頭数
    race_name: str        # 3歳未勝利 / カーネーションカップ など
    venue: str            # 東京
    date: str             # 20260523


# ============================================================
# 共通フェッチ
# ============================================================
class JraSession:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.9"})
        # トップページにアクセスしてセッション cookie を取得
        self.s.get(BASE + "/", timeout=15)
        time.sleep(INTERVAL_SEC)

    def get_by_cname(self, cname: str, save_label: str | None = None) -> str:
        """POST で doAction 互換の遷移を行う。
        トップから始めて段階的に CNAME を辿るのが本来の使い方。
        実装上は POST と GET 両方試して成功した方を返す。
        """
        url = f"{BASE}/JRADB/accessD.html"
        print(f"[POST] {url}  cname={cname}")
        r = self.s.post(url, data={"cname": cname}, timeout=15)
        if r.status_code != 200 or len(r.text) < 5000:
            print(f"  [fallback GET] (POST status={r.status_code}, size={len(r.text)})")
            r = self.s.get(f"{url}?CNAME={cname}", timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "shift_jis"
        if save_label:
            safe = cname.replace("/", "_")
            (RAW_DIR / f"{safe}_{save_label}.html").write_text(r.text, encoding="utf-8")
        time.sleep(INTERVAL_SEC)
        return r.text


# ============================================================
# Step1: 出馬表トップ → 開催一覧
# ============================================================
def list_kaisai(sess: JraSession) -> list[KaisaiRef]:
    html = sess.get_by_cname(ENTRY_CNAME, save_label="kaisai_top")
    soup = BeautifulSoup(html, "lxml")

    refs: list[KaisaiRef] = []
    # 例: sw01drl00052026020920260523/26
    #     sw01drl + 0005(競馬場) + 20260209(回日?) + 20260523(開催日) + /チェックサム
    pat_cname = re.compile(r"sw01drl(\d{4})(\d{8})(\d{8})/[0-9A-F]{2}")
    seen = set()
    for a in soup.find_all("a", onclick=True):
        m_oc = re.search(r"doAction\(\s*['\"]/JRADB/accessD\.html['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", a.get("onclick", ""))
        if not m_oc:
            continue
        cname = m_oc.group(1)
        if cname in seen:
            continue
        m = pat_cname.match(cname)
        if not m:
            continue
        seen.add(cname)
        venue_code = m.group(1)[2:]  # "0005" → "05"
        date = m.group(3)
        venue = next((k for k, v in VENUE_CODE.items() if v == venue_code), "?")
        label = a.get_text(strip=True) or venue
        refs.append(KaisaiRef(cname=cname, venue=venue, date=date, label=label))
    return refs


# ============================================================
# Step2: 開催 → レース一覧
# ============================================================
def list_races(sess: JraSession, kaisai: KaisaiRef) -> list[RaceRef]:
    html = sess.get_by_cname(kaisai.cname, save_label=f"races_{kaisai.venue}_{kaisai.date}")
    soup = BeautifulSoup(html, "lxml")

    races: list[RaceRef] = []
    # 各レースは <a href="/JRADB/accessD.html?CNAME=sw01dde..."> を持つ
    seen = set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"CNAME=(sw01dde\d{4}\d{10}\d{8}/[0-9A-F]{2})", a["href"])
        if not m:
            continue
        cname = m.group(1)
        if cname in seen:
            continue
        seen.add(cname)

        # ラベル "1R" "2R" を含む raceNo span を探す
        race_no_el = a.find("span", class_="raceNo")
        if not race_no_el:
            continue
        race_no_text = race_no_el.get_text(strip=True)
        m_no = re.match(r"(\d+)R", race_no_text)
        if not m_no:
            continue
        race_no = int(m_no.group(1))

        # コース・距離・頭数・レース名: 2 つ目の同じ a タグに含まれる
        # 例: 3歳未勝利<div>1600mダート 15頭</div>
        siblings = list(a.parent.parent.find_all("a"))
        course_text = ""
        race_name = ""
        for s in siblings:
            inner = s.get_text(separator="\n", strip=True)
            if "頭" in inner and ("m" in inner or "メートル" in inner):
                course_text = inner
                break

        m_dist = re.search(r"(\d+)\s*m\s*(芝|ダート|障)", course_text)
        m_horses = re.search(r"(\d+)\s*頭", course_text)
        if m_dist:
            distance = int(m_dist.group(1))
            track_type = m_dist.group(2)
        else:
            distance = 0
            track_type = ""
        num_horses = int(m_horses.group(1)) if m_horses else 0

        # レース名は course_text の先頭 (改行前) と仮定
        race_name = course_text.split("\n")[0].strip() if course_text else f"R{race_no}"

        races.append(RaceRef(
            cname=cname, race_no=race_no, distance=distance, track_type=track_type,
            num_horses=num_horses, race_name=race_name, venue=kaisai.venue, date=kaisai.date,
        ))

    races.sort(key=lambda r: r.race_no)
    return races


# ============================================================
# Step3: 出馬表ページ → 出走馬データ
# ============================================================
@dataclass
class PastRun:
    """1 走分の過去成績（前4走のいずれか）。"""
    finish: int | None       # 着順
    popularity: int | None   # 人気
    date: str | None         # YYYY-MM-DD
    venue: str | None        # 競馬場
    track_type: str | None   # 芝/ダート/障
    distance: int | None     # 距離 m
    track_condition: str | None  # 良/稍重/重/不良
    num_horses: int | None
    pos_4c: int | None       # 4角通過順位（通過順の最後の数字）


@dataclass
class HorseFeatures:
    """過去走から計算された馬の特徴量。"""
    n_past: int                  # 取得できた過去走数（最大 4）
    avg_finish_3: float | None
    avg_finish_5: float | None
    avg_popularity_3: float | None
    place_rate_track: float | None    # 同馬場種別での連対率（2着以内率）
    place_rate_course: float | None   # 同競馬場での連対率
    place_rate_distance: float | None # 同距離(±200m)での連対率
    top5_4c_rate: float | None        # 4角5番手内率


@dataclass
class Entry:
    horse_number: int
    frame_number: int
    horse_name: str
    win_odds: float | None
    popularity_rank: int | None
    horse_age: int | None
    horse_sex: str | None
    horse_color: str | None
    horse_weight: int | None
    horse_weight_diff: int | None
    jockey_name: str
    carrying_weight: float
    trainer_name: str
    trainer_belong: str  # 美浦/栗東
    past_runs: list[PastRun] = None  # type: ignore[assignment]
    features: HorseFeatures | None = None


def parse_past_runs(td_kako_text: str) -> list[PastRun]:
    """tr_kako の td.td_kako テキストから過去 4 走を抽出する。

    フォーマット例:
      "前走 8着 3番人気 2026年4月25日 福島 3歳牝未勝利 ダート1700 良 15頭 6番
       1:49.2 470kg 菊沢一樹 (55.0) 4-4-4-3 3F 40.4 ゴールドドレッサ (1.5)
       前々走 ... 3走前 ... 4走前 なし"

    過去走がない場合は「なし」が入っているのでスキップ。
    """
    runs: list[PastRun] = []
    sections = re.split(r"(前走|前々走|\d走前)", td_kako_text)
    # sections[0] は header（ヘッダー or 空）。以後は ["前走", "<内容>", "前々走", ...] 順
    for j in range(1, len(sections), 2):
        if j + 1 >= len(sections):
            break
        body = sections[j + 1].strip()
        if not body or body.startswith("なし"):
            continue

        # 着順
        m_finish = re.search(r"(\d+)着", body)
        finish = int(m_finish.group(1)) if m_finish else None

        # 人気
        m_pop = re.search(r"(\d+)番人気", body)
        popularity = int(m_pop.group(1)) if m_pop else None

        # 日付
        m_date = re.search(r"(\d{4})年(\d+)月(\d+)日", body)
        date = (
            f"{m_date.group(1)}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"
            if m_date else None
        )

        # 競馬場（日付直後の競馬場名 1〜3 文字）
        venue = None
        if m_date:
            after_date = body[m_date.end():].lstrip()
            m_venue = re.match(r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉|地方|海外|門別|大井|川崎|船橋|浦和|盛岡|水沢|金沢|笠松|名古屋|園田|姫路|高知|佐賀|帯広)", after_date)
            if m_venue:
                venue = m_venue.group(1)

        # 馬場種別 + 距離: "ダート1700" "芝1800" "障2880" 形式
        m_track = re.search(r"(芝|ダート|障)(\d+)", body)
        track_type = m_track.group(1) if m_track else None
        distance = int(m_track.group(2)) if m_track else None

        # 馬場状態
        m_cond = re.search(r"(?:芝|ダート|障)\d+\s+(良|稍重|重|不良)", body)
        track_condition = m_cond.group(1) if m_cond else None

        # 頭数
        m_horses = re.search(r"(\d+)頭", body)
        num_horses = int(m_horses.group(1)) if m_horses else None

        # 4 角通過順位: "4-4-4-3" の最後の数字、もしくは "8-8" の最後
        m_pass = re.search(r"\b(\d+(?:-\d+)+)\b", body)
        pos_4c = None
        if m_pass:
            pos_4c = int(m_pass.group(1).split("-")[-1])

        runs.append(PastRun(
            finish=finish, popularity=popularity, date=date, venue=venue,
            track_type=track_type, distance=distance, track_condition=track_condition,
            num_horses=num_horses, pos_4c=pos_4c,
        ))
    return runs


def compute_features(
    past_runs: list[PastRun],
    current_track_type: str | None,
    current_venue: str | None,
    current_distance: int | None,
) -> HorseFeatures:
    """過去走と当該レース条件から特徴量を計算する。

    - avg_finish_3 / 5: 直近 N 走の平均着順
    - avg_popularity_3: 直近 3 走の平均人気
    - place_rate_*: 該当条件での 2 着以内率（連対率）
    - top5_4c_rate: 4 角通過順位が 5 番以内だった率
    """
    if not past_runs:
        return HorseFeatures(0, None, None, None, None, None, None, None)

    finishes = [r.finish for r in past_runs if r.finish is not None]
    pops = [r.popularity for r in past_runs if r.popularity is not None]

    avg_3 = sum(finishes[:3]) / len(finishes[:3]) if finishes[:3] else None
    avg_5 = sum(finishes[:5]) / len(finishes[:5]) if finishes[:5] else None
    avg_pop_3 = sum(pops[:3]) / len(pops[:3]) if pops[:3] else None

    def _place_rate(filtered: list[PastRun]) -> float | None:
        with_finish = [r for r in filtered if r.finish is not None]
        if not with_finish:
            return None
        in_top2 = sum(1 for r in with_finish if r.finish <= 2)
        return in_top2 / len(with_finish)

    same_track = [r for r in past_runs if r.track_type == current_track_type] if current_track_type else []
    same_course = [r for r in past_runs if r.venue == current_venue] if current_venue else []
    same_dist = (
        [r for r in past_runs if r.distance is not None and current_distance and abs(r.distance - current_distance) <= 200]
        if current_distance else []
    )

    pos_4c_list = [r.pos_4c for r in past_runs if r.pos_4c is not None]
    if pos_4c_list:
        top5_rate = sum(1 for p in pos_4c_list if p <= 5) / len(pos_4c_list)
    else:
        top5_rate = None

    return HorseFeatures(
        n_past=len(past_runs),
        avg_finish_3=avg_3,
        avg_finish_5=avg_5,
        avg_popularity_3=avg_pop_3,
        place_rate_track=_place_rate(same_track),
        place_rate_course=_place_rate(same_course),
        place_rate_distance=_place_rate(same_dist),
        top5_4c_rate=top5_rate,
    )


def parse_shutuba(html: str) -> tuple[dict, list[Entry]]:
    """出馬表 HTML を解析してレース情報と出走馬リストを返す。"""
    soup = BeautifulSoup(html, "lxml")

    # レース情報: h1, h2 から
    meta: dict = {}
    h1 = soup.find("h1", id="titleDiv")
    h2 = soup.find("h2", class_="subTitle")

    # レース名・コース情報を taggedRace から
    info_block = soup.find("div", class_="cellInBox") or soup.find("div", class_="raceInfo")
    if info_block:
        info_text = info_block.get_text(separator=" ", strip=True)
        meta["info_text"] = info_text

    # subTitle: "2026年5月23日(土曜) 2回東京9日"
    if h2:
        sub = h2.get_text(strip=True)
        meta["sub_title"] = sub
        m_date = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", sub)
        if m_date:
            meta["target_date"] = f"{m_date.group(1)}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"
        m_venue = re.search(r"(\d+)回(\S+?)(\d+)日", sub)
        if m_venue:
            meta["kai"] = int(m_venue.group(1))
            meta["venue"] = m_venue.group(2)
            meta["nichi_me"] = int(m_venue.group(3))

    # レース名・コース・条件: title または raceTitle 部分から
    race_title = soup.find("div", id="race_title") or soup.find("h3")
    if race_title:
        meta["race_name"] = race_title.get_text(strip=True)

    # 出馬表テーブル
    entries: list[Entry] = []
    table = soup.find("div", id="umabashira")
    if not table:
        return meta, entries

    # 各 tr を順に走査。馬の uban 行と直後の tr_kako (過去成績) をペアで処理する。
    # 枠 (wban) は rowspan=2 で、同枠2頭目の tr には wban が含まれない。直前の枠を引き継ぐ。
    prev_frame = 0
    all_trs = table.find_all("tr")
    pending_entry_idx: int | None = None  # 直前の uban 行で entries に追加したインデックス
    for tr_idx, tr in enumerate(all_trs):
        if "tr_kako" in (tr.get("class") or []):
            # 直前に追加した entry に過去走を紐付ける
            if pending_entry_idx is None:
                continue
            td_kako = tr.find("td", class_="td_kako")
            if td_kako:
                kako_text = td_kako.get_text(separator=" ", strip=True)
                runs = parse_past_runs(kako_text)
                entries[pending_entry_idx].past_runs = runs
            pending_entry_idx = None
            continue

        # td.uban 馬番（必ずある）
        uban_td = tr.find("td", class_="uban")
        if not uban_td:
            continue
        uban_text = uban_td.get_text(strip=True)
        if not uban_text.isdigit():
            continue
        horse_no = int(uban_text)

        # td.wban 枠（無ければ前の枠を引き継ぐ）
        wban_td = tr.find("td", class_=re.compile(r"wban"))
        if wban_td and wban_td.get_text(strip=True).isdigit():
            frame = int(wban_td.get_text(strip=True))
            prev_frame = frame
        else:
            frame = prev_frame

        # td.uma の中
        uma_td = tr.find("td", class_="uma")
        if not uma_td:
            continue

        # 馬名
        bamei = uma_td.find("span", class_="bamei")
        horse_name = bamei.get_text(strip=True) if bamei else ""

        # 単勝オッズ・人気
        tan = uma_td.find("span", class_="tanOz")
        win_odds = None
        popularity = None
        if tan:
            tan_text = tan.get_text(strip=True)
            m_odds = re.search(r"([\d\.]+)", tan_text)
            m_pop = re.search(r"(\d+)番人気", tan_text)
            if m_odds:
                try:
                    win_odds = float(m_odds.group(1))
                except ValueError:
                    win_odds = None
            if m_pop:
                popularity = int(m_pop.group(1))

        # 性齢/毛色/馬体重: tanOz 直後の <span>
        sex_color_span = None
        for sp in uma_td.find_all("span", recursive=False):
            txt = sp.get_text(separator=" ", strip=True)
            if "/" in txt and ("kg" in txt or "牡" in txt or "牝" in txt or "セ" in txt):
                sex_color_span = sp
                break

        horse_age = None
        horse_sex = None
        horse_color = None
        horse_weight = None
        horse_weight_diff = None
        if sex_color_span:
            sc_text = sex_color_span.get_text(separator=" ", strip=True)
            m_age = re.search(r"([牡牝セせ])(\d+)", sc_text)
            if m_age:
                horse_sex = m_age.group(1)
                horse_age = int(m_age.group(2))
            # 毛色: / の後ろ 1〜2 文字
            m_color = re.search(r"/\s*(\S{1,3}?)\s+", sc_text)
            if m_color:
                horse_color = m_color.group(1)
            batai = sex_color_span.find("span", class_="batai")
            if batai:
                bt_text = batai.get_text(strip=True)
                m_w = re.search(r"(\d+)kg\(([+-]?\d+)\)", bt_text)
                if m_w:
                    horse_weight = int(m_w.group(1))
                    horse_weight_diff = int(m_w.group(2))
                else:
                    m_w_only = re.search(r"(\d+)kg", bt_text)
                    if m_w_only:
                        horse_weight = int(m_w_only.group(1))
                        horse_weight_diff = 0

        # 騎手名・斤量・調教師
        jockey_name = ""
        carrying_weight = 0.0
        trainer_name = ""
        trainer_belong = ""
        # 騎手・調教師は最後の span 内に複数 a + テキスト形式
        for sp in uma_td.find_all("span", recursive=False):
            sp_text = sp.get_text(separator=" ", strip=True)
            if "(" in sp_text and ")" in sp_text and any(b in sp_text for b in ["美浦", "栗東", "地方"]):
                # 騎手 + 調教師の span 確定
                anchors = sp.find_all("a")
                if len(anchors) >= 1:
                    jockey_name = anchors[0].get_text(strip=True)
                if len(anchors) >= 2:
                    trainer_name = anchors[1].get_text(strip=True)
                # 斤量 (騎手後の数字)
                m_w = re.search(r"\(([\d\.]+)\)", sp_text)
                if m_w:
                    try:
                        carrying_weight = float(m_w.group(1))
                    except ValueError:
                        carrying_weight = 0.0
                # 所属
                m_belong = re.search(r"\((美浦|栗東|地方)\)", sp_text)
                if m_belong:
                    trainer_belong = m_belong.group(1)
                break

        entries.append(Entry(
            horse_number=horse_no, frame_number=frame, horse_name=horse_name,
            win_odds=win_odds, popularity_rank=popularity,
            horse_age=horse_age, horse_sex=horse_sex, horse_color=horse_color,
            horse_weight=horse_weight, horse_weight_diff=horse_weight_diff,
            jockey_name=jockey_name, carrying_weight=carrying_weight,
            trainer_name=trainer_name, trainer_belong=trainer_belong,
            past_runs=[], features=None,
        ))
        pending_entry_idx = len(entries) - 1

    return meta, entries


# ============================================================
# CSV 出力 (import_race_csv.py 互換フォーマット)
# ============================================================
def write_csv(out_path: Path, race_ref: RaceRef, meta: dict, entries: list[Entry]) -> None:
    venue_code = VENUE_CODE.get(race_ref.venue, "00")
    target_date = meta.get("target_date") or f"{race_ref.date[:4]}-{race_ref.date[4:6]}-{race_ref.date[6:8]}"
    # race_key: 16桁 = YYYYMMDD + 競馬場(2) + 開催回(2) + 日目(2) + R(2) + filler(0)
    kai = meta.get("kai", 0)
    nichi_me = meta.get("nichi_me", 0)
    race_key = f"{race_ref.date}{venue_code}{kai:02d}{nichi_me:02d}{race_ref.race_no:02d}"
    # 16桁にゼロパディング (元の 16桁仕様: 8+2+2+2+2 = 16)
    race_key = race_key[:16].ljust(16, "0")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _f(v):
        """None / 空 を空文字に。float は丸めて文字列化。"""
        if v is None or v == "":
            return ""
        if isinstance(v, float):
            return f"{v:.4f}"
        return v

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        # メタ情報 (# で始まる)
        f.write(f"# race_key: {race_key}\n")
        f.write(f"# target_date: {target_date}\n")
        f.write(f"# venue: {race_ref.venue}\n")
        f.write(f"# race_no: {race_ref.race_no}\n")
        f.write(f"# race_name: {race_ref.race_name}\n")
        f.write(f"# track_type: {race_ref.track_type}\n")
        f.write(f"# race_distance: {race_ref.distance}\n")
        f.write(f"# num_horses: {len(entries)}\n")
        f.write(f"# source: jra_sp / cname={race_ref.cname}\n")
        f.write(f"# fetched_at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        # CSV ヘッダ（過去走特徴量を末尾に追加）
        writer = csv.writer(f)
        writer.writerow([
            "horse_number", "frame_number", "horse_name", "jockey_name",
            "trainer_name", "horse_weight", "horse_weight_diff",
            "carrying_weight", "horse_age", "horse_sex", "win_odds",
            # 過去走から計算した特徴量
            "n_past", "avg_finish_3", "avg_finish_5", "avg_popularity_3",
            "place_rate_track", "place_rate_course", "place_rate_distance",
            "top5_4c_rate",
        ])
        for e in entries:
            feat = e.features or HorseFeatures(0, None, None, None, None, None, None, None)
            writer.writerow([
                e.horse_number, e.frame_number, e.horse_name, e.jockey_name,
                e.trainer_name, e.horse_weight or "", e.horse_weight_diff if e.horse_weight_diff is not None else "",
                e.carrying_weight or "", e.horse_age or "", e.horse_sex or "",
                e.win_odds if e.win_odds is not None else "",
                feat.n_past,
                _f(feat.avg_finish_3), _f(feat.avg_finish_5), _f(feat.avg_popularity_3),
                _f(feat.place_rate_track), _f(feat.place_rate_course), _f(feat.place_rate_distance),
                _f(feat.top5_4c_rate),
            ])


# ============================================================
# main
# ============================================================
def main() -> int:
    p = argparse.ArgumentParser(description="JRA sp版から出馬表を取得して CSV 出力")
    p.add_argument("--date", required=True, help="開催日 YYYYMMDD")
    p.add_argument("--venue", help="競馬場名 (東京/京都/新潟 等)。省略時は全開催")
    p.add_argument("--race", type=int, help="R番号。省略時は全レース")
    p.add_argument("--output", default=str(DEFAULT_OUT), help="CSV 出力ディレクトリ")
    args = p.parse_args()

    sess = JraSession()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Step1: 開催一覧取得 ({args.date}) ===")
    kaisais = list_kaisai(sess)
    target_kaisais = [k for k in kaisais if k.date == args.date]
    if args.venue:
        target_kaisais = [k for k in target_kaisais if k.venue == args.venue]
    if not target_kaisais:
        print(f"[ERROR] {args.date} {args.venue or '全競馬場'} の開催が見つかりません。")
        print(f"  当日の開催:")
        for k in kaisais:
            print(f"    {k.venue} {k.date} (cname={k.cname})")
        return 1

    total_races = 0
    total_entries = 0
    for k in target_kaisais:
        print(f"\n=== Step2: {k.venue} {k.date} レース一覧 ===")
        races = list_races(sess, k)
        print(f"  検出 {len(races)} レース")
        for r in races:
            print(f"    {r.race_no:2d}R: {r.race_name} ({r.distance}m {r.track_type}, {r.num_horses}頭)")

        if args.race:
            races = [r for r in races if r.race_no == args.race]
            if not races:
                print(f"  [WARN] {args.race}R が見つかりません")
                continue

        for r in races:
            print(f"\n=== Step3: {k.venue} {r.race_no}R 出馬表取得 ===")
            html = sess.get_by_cname(r.cname, save_label=f"shutuba_{k.venue}_{r.race_no:02d}")
            meta, entries = parse_shutuba(html)
            print(f"  抽出: {len(entries)} 頭")
            if not entries:
                print(f"  [WARN] 出走馬が抽出できませんでした (HTML 構造確認推奨)")
                continue

            # 各馬: 過去走 → 特徴量計算
            n_with_past = 0
            for e in entries:
                e.features = compute_features(
                    past_runs=e.past_runs or [],
                    current_track_type=r.track_type,
                    current_venue=k.venue,
                    current_distance=r.distance,
                )
                if e.features.n_past > 0:
                    n_with_past += 1
            print(f"  過去走あり: {n_with_past}/{len(entries)} 頭")

            csv_name = f"jra_{k.date}_{k.venue}_{r.race_no:02d}.csv"
            out = out_dir / csv_name
            write_csv(out, r, meta, entries)
            print(f"  -> CSV: {out}")
            total_races += 1
            total_entries += len(entries)

    print(f"\n=== 完了: races={total_races}, entries={total_entries} ===")
    if total_races > 0:
        print(f"次のステップ:")
        print(f"  python scripts\\import_race_csv.py {out_dir}\\jra_{args.date}_*.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
