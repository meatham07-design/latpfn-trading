"""Fetch fill history for a survivorship-aware panel of Hyperliquid wallets (public userFillsByTime).
Panel = top 300 by 30d PnL (>= $100k 30d volume) + bottom 100 + 150 random active wallets from the public
leaderboard snapshot (stats-data.hyperliquid.xyz/Mainnet/leaderboard, cached leaderboard_2026-08-28.parquet).
Pages BACKWARD from now (most recent first), at most MAX_PAGES x 2000 fills or back to MIN_TIME.
Cache: data/hl_wallets/fills/<addr>.parquet ; panel: data/hl_wallets/panel.parquet.  Resumable; per-wallet checkpoint.
usage: fetch_hl_wallets.py <worker_id> <n_workers>"""
import json, time, sys
from pathlib import Path
import numpy as np, pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
WD = ROOT / "data" / "hl_wallets"; FD = WD / "fills"; FD.mkdir(parents=True, exist_ok=True)
U = "https://api.hyperliquid.xyz/info"
MAX_PAGES = 4
MIN_TIME = int(pd.Timestamp("2025-05-01", tz="UTC").timestamp() * 1000)
wid, nw = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)

lb = pd.read_parquet(WD / "leaderboard_2026-08-28.parquet")
panel_path = WD / "panel.parquet"
if panel_path.exists():
    panel = pd.read_parquet(panel_path)
else:
    rng = np.random.default_rng(20260828)
    active = lb[lb.m_vlm >= 1e5].copy()
    top = active.sort_values("m_pnl", ascending=False).head(300).assign(group="top")
    bot = active.sort_values("m_pnl", ascending=True).head(100).assign(group="bottom")
    rest = active[~active.addr.isin(top.addr) & ~active.addr.isin(bot.addr)]
    rnd = rest.iloc[rng.choice(len(rest), 150, replace=False)].assign(group="random")
    panel = pd.concat([top, bot, rnd], ignore_index=True)
    panel.to_parquet(panel_path)

log = open(WD / f"_fetch_w{wid}.log", "a")
NOW = int(time.time() * 1000) + 60_000
for i, row in panel.iterrows():
    if i % nw != wid:
        continue
    addr = row.addr
    out = FD / f"{addr}.parquet"
    if out.exists():
        continue
    allf, end, pages, ok = [], NOW, 0, True
    while True:
        f = None
        for attempt in range(6):
            try:
                t0 = time.time()
                r = requests.post(U, json={"type": "userFillsByTime", "user": addr, "startTime": MIN_TIME,
                                           "endTime": end, "aggregateByTime": True}, timeout=90)
                if r.status_code == 429:
                    print("429", addr, file=log, flush=True); time.sleep(15 * (attempt + 1)); continue
                f = r.json()
                if not isinstance(f, list):
                    raise RuntimeError(str(f)[:200])
                break
            except Exception as e:
                print("retry", addr, attempt, repr(e)[:120], file=log, flush=True); time.sleep(4 * (attempt + 1)); f = None
        if f is None:
            ok = False; break
        allf += f; pages += 1
        print(f"  page {pages} n={len(f)} {time.time()-t0:.1f}s", file=log, flush=True)
        if len(f) < 2000 or pages >= MAX_PAGES:
            break
        end = min(x["time"] for x in f) - 1
        time.sleep(0.5)
    if not ok:
        print("FAILED", addr, file=log, flush=True); continue
    cols = ["coin","px","sz","side","time","startPosition","dir","closedPnl","hash","oid","crossed","fee","tid","feeToken","twapId"]
    if allf:
        df = pd.DataFrame(allf)
        for c in ("px", "sz", "startPosition", "closedPnl", "fee"):
            df[c] = df[c].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        df = df.drop_duplicates("tid").sort_values("time")
        df["truncated"] = bool(pages >= MAX_PAGES and len(allf) >= 2000 * MAX_PAGES)
    else:
        df = pd.DataFrame(columns=cols + ["truncated"])
    df.to_parquet(out)
    print(f"{i} {row.group} {addr} fills={len(df)} pages={pages} first={df.time.min() if len(df) else None}", file=log, flush=True)
    time.sleep(0.5)
print("DONE", file=log, flush=True)
