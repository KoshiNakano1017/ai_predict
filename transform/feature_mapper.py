"""CrossFactor SQLite の列名 -> 内部特徴量名 のマッピング。

列名が変わった場合はここだけ修正する。
>> 実際のカラム名は CrossFactor DB の実データで確認が必要 (§17.1 の確認事項)。
   特に「ウッドチップ調教」カラムのプレフィックスが空白始まり ("_直近1_4F合計") のため
   実テーブルの実際のカラム名を確認してから定数を確定すること。
"""
from __future__ import annotations

from typing import Dict

# --- レース基本情報 (JVレース詳細EX) ---
RACE_COLUMN_MAP: Dict[str, str] = {
    "開催年":       "kai_nen",
    "開催月日":     "kai_tsuki_hi",
    "競馬場":       "keibajo",
    "開催回":       "kai",
    "開催日目":     "nichi_me",
    "番号":         "race_no",
    "距離":         "race_distance",
    "（芝ダ）区分": "track_type_code",
    "芝馬場状態":   "track_condition_turf",
    "ダ馬場状態":   "track_condition_dirt",
    "天候":         "weather",
    "競走種別":     "race_class_code",
    "競走条件":     "race_condition",
    "出走頭数":     "num_horses",
    "G前直線距離":  "straight_distance",
    "本賞金1":      "prize_money_1st",
    "発走時刻":     "start_time",
}

# --- 出走馬情報 (JV馬毎レース情報EX) ---
# 馬名・騎手名・調教師名は JV馬毎レース情報EX 自体に格納されているため
# マスタ結合に頼らず取得する。マスタは欠損時のフォールバック用に使う。
# 列番号: 17=馬名 / 24=調教師(コード) / 25=調教師名略称 / 153=騎手名 / 154=調教師名
ENTRY_COLUMN_MAP: Dict[str, str] = {
    "血統登録番号":       "horse_key",
    "馬番":              "horse_number",
    "枠番":              "frame_number",
    "馬名":              "horse_name",
    "斤量":              "carrying_weight",
    "馬体重":            "horse_weight",
    "馬体重増減":         "horse_weight_diff",
    "騎手名":            "jockey_name",
    "調教師":            "trainer_code",
    "調教師名":          "trainer_name",
    "平均着順_前3走":     "avg_finish_3",
    "平均着順_前5走":     "avg_finish_5",
    "平均人気_前3走":     "avg_popularity_3",
    "着度数P_馬場適性":   "place_rate_track",
    "着度数P_競馬場":     "place_rate_course",
    "着度数P_同距離":     "place_rate_distance",
    "着度数P_回り適性":   "turn_aptitude",
    "位置取り指数":       "position_index",
    "位置取り指数順位":   "position_index_rank",
    "予想脚質":           "predicted_running_style",
    "4角5番手内率":       "top5_4c_rate",
    "上がり3位内率":      "top3_finish_rate",
    "PCI":               "pci",
    "休養週数":           "rest_weeks",
    "休養後何走目":       "runs_since_return",
    "距離増減":           "distance_change",
    "斤量補正値":         "weight_correction",
    "斤量補正値_上がり":  "weight_correction_finish",
    "競走馬単勝回収率":   "win_recovery_rate",
    "競走馬複勝回収率":   "place_recovery_rate",
    "坂路_直近1_4F合計":  "slope_1_4f",
    "坂路_直近1_1F":      "slope_1_1f",
    "坂路_直近2_4F合計":  "slope_2_4f",
    # ウッドチップ: 先頭スペースまたは別プレフィックスの可能性あり -> 要確認
    "_直近1_4F合計":      "wood_1_4f",
    "_直近1_1F":          "wood_1_1f",
    "USER_指数1":         "user_index_1",
    "USER_指数2":         "user_index_2",
    "USER_指数3":         "user_index_3",
    "確定着順":           "finish_position",
    "乗り":              "jockey_code",
}

# --- マスタ結合用カラム ---
# JV馬毎レース情報EX に騎手名・調教師名が既に格納されているため、
# マスタから取得する値は欠損時のフォールバック用として扱う。
MASTER_COLUMN_MAP: Dict[str, str] = {
    # JV競走馬マスタ (馬齢・性別補完用)
    "生年月日":    "birth_date",
    "性別":        "horse_sex",
    # JV騎手マスタ (騎手名のフォールバック用)
    "騎手名":      "jockey_name",
    # JV調教師マスタ (調教師名のフォールバック用)
    "調教師名":    "trainer_name",
    "調教師コード": "trainer_code",
}

# --- オッズ (JVオッズ_単複枠) ---
ODDS_COLUMN_MAP: Dict[str, str] = {
    "発表月日時分": "odds_published_at",
    "単勝オッズ":   "win_odds_raw",   # 要変換: 文字列 "1500" -> 15.0 倍
    "複勝オッズ下": "place_odds_low_raw",
    "複勝オッズ上": "place_odds_high_raw",
}

# --- 払戻 (JV払戻) ---
PAYOUT_COLUMN_MAP: Dict[str, str] = {
    "単勝払戻": "win_payout",
    "複勝払戻": "place_payout",
}

# --- 競馬場コード -> 場所名変換 ---
KEIBAJO_CODE_MAP: Dict[str, str] = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}

# --- 芝ダ区分コード -> 文字変換 ---
TRACK_TYPE_MAP: Dict[str, str] = {
    "1": "芝", "2": "ダート", "3": "障害",
}

# --- 馬場状態コード -> 文字変換 ---
TRACK_CONDITION_MAP: Dict[str, str] = {
    "1": "良", "2": "稍重", "3": "重", "4": "不良",
}

# --- 性別コード -> 文字変換 ---
SEX_MAP: Dict[str, str] = {
    "1": "牡", "2": "牝", "3": "騸",
}


def map_race_columns(row: dict) -> dict:
    """JVレース詳細EX の行を内部列名に変換する。"""
    out = {}
    for orig, new in RACE_COLUMN_MAP.items():
        if orig in row:
            out[new] = row[orig]
    # コード -> 文字列変換
    out["track_type"] = TRACK_TYPE_MAP.get(str(out.get("track_type_code", "")), "不明")
    out["venue"] = KEIBAJO_CODE_MAP.get(str(out.get("keibajo", "")).zfill(2), str(out.get("keibajo", "")))
    track_cond_code = str(out.get("track_condition_turf") or out.get("track_condition_dirt") or "")
    out["track_condition"] = TRACK_CONDITION_MAP.get(track_cond_code, "不明")
    return out


def map_entry_columns(row: dict) -> dict:
    """JV馬毎レース情報EX の行を内部列名に変換する。"""
    out = {}
    for orig, new in ENTRY_COLUMN_MAP.items():
        if orig in row:
            out[new] = row[orig]
    return out


def map_odds_columns(row: dict) -> dict:
    """JVオッズ_単複枠 の行を内部列名に変換する。"""
    out = {}
    for orig, new in ODDS_COLUMN_MAP.items():
        if orig in row:
            out[new] = row[orig]
    # オッズ変換: 08_CrossFactor_DB定義書 JV馬毎レース情報EX 単勝列の備考
    # 「単勝。÷10で入れる。」に従い、DB値を 10 で割って実倍率に戻す。
    # 例: DB値 "150" -> 15.0 倍 / DB値 "35" -> 3.5 倍
    # >> JVオッズ_単複枠 の格納形式が異なる場合は実データ確認後に調整すること
    for raw_key, parsed_key in [
        ("win_odds_raw", "win_odds"),
        ("place_odds_low_raw", "place_odds_low"),
        ("place_odds_high_raw", "place_odds_high"),
    ]:
        raw_val = out.get(raw_key)
        if raw_val is not None:
            try:
                out[parsed_key] = int(str(raw_val)) / 10.0
            except (ValueError, TypeError):
                out[parsed_key] = None
    return out
