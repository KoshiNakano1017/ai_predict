-- races / entries テーブル定義 (12_抽出スクリプト設計書.md + src/types/race.ts 準拠)
-- Supabase Dashboard > SQL Editor で実行する

-- 1. races テーブル -----------------------------------------------------------------
create table if not exists public.races (
  race_key           text primary key,          -- 16桁: YYYY+MMDD+競馬場+回+日目+R番号
  target_date        date not null,             -- 開催日 (YYYY-MM-DD)
  venue              text not null,             -- 競馬場名 (東京・阪神 等)
  race_no            smallint not null,         -- レース番号 (1-12)
  track_type         text,                      -- 芝/ダート/障害
  race_distance      smallint,                  -- 距離 (m)
  track_condition    text,                      -- 馬場状態
  weather            text,                      -- 天候
  num_horses         smallint,                  -- 出走頭数
  straight_distance  smallint,                  -- 直線距離 (m)
  prize_money_1st    integer,                   -- 1着本賞金 (万円)
  start_time         text,                      -- 発走時刻 (HHMM)
  race_class_code    text,                      -- 競走種別コード
  created_at         timestamptz default now(),
  updated_at         timestamptz default now()
);

-- 2. entries テーブル ---------------------------------------------------------------
create table if not exists public.entries (
  entry_key              text primary key,     -- 18桁: race_key + 馬番
  race_key               text not null references public.races(race_key),
  horse_number           smallint not null,    -- 馬番
  frame_number           smallint,             -- 枠番
  horse_key              text,                 -- 血統登録番号
  horse_name             text,                 -- 馬名
  jockey_code            text,
  jockey_name            text,
  trainer_code           text,
  trainer_name           text,
  horse_weight           smallint,             -- 馬体重 (kg)
  horse_weight_diff      smallint,             -- 馬体重増減
  carrying_weight        real,                 -- 斤量
  horse_age              smallint,
  horse_sex              text,

  -- CrossFactor 特徴量
  avg_finish_3           real,
  avg_finish_5           real,
  avg_popularity_3       real,
  place_rate_track       real,
  place_rate_course      real,
  place_rate_distance    real,
  turn_aptitude          real,
  position_index         real,
  position_index_rank    smallint,
  predicted_running_style smallint,
  top5_4c_rate           real,
  top3_finish_rate       real,
  pci                    real,
  rest_weeks             smallint,
  runs_since_return      smallint,
  distance_change        smallint,
  weight_correction      real,
  weight_correction_finish real,
  win_recovery_rate      real,
  place_recovery_rate    real,
  slope_1_4f             real,
  slope_1_1f             real,
  slope_2_4f             real,
  wood_1_4f              real,
  wood_1_1f              real,
  user_index_1           real,

  -- オッズ
  win_odds               real,
  popularity_rank        smallint,
  place_odds_low         real,
  place_odds_high        real,
  odds_snapshot_at       text,

  -- 着順 (バックテスト / 学習用)
  finish_position        smallint,

  -- AI 予測結果 (推論後に更新)
  win_rate               real,                 -- 勝率 (%)
  place_rate             real,                 -- 連対率 (%)
  show_rate              real,                 -- 複勝率 (%)
  expected_value_win     real,                 -- 単勝期待値
  expected_value_place   real,                 -- 複勝期待値
  star_rating            text check (star_rating in ('★', '▲', '⚠', '◆') or star_rating is null),
  ai_comment             text,

  created_at             timestamptz default now(),
  updated_at             timestamptz default now()
);

-- 3. インデックス -------------------------------------------------------------------
create index if not exists idx_entries_race_key on public.entries(race_key);
create index if not exists idx_races_target_date on public.races(target_date);

-- 4. RLS 有効化 -------------------------------------------------------------------
alter table public.races   enable row level security;
alter table public.entries enable row level security;

-- 5. races: 全員読み取り可 --------------------------------------------------------
create policy "races_select_all"
  on public.races for select
  using (true);

-- 6. entries: 基本情報は全員読み取り可 -----------------------------------------------
--    予測列 (win_rate 等) は Pro/Trial ユーザーのみ。
--    フロント側で policy チェックするため、DB レベルでは全カラム公開とし
--    必要に応じて View + RLS で絞り込む方式に移行可能。
create policy "entries_select_all"
  on public.entries for select
  using (true);

-- 7. service_role からの INSERT/UPDATE/UPSERT は RLS バイパス (バッチ投入用) --------
--    service_role キーは .env のみに保持し、フロントには公開しない。

-- 8. updated_at 自動更新 trigger --------------------------------------------------
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_races_updated_at
  before update on public.races
  for each row execute function public.set_updated_at();

create trigger set_entries_updated_at
  before update on public.entries
  for each row execute function public.set_updated_at();
