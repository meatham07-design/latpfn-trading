"""Fetch Polymarket BTC 5-minute Up/Down windows (Gamma metadata + data-api fills)
into data/polymarket/. Public read-only endpoints. Resumable, chunked parquet.

Sample: every window in the last 3 weeks + N_PER_MONTH random windows per month
from 2026-02-12 (first traded window) to the start of the full-coverage span.
Run: venv/bin/python fetch_polymarket.py
"""
from __future__ import annotations
import json, sys, time, datetime as dt, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, pandas as pd, numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "polymarket"
OUT.mkdir(parents=True, exist_ok=True)
GAMMA = "https://gamma-api.polymarket.com/events"
TRADES = "https://data-api.polymarket.com/trades"
FIRST = dt.datetime(2026, 2, 12, 0, 0, tzinfo=dt.timezone.utc)
NOW = dt.datetime.now(dt.timezone.utc)
FULL_FROM = (NOW - dt.timedelta(days=21)).replace(minute=0, second=0, microsecond=0)
LAST = (NOW - dt.timedelta(minutes=15)).timestamp() // 300 * 300  # resolved windows only
N_PER_MONTH = 450
THREADS = 8
CHUNK = 400

def window_list():
    rng = random.Random(20260827)
    full = list(range(int(FULL_FROM.timestamp()) // 300 * 300, int(LAST) + 1, 300))
    strat = []
    m = FIRST
    while m < FULL_FROM:
        m_end = (m.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0)
        m_end = min(m_end, FULL_FROM)
        cand = list(range(int(m.timestamp()) // 300 * 300, int(m_end.timestamp()), 300))
        strat += sorted(rng.sample(cand, min(N_PER_MONTH, len(cand))))
        m = m_end
    return sorted(set(strat + full))

S = requests.Session()

def get(url, params, tries=6):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (k + 1)); continue
            return None
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None

def fetch_window(ts: int):
    ev = get(GAMMA, dict(slug=f"btc-updown-5m-{ts}"))
    if not ev:
        return dict(ts=ts, ok=0), []
    e = ev[0]; m = e["markets"][0]
    meta = e.get("eventMetadata") or {}
    fs = m.get("feeSchedule") or {}
    try:
        op = json.loads(m.get("outcomePrices") or "[]")
    except Exception:
        op = []
    toks = json.loads(m.get("clobTokenIds") or "[]")
    row = dict(ts=ts, ok=1, cid=m["conditionId"], tok_up=toks[0] if toks else None,
               tok_down=toks[1] if len(toks) > 1 else None,
               up_price_final=float(op[0]) if op else np.nan,
               volume=float(m.get("volumeNum") or 0.0),
               fee_rate=float(fs.get("rate", np.nan)), fee_exp=float(fs.get("exponent", np.nan)),
               fee_rebate=float(fs.get("rebateRate", np.nan)),
               cfg=m.get("cryptoMarketConfigId"), tick=float(m.get("orderPriceMinTickSize") or np.nan),
               min_size=float(m.get("orderMinSize") or np.nan),
               price_to_beat=float(meta.get("priceToBeat") or np.nan),
               final_price=float(meta.get("finalPrice") or np.nan),
               closed_time=e.get("closedTime"), uma_status=m.get("umaResolutionStatus"))
    trades = []
    off = 0
    while True:
        tr = get(TRADES, dict(market=row["cid"], limit=5000, offset=off))
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
    wl = window_list()
    done = set()
    for p in OUT.glob("meta_*.parquet"):
        done |= set(pd.read_parquet(p)["ts"].tolist())
    todo = [t for t in wl if t not in done]
    print(f"windows total={len(wl)} done={len(done)} todo={len(todo)} full_from={FULL_FROM}", flush=True)
    for ci in range(0, len(todo), CHUNK):
        chunk = todo[ci:ci + CHUNK]
        t0 = time.time()
        with ThreadPoolExecutor(THREADS) as ex:
            res = list(ex.map(fetch_window, chunk))
        metas = pd.DataFrame([r for r, _ in res])
        tr = [x for _, lst in res for x in lst]
        trd = pd.DataFrame(tr, columns=["ts", "t", "buy", "up", "price", "size"])
        trd = trd.astype({"ts": "int64", "t": "int64", "buy": "int8", "up": "int8", "price": "float32", "size": "float32"})
        tag = f"{chunk[0]}_{chunk[-1]}"
        metas.to_parquet(OUT / f"meta_{tag}.parquet", index=False)
        trd.to_parquet(OUT / f"trades_{tag}.parquet", index=False)
        print(f"chunk {ci//CHUNK} {tag} n={len(chunk)} trades={len(trd)} {time.time()-t0:.0f}s", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
