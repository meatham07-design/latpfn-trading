"""Hyperliquid listing windows: for every coin in meta (incl. delisted), the
listing day = first daily candle with volume>0 (pre-listing candles are
oracle-only, volume 0).  Fetch hourly funding for [listing, listing+21d]
(fundingHistory serves full history; candleSnapshot does not).
Cache: data/hl_listings/funding_<coin>.parquet + _listings.json."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import pandas as pd, requests
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import common as C
OUT = ROOT / "data" / "hl_listings"; OUT.mkdir(exist_ok=True)
PIT = C.DATA / "xsec_pit"
S = requests.Session()

def post(body, tries=6):
    for k in range(tries):
        try:
            r = S.post(C.HL_INFO_URL, json=body, timeout=60)
            if r.status_code == 429: time.sleep(3 + 3 * k); continue
            r.raise_for_status(); return r.json()
        except Exception:
            if k == tries - 1: raise
            time.sleep(2.0 * (k + 1))

meta = post({"type": "meta"})
rows = {}
for u in meta["universe"]:
    coin = u["name"]
    p = PIT / f"hl_{coin}_1d.parquet"
    if not p.exists():
        rows[coin] = {"error": "no daily file"}; continue
    d = pd.read_parquet(p)
    live = d[d["volume"] > 0]
    if len(live) == 0:
        rows[coin] = {"error": "never traded"}; continue
    t0 = live.index[0]
    rows[coin] = {"listing_day": str(t0.date()), "delisted": bool(u.get("isDelisted", False)),
                  "onlyIsolated": bool(u.get("onlyIsolated", False)), "maxLeverage": u.get("maxLeverage"),
                  "n_pre_oracle_days": int((d.index < t0).sum()), "first_series_day": str(d.index[0].date()),
                  "last_day": str(d.index[-1].date())}
    fp = OUT / f"funding_{coin}.parquet"
    if fp.exists(): continue
    st = int(t0.timestamp() * 1000); en = st + 22 * 86400000
    parts, start = [], st
    while True:
        chunk = post({"type": "fundingHistory", "coin": coin, "startTime": start, "endTime": en})
        if not chunk: break
        parts.extend(chunk); last = int(chunk[-1]["time"])
        if len(chunk) < 500 or last >= en: break
        start = last + 1; time.sleep(0.3)
    if parts:
        df = pd.DataFrame(parts); df["time"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
        out = pd.DataFrame({"fundingRate": df["fundingRate"].astype(float).values, "premium": df["premium"].astype(float).values},
                           index=pd.DatetimeIndex(df["time"])); out.index.name = "time"
        out.to_parquet(fp)
    rows[coin]["n_funding"] = len(parts)
    time.sleep(0.35)
(OUT / "_listings.json").write_text(json.dumps(rows, indent=1))
print("done", len(rows))
