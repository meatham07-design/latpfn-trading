"""Write data/MANIFEST.md listing every parquet: rows, date range."""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA

rows = []
for p in sorted(DATA.glob("*.parquet")):
    df = pd.read_parquet(p)
    if isinstance(df.index, pd.DatetimeIndex) and len(df):
        rng = f"{df.index.min():%Y-%m-%d %H:%M} -> {df.index.max():%Y-%m-%d %H:%M} UTC ({(df.index.max()-df.index.min()).days}d)"
    else:
        rng = "-"
    rows.append((p.name, len(df), rng, ", ".join(map(str, df.columns))))
probs = []
for f in ("_hl_problems.json", "_yf_problems.json"):
    if (DATA / f).exists():
        probs += json.loads((DATA / f).read_text())
lines = ["# edge_hunt data MANIFEST", "",
         f"Built {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M UTC}. All indexes are tz-aware UTC 'time' = bar OPEN time.",
         "Hyperliquid candle close = perp mark/last. Funding rate is the hourly fraction.",
         "yf_MBT_F_1d.parquet is DERIVED (resampled from yf_MBT_F_1h, CME 18:00 ET session days) because Yahoo has no daily history for MBT=F.",
         "", "| file | rows | range | columns |", "|---|---:|---|---|"]
lines += [f"| {n} | {r} | {g} | {c} |" for n, r, g, c in rows]
lines += ["", "## Fetch problems", ""] + ([f"- {p}" for p in probs] or ["- none"])
(DATA / "MANIFEST.md").write_text("\n".join(lines) + "\n")
print(f"{len(rows)} files; problems={probs}")
