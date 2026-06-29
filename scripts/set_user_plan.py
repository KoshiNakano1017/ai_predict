# -*- coding: utf-8 -*-
"""Supabase public.users.plan を email 指定で更新するテスト用スクリプト。

実行例:
  python scripts/set_user_plan.py nakano1017rec@gmail.com pro
  python scripts/set_user_plan.py user@example.com trial --trial-days 30
  python scripts/set_user_plan.py user@example.com expired

前提:
  - source/.env.local もしくは .env に
      SUPABASE_URL (= NEXT_PUBLIC_SUPABASE_URL)
      SUPABASE_SERVICE_ROLE_KEY
    が定義されていること
  - 対象ユーザーが Supabase Auth にサインアップ済みであること
    （未登録なら先にアプリの /signup から登録）
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    print("[ERROR] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を環境変数で設定してください")
    print(f"  探索パス: {ROOT}/.env, {ROOT}/source/.env.local")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("[ERROR] supabase が必要です: pip install supabase", file=sys.stderr)
    sys.exit(1)

VALID_PLANS = ("trial", "expired", "pro")


def find_user_by_email(sb, email: str):
    """Auth Admin API でメールアドレス一致ユーザーを探す（ページネーション対応）。"""
    target = email.strip().lower()
    page = 1
    per_page = 200
    while True:
        resp = sb.auth.admin.list_users(page=page, per_page=per_page)
        users = getattr(resp, "users", None)
        if users is None:
            users = resp if isinstance(resp, list) else []
        if not users:
            return None
        for u in users:
            u_email = getattr(u, "email", None)
            if u_email is None and isinstance(u, dict):
                u_email = u.get("email")
            if u_email and u_email.strip().lower() == target:
                return u
        if len(users) < per_page:
            return None
        page += 1
        if page > 50:
            print("[WARN] 50ページ走査しても見つかりません。中断します。")
            return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Supabase public.users.plan を email で更新するテスト用スクリプト"
    )
    parser.add_argument("email", help="対象ユーザーのメールアドレス")
    parser.add_argument("plan", choices=VALID_PLANS, help="設定するプラン")
    parser.add_argument(
        "--trial-days",
        type=int,
        default=None,
        help="trial 設定時の trial_ends_at を今からN日後に上書き（plan='trial' のみ有効）",
    )
    args = parser.parse_args()

    print(f"[set-plan] Supabase URL: {SUPABASE_URL}")
    print(f"[set-plan] Email      : {args.email}")
    print(f"[set-plan] Plan       : {args.plan}")
    if args.plan == "trial" and args.trial_days is not None:
        print(f"[set-plan] trial_days : +{args.trial_days} days")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    user = find_user_by_email(sb, args.email)
    if not user:
        print(f"[ERROR] auth.users に email={args.email} のユーザーが見つかりません。")
        print("  → 先にアプリの /signup でサインアップしてください。")
        return 1

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if not user_id:
        print("[ERROR] ユーザーの id を取得できませんでした。")
        return 1

    print(f"[set-plan] auth.users.id = {user_id}")

    payload: dict = {"id": user_id, "plan": args.plan}

    if args.plan == "trial" and args.trial_days is not None:
        ends_at = datetime.now(timezone.utc) + timedelta(days=args.trial_days)
        payload["trial_ends_at"] = ends_at.isoformat()
    elif args.plan in ("expired", "pro"):
        payload["trial_ends_at"] = None

    res = sb.table("users").upsert(payload, on_conflict="id").execute()
    if not res.data:
        print("[ERROR] upsert 結果が空です。RLS設定や service_role key を確認してください。")
        return 1
    print(f"[set-plan] users upsert OK: {res.data[0]}")

    chk = (
        sb.table("users")
        .select("id, plan, role, trial_ends_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    print(f"[set-plan] 確認        : {chk.data}")
    print("[set-plan] 完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
