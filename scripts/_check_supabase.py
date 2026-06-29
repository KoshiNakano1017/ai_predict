# -*- coding: utf-8 -*-
"""Supabase の races/entries テーブルに何が入っているか確認。"""
from __future__ import annotations

import sys, io, os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from supabase import create_client

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
client = create_client(url, key)

target_date = "2026-05-23"

# races
res = client.table("races").select("race_key, target_date, venue", count="exact").eq("target_date", target_date).execute()
print(f"races on {target_date}: {res.count} 行")
for r in res.data[:3]:
    print(f"  {r}")

# entries （該当 races の entry_key を 1 件サンプル取得）
if res.data:
    rk = res.data[0]["race_key"]
    e = client.table("entries").select("entry_key, race_key, horse_number, horse_name, win_rate, star_rating", count="exact").eq("race_key", rk).execute()
    print(f"\nentries for race_key={rk}: {e.count} 行")
    for ent in e.data[:5]:
        print(f"  {ent}")
