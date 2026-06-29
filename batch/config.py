"""設定ファイル読込と環境変数バリデーション。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _ROOT / "config.yaml"


@dataclass
class SqliteConfig:
    path: str
    timeout_sec: int = 30
    retry_count: int = 3
    retry_interval_sec: int = 10


@dataclass
class BatchConfig:
    run_dir: str
    log_dir: str
    checkpoint_file: str
    intermediate_retention_days: int = 7


@dataclass
class SupabaseConfig:
    url: str
    service_role_key: str
    retry_count: int = 3
    retry_intervals_sec: List[int] = field(default_factory=lambda: [5, 15, 30])


@dataclass
class MailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    mail_from: str
    to: List[str]


@dataclass
class VmDbConfig:
    """VM 内 PostgreSQL (AI用) 接続設定。"""
    host: str = "localhost"
    port: int = 5432
    dbname: str = "keiba_ai"
    user: str = "ai_runner"
    password: str = ""
    dsn: str = ""          # 直接 DSN を指定する場合（設定されていればこちら優先）


@dataclass
class InferenceConfig:
    model_dir: str
    win_model: str
    top2_model: str
    top3_model: str
    model_version: str = "v1.0.0"   # Supabase反映時に必須
    star_ev_threshold: float = 1.05
    triangle_ev_threshold: float = 1.02
    longshot_popularity_rank: int = 5
    risky_favorite_rank: int = 3


@dataclass
class AppConfig:
    timezone: str
    environment: str
    sqlite: SqliteConfig
    batch: BatchConfig
    supabase: SupabaseConfig
    mail: MailConfig
    inference: InferenceConfig
    vm_db: VmDbConfig = field(default_factory=VmDbConfig)


def load(config_path: Optional[str] = None, env_file: Optional[str] = None) -> AppConfig:
    """設定ファイルと環境変数を読み込んで AppConfig を返す。"""
    env_path = env_file or (_ROOT / ".env")
    if Path(str(env_path)).exists():
        load_dotenv(env_path)

    cfg_path = config_path or _DEFAULT_CONFIG
    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    def _env(key: str, default: str = "") -> str:
        val = os.getenv(key, default)
        return val

    def _env_required(key: str) -> str:
        val = os.getenv(key)
        if not val:
            raise EnvironmentError(f"環境変数 {key} が未設定です。.env を確認してください。")
        return val

    mail_to_env = os.getenv("MAIL_TO", "")
    mail_to = [a.strip() for a in mail_to_env.split(",") if a.strip()] \
              or raw.get("mail", {}).get("to", [])

    return AppConfig(
        timezone=raw["app"]["timezone"],
        environment=raw["app"]["environment"],
        sqlite=SqliteConfig(
            path=raw["sqlite"]["path"],
            timeout_sec=raw["sqlite"].get("timeout_sec", 30),
            retry_count=raw["sqlite"].get("retry_count", 3),
            retry_interval_sec=raw["sqlite"].get("retry_interval_sec", 10),
        ),
        batch=BatchConfig(
            run_dir=raw["batch"]["run_dir"],
            log_dir=raw["batch"]["log_dir"],
            checkpoint_file=raw["batch"]["checkpoint_file"],
            intermediate_retention_days=raw["batch"].get("intermediate_retention_days", 7),
        ),
        supabase=SupabaseConfig(
            url=_env_required(_env_key(raw, "supabase", "url_env", "SUPABASE_URL")),
            service_role_key=_env_required(_env_key(raw, "supabase", "key_env", "SUPABASE_SERVICE_ROLE_KEY")),
            retry_count=raw["supabase"].get("retry_count", 3),
            retry_intervals_sec=raw["supabase"].get("retry_intervals_sec", [5, 15, 30]),
        ),
        mail=MailConfig(
            smtp_host=_env(_env_key(raw, "mail", "smtp_host_env", "SMTP_HOST")),
            smtp_port=int(_env(_env_key(raw, "mail", "smtp_port_env", "SMTP_PORT"),
                               str(raw["mail"].get("smtp_port_default", 587)))),
            username=_env(_env_key(raw, "mail", "username_env", "SMTP_USER")),
            password=_env(_env_key(raw, "mail", "password_env", "SMTP_PASSWORD")),
            mail_from=_env(_env_key(raw, "mail", "from_env", "MAIL_FROM")),
            to=mail_to,
        ),
        inference=InferenceConfig(
            model_dir=raw["inference"]["model_dir"],
            win_model=raw["inference"]["win_model"],
            top2_model=raw["inference"]["top2_model"],
            top3_model=raw["inference"]["top3_model"],
            model_version=_env("MODEL_VERSION", raw["inference"].get("model_version", "v1.0.0")),
            star_ev_threshold=raw["inference"].get("star_ev_threshold", 1.05),
            triangle_ev_threshold=raw["inference"].get("triangle_ev_threshold", 1.02),
            longshot_popularity_rank=raw["inference"].get("longshot_popularity_rank", 5),
            risky_favorite_rank=raw["inference"].get("risky_favorite_rank", 3),
        ),
        vm_db=VmDbConfig(
            host=_env("AI_DB_HOST", raw.get("vm_db", {}).get("host", "localhost")),
            port=int(_env("AI_DB_PORT", str(raw.get("vm_db", {}).get("port", 5432)))),
            dbname=_env("AI_DB_NAME", raw.get("vm_db", {}).get("dbname", "keiba_ai")),
            user=_env("AI_DB_USER", raw.get("vm_db", {}).get("user", "ai_runner")),
            password=_env("AI_DB_PASSWORD", raw.get("vm_db", {}).get("password", "")),
            dsn=_env("AI_DB_DSN", ""),
        ),
    )


def _env_key(raw: dict, section: str, key: str, fallback: str) -> str:
    return raw.get(section, {}).get(key, fallback)
