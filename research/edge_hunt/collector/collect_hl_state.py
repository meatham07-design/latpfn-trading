#!/usr/bin/env python3
"""Forward collector for Hyperliquid market state (public endpoints only).

Every INTERVAL seconds:
  - metaAndAssetCtxs: mark, oracle, mid, funding, OI, premium, 24h vol for every perp
  - l2Book (top 5 levels) for the TOP_N coins by 24h volume
Appends one parquet per UTC day per stream under data/. Purpose: build a history for
oracle-vs-mark premium ticks, OI-change / liquidation proxies, and book-imbalance tests.
No keys, no orders.
"""
import json, time, logging, datetime as dt, pathlib, requests, pandas as pd

API = "https://api.hyperliquid.xyz/info"
OUT = pathlib.Path(__file__).parent / "data"
INTERVAL = 300
TOP_N = 30
LEVELS = 5
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.FileHandler(pathlib.Path(__file__).parent / "collector.log"), logging.StreamHandler()])
S = requests.Session()

def post(body):
    r = S.post(API, json=body, timeout=20); r.raise_for_status(); return r.json()

def append(name, rows, ts):
    if not rows: return
    df = pd.DataFrame(rows); df["ts"] = ts
    f = OUT / f"{name}_{ts.strftime('%Y%m%d')}.parquet"
    if f.exists(): df = pd.concat([pd.read_parquet(f), df], ignore_index=True)
    df.to_parquet(f, index=False)

def cycle():
    ts = dt.datetime.now(dt.UTC).replace(microsecond=0)
    meta, ctxs = post({"type": "metaAndAssetCtxs"})
    rows = []
    for m, c in zip(meta["universe"], ctxs):
        rows.append({"coin": m["name"], "szDecimals": m.get("szDecimals"), "maxLev": m.get("maxLeverage"),
                     "mark": float(c.get("markPx") or 0), "oracle": float(c.get("oraclePx") or 0),
                     "mid": float(c.get("midPx") or 0), "funding": float(c.get("funding") or 0),
                     "oi": float(c.get("openInterest") or 0), "premium": float(c.get("premium") or 0),
                     "dayVlm": float(c.get("dayNtlVlm") or 0), "prevDayPx": float(c.get("prevDayPx") or 0)})
    append("assetctx", rows, ts)
    top = sorted(rows, key=lambda r: -r["dayVlm"])[:TOP_N]
    brows = []
    for r in top:
        try:
            b = post({"type": "l2Book", "coin": r["coin"], "nSigFigs": 5})
            bids, asks = b["levels"][0][:LEVELS], b["levels"][1][:LEVELS]
            brows.append({"coin": r["coin"],
                          **{f"b{i}_px": float(l["px"]) for i, l in enumerate(bids)}, **{f"b{i}_sz": float(l["sz"]) for i, l in enumerate(bids)},
                          **{f"a{i}_px": float(l["px"]) for i, l in enumerate(asks)}, **{f"a{i}_sz": float(l["sz"]) for i, l in enumerate(asks)}})
            time.sleep(0.15)
        except Exception as e:
            logging.warning("l2 %s: %s", r["coin"], e)
    append("l2top", brows, ts)
    logging.info("cycle ok: %d ctx rows, %d books", len(rows), len(brows))

if __name__ == "__main__":
    while True:
        t0 = time.time()
        try: cycle()
        except Exception as e: logging.error("cycle failed: %s", e)
        time.sleep(max(5, INTERVAL - (time.time() - t0)))
