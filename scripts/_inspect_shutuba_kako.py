# -*- coding: utf-8 -*-
"""tr_kako の中身（過去走テキスト）を 3 馬分表示してパース戦略を立てる。"""
from __future__ import annotations

import sys, io, re
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

f = Path(r"scripts\raw_html\jra_sp\sw01dde0105202602090120260523_09_shutuba_東京_01.html")
html = f.read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")
table = soup.find("div", id="umabashira")

trs = table.find_all("tr")
horses_seen = 0
for i, tr in enumerate(trs):
    cls = tr.get("class") or []
    if "tr_kako" in cls:
        td = tr.find("td", class_="td_kako")
        if not td:
            continue
        text = td.get_text(separator=" ", strip=True)
        # 前走/前々走/3走前/4走前 で分割
        sections = re.split(r"(前走|前々走|\d走前)", text)
        # sections = ["", "前走", "<前走の内容>", "前々走", "<前々走の内容>", ...]
        print(f"--- tr[{i}] ---")
        print(f"raw: {text[:500]}")
        print(f"  分割数: {len(sections)}")
        for j in range(1, len(sections), 2):
            label = sections[j]
            content = sections[j+1] if j+1 < len(sections) else ""
            print(f"  [{label}] {content[:200]}")
        print()
        horses_seen += 1
        if horses_seen >= 3:
            break
