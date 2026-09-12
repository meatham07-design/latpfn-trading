"""For each data/poly/markets_<YYYY-MM>.parquet: draw a seeded random sample of
up to N_PER_MONTH non-sub-daily markets, pull every print from
data-api /trades (public, read-only) into trades_<YYYY-MM>.parquet, and the
event tags (Gamma /events?id=..) into tags_<YYYY-MM>.parquet. Resumable per
month; waits for the listing crawler (fetch_poly_markets.py) to finish.
"""
from __future__ import annotations
import time, datetime as dt, re, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, pandas as pd, numpy as np

ROOT = Path(__file__).resolve().parent
D = ROOT / "data" / "poly"
T = "https://data-api.polymarket.com/trades"
E = "https://gamma-api.polymarket.com/events"
N_PER_MONTH = 800
THREADS = 6
SUBDAILY = re.compile(r"updown-|-up-or-down-\d+m|hourly|-1h-")
S = requests.Session()

def get(url, params, tries=6):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            time.sleep(1.5 * (k + 1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None

def fetch_trades(cid):
    out, off = [], 0
    while True:
        js = get(T, dict(market=cid, limit=10000, offset=off))
        if js is None:
            return cid, None
        for t in js:
            out.append((cid, int(t["timestamp"]), int(t["outcomeIndex"]), 1 if t["side"] == "BUY" else 0,
                        float(t["price"]), float(t["size"])))
        if len(js) < 10000:
            break
        off += 10000
        time.sleep(0.2)
    time.sleep(0.15)
    return cid, out

def fetch_tags(event_ids):
    rows = []
    ids = [str(i) for i in event_ids if i is not None]
    for i in range(0, len(ids), 20):
        js = get(E, [("id", x) for x in ids[i:i + 20]])
        if js:
            for e in js:
                rows.append(dict(event_id=str(e["id"]), tags="|".join(t.get("slug", "") for t in e.get("tags", []) or []),
                                 n_markets_in_event=len(e.get("markets") or []), neg_risk=bool(e.get("negRisk") or e.get("enableNegRisk"))))
        time.sleep(0.25)
    return pd.DataFrame(rows)

def process(mtag):
    mk = pd.read_parquet(D / f"markets_{mtag}.parquet")
    if len(mk) == 0:
        pd.DataFrame(columns=["cid", "t", "oi", "buy", "price", "size"]).to_parquet(D / f"trades_{mtag}.parquet", index=False)
        pd.DataFrame(columns=["event_id", "tags", "n_markets_in_event", "neg_risk"]).to_parquet(D / f"tags_{mtag}.parquet", index=False)
        return
    mk = mk[~mk["slug"].fillna("").str.contains(SUBDAILY)]
    rng = np.random.default_rng(int(mtag.replace("-", "")))
    samp = mk if len(mk) <= N_PER_MONTH else mk.iloc[np.sort(rng.choice(len(mk), N_PER_MONTH, replace=False))]
    t0 = time.time()
    with ThreadPoolExecutor(THREADS) as ex:
        res = list(ex.map(fetch_trades, samp["conditionId"].tolist()))
    rows = [x for _, lst in res if lst for x in lst]
    failed = [c for c, lst in res if lst is None]
    df = pd.DataFrame(rows, columns=["cid", "t", "oi", "buy", "price", "size"])
    df = df.astype({"t": "int64", "oi": "int8", "buy": "int8", "price": "float32", "size": "float32"})
    df.to_parquet(D / f"trades_{mtag}.parquet", index=False)
    samp[["id", "conditionId"]].assign(fetched=~samp["conditionId"].isin(failed)).to_parquet(D / f"sample_{mtag}.parquet", index=False)
    tg = fetch_tags(samp["event_id"].dropna().unique().tolist())
    tg.to_parquet(D / f"tags_{mtag}.parquet", index=False)
    print(f"{mtag}: listed={len(mk)} sampled={len(samp)} trades={len(df)} failed={len(failed)} tags={len(tg)} {time.time()-t0:.0f}s", flush=True)

def main():
    while True:
        months = sorted(p.name[len("markets_"):-len(".parquet")] for p in D.glob("markets_*.parquet"))
        todo = [m for m in months if not (D / f"trades_{m}.parquet").exists()]
        log = (D / "_markets_fetch.log").read_text() if (D / "_markets_fetch.log").exists() else ""
        if not todo:
            if "DONE" in log:
                print("DONE", flush=True); return
            time.sleep(30); continue
        process(todo[0])

if __name__ == "__main__":
    main()
