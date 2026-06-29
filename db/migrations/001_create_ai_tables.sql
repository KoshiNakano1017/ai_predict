-- ============================================================
-- AI用 PostgreSQL (keiba_ai DB) テーブル定義
-- 冪等実行可能: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
-- 実行例:
--   psql -U ai_runner -d keiba_ai -f 001_create_ai_tables.sql
-- ============================================================

-- ──────────────────────────────────────────
-- raw_races  SQLiteから取り込んだレース基本情報
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_races (
    race_key            TEXT        PRIMARY KEY,
    target_date         DATE        NOT NULL,
    venue               TEXT,
    race_no             INTEGER,
    track_type          TEXT,
    race_distance       INTEGER,
    track_condition     TEXT,
    weather             TEXT,
    num_horses          INTEGER,
    straight_distance   INTEGER,
    prize_money_1st     BIGINT,
    start_time          TEXT,
    race_class_code     TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_races_target_date ON raw_races (target_date);

-- ──────────────────────────────────────────
-- raw_entries  SQLiteから取り込んだ出走馬情報 + 特徴量
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_entries (
    entry_key               TEXT        PRIMARY KEY,
    race_key                TEXT        NOT NULL REFERENCES raw_races(race_key) ON DELETE CASCADE,
    horse_number            INTEGER,
    frame_number            INTEGER,
    horse_key               TEXT,
    horse_name              TEXT,
    jockey_code             TEXT,
    jockey_name             TEXT,
    trainer_code            TEXT,
    trainer_name            TEXT,
    horse_weight            NUMERIC,
    horse_weight_diff       NUMERIC,
    carrying_weight         NUMERIC,
    horse_age               INTEGER,
    horse_sex               TEXT,
    -- AI features
    avg_finish_3            NUMERIC,
    avg_finish_5            NUMERIC,
    avg_popularity_3        NUMERIC,
    place_rate_track        NUMERIC,
    place_rate_course       NUMERIC,
    place_rate_distance     NUMERIC,
    turn_aptitude           NUMERIC,
    position_index          NUMERIC,
    position_index_rank     INTEGER,
    predicted_running_style INTEGER,
    top5_4c_rate            NUMERIC,
    top3_finish_rate        NUMERIC,
    pci                     NUMERIC,
    rest_weeks              NUMERIC,
    runs_since_return       INTEGER,
    distance_change         INTEGER,
    weight_correction       NUMERIC,
    weight_correction_finish NUMERIC,
    win_recovery_rate       NUMERIC,
    place_recovery_rate     NUMERIC,
    slope_1_4f              NUMERIC,
    slope_1_1f              NUMERIC,
    slope_2_4f              NUMERIC,
    wood_1_4f               NUMERIC,
    wood_1_1f               NUMERIC,
    -- オッズ
    win_odds                NUMERIC,
    popularity_rank         INTEGER,
    place_odds_low          NUMERIC,
    place_odds_high         NUMERIC,
    odds_snapshot_at        TIMESTAMPTZ,
    -- CrossFactor 追加
    jockey_win_rate_all     NUMERIC,
    jockey_win_rate_course  NUMERIC,
    trainer_win_rate_all    NUMERIC,
    jockey_change           BOOLEAN,
    user_index_1            NUMERIC,
    finish_position         INTEGER,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_entries_race_key ON raw_entries (race_key);
CREATE INDEX IF NOT EXISTS idx_raw_entries_horse_key ON raw_entries (horse_key);

-- ──────────────────────────────────────────
-- features  特徴量確定版（正規化・エンコード済み）
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS features (
    entry_key       TEXT        PRIMARY KEY,
    race_key        TEXT        NOT NULL,
    feature_data    JSONB       NOT NULL,   -- 全特徴量列をJSONBで格納（柔軟拡張用）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_features_race_key ON features (race_key);

-- ──────────────────────────────────────────
-- predictions_staging  推論結果ステージング
-- Supabaseへupsertする前の最終成果物バッファ
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions_staging (
    entry_key               TEXT        NOT NULL,
    race_key                TEXT        NOT NULL,
    inference_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version           TEXT        NOT NULL,
    -- 確率
    win_prob                NUMERIC,    -- 勝率 (%)
    top2_prob               NUMERIC,    -- 連対率 (%)
    top3_prob               NUMERIC,    -- 複勝率 (%)
    -- 期待値
    expected_value_win      NUMERIC,
    expected_value_place    NUMERIC,
    -- ★評価
    star_rating             TEXT,
    ai_comment              TEXT,
    -- Supabase反映済みフラグ
    published_to_supabase   BOOLEAN     NOT NULL DEFAULT FALSE,
    published_at            TIMESTAMPTZ,
    PRIMARY KEY (entry_key, inference_at)
);

CREATE INDEX IF NOT EXISTS idx_predictions_staging_race_key   ON predictions_staging (race_key);
CREATE INDEX IF NOT EXISTS idx_predictions_staging_unpublished ON predictions_staging (published_to_supabase)
    WHERE NOT published_to_supabase;

-- ──────────────────────────────────────────
-- job_runs  バッチ実行ログ
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_runs (
    id              BIGSERIAL   PRIMARY KEY,
    job_name        TEXT        NOT NULL,          -- daily_evening / race_day_morning / pre_race / backfill
    target_date     DATE        NOT NULL,
    mode            TEXT        NOT NULL,
    model_version   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running',  -- running / success / failed
    rows_raw_races  INTEGER,
    rows_raw_entries INTEGER,
    rows_features   INTEGER,
    rows_predictions INTEGER,
    rows_published  INTEGER,
    error_message   TEXT,
    log_path        TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_runs_target_date ON job_runs (target_date);
CREATE INDEX IF NOT EXISTS idx_job_runs_status      ON job_runs (status);
