# -*- coding: utf-8 -*-
import sys, io
import pandas as pd
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

files = sorted(Path("C:/keiba-ai/runs").glob("*/features.parquet"))
for f in files[:3] + files[-2:]:
    d = pd.read_parquet(f)
    cols = list(d.columns)
    print(f"{f.parent.name}: rows={len(d)} index={d.index.name} cols(head)={cols[:5]}, has_race_key={'race_key' in cols}")
