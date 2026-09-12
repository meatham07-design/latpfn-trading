"""Fetch Polymarket crypto Up/Down windows for any slug family (Gamma metadata +
data-api prints) into data/polymarket_<slug>/. Same schema as fetch_polymarket.py.
Usage: venv/bin/python fetch_polymarket_multi.py <slug> <step_s> <days_back>
  e.g. eth-updown-5m 300 14 ; btc-updown-15m 900 21
"""
from __future__ import annotations
import sys, time, datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_polymarket as F

slug, step, days = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
OUT = F.ROOT / "data" / f"polymarket_{slug.replace('-', '_')}"
OUT.mkdir(parents=True, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc)
LAST = int((NOW - dt.timedelta(minutes=step / 60 + 10)).timestamp()) // step * step
FROM = int((NOW - dt.timedelta(days=days)).timestamp()) // step * step

def fetch_window(ts):
    row, trades = F.fetch_window.__wrapped__(ts) if hasattr(F.fetch_window, "__wrapped__") else _fw(ts)
    return row, trades

def _fw(ts):
    ev = F.get(F.GAMMA, dict(slug=f"{slug}-{ts}"))
    if not ev:
        return dict(ts=ts, ok=0), []
    # reuse the body of F.fetch_window by monkeypatching slug: simplest is to inline
    import json, numpy as np
    e = ev[0]; m = e["markets"][0]
    meta = e.get("eventMetadata") or {}
    fs = m.get("feeSchedule") or {}
    try: op = json.loads(m.get("outcomePrices") or "[]")
    except Exception: op = []
    toks = json.loads(m.get("clobTokenIds") or "[]")
    row = dict(ts=ts, ok=1, cid=m["conditionId"], tok_up=toks[0] if toks else None,
               tok_down=toks[1] if len(toks) > 1 else None,
               up_price_final=float(op[0]) if op else np.nan,
               volume=float(m.get("volumeNum") or 0.0),
               fee_rate=float(fs.get("rate", np.nan)), fee_exp=float(fs.get("exponent", np.nan)),
               fee_rebate=float(fs.get("rebateRate", np.nan)), taker_only=bool(fs.get("takerOnly", False)),
               cfg=m.get("cryptoMarketConfigId"), tick=float(m.get("orderPriceMinTickSize") or np.nan),
               min_size=float(m.get("orderMinSize") or np.nan),
               price_to_beat=float(meta.get("priceToBeat") or np.nan),
               final_price=float(meta.get("finalPrice") or np.nan),
               closed_time=e.get("closedTime"), uma_status=m.get("umaResolutionStatus"))
    trades = []; off = 0
    while True:
        tr = F.get(F.TRADES, dict(market=row["cid"], limit=5000, offset=off))
        if tr is None:
            row["trades_ok"] = 0; break
        for t in tr:
            trades.append((ts, int(t["timestamp"]), 1 if t["side"] == "BUY" else 0,
                           1 if t["outcome"] == "Up" else 0, float(t["price"]), float(t["size"])))
        row["trades_ok"] = 1
        if len(tr) < 5000: break
        off += 5000
    row["n_trades_raw"] = len(trades)
    return row, trades

def main():
    wl = list(range(FROM, LAST + 1, step))
    done = set()
    for p in OUT.glob("meta_*.parquet"):
        done |= set(pd.read_parquet(p)["ts"].tolist())
    todo = [t for t in wl if t not in done]
    print(f"{slug}: total={len(wl)} done={len(done)} todo={len(todo)}", flush=True)
    CH = 400
    for ci in range(0, len(todo), CH):
        chunk = todo[ci:ci + CH]; t0 = time.time()
        with ThreadPoolExecutor(F.THREADS) as ex:
            res = list(ex.map(_fw, chunk))
        metas = pd.DataFrame([r for r, _ in res])
        trd = pd.DataFrame([x for _, lst in res for x in lst], columns=["ts", "t", "buy", "up", "price", "size"])
        trd = trd.astype({"ts": "int64", "t": "int64", "buy": "int8", "up": "int8", "price": "float32", "size": "float32"})
        tag = f"{chunk[0]}_{chunk[-1]}"
        metas.to_parquet(OUT / f"meta_{tag}.parquet", index=False)
        trd.to_parquet(OUT / f"trades_{tag}.parquet", index=False)
        print(f"chunk {ci//CH} {tag} n={len(chunk)} trades={len(trd)} {time.time()-t0:.0f}s", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
