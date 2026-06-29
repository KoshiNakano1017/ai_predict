"""pytest 共通設定。

`tests/` 配下から `extract` / `transform` / `load` 等のトップレベルパッケージを
import できるようプロジェクトルートを sys.path に追加する。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
