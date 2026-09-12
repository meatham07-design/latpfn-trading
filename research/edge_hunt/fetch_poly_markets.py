"""List every CLOSED Polymarket market (Gamma) with endDate in [FROM, TO] and
final volume >= VOL_MIN into data/poly/markets_<YYYY-MM>.parquet.
Day windows via end_date_min/max; a window is split into hours when the
offset cap (~2000) is hit. Resumable per month. Public read-only, polite.
Run: venv/bin/python fetch_poly_markets.py
"""
from __future__ import annotations
import json, time, datetime as dt, sys
from pathlib import Path
import requests, pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "poly"; OUT.mkdir(parents=True, exist_ok=True)
G = "https://gamma-api.polymarket.com/markets"
FROM = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
TO = dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc)
VOL_MIN = 1000
S = requests.Session()
KEEP = ["id", "conditionId", "question", "slug", "endDate", "closedTime", "startDate", "createdAt",
        "outcomes", "outcomePrices", "clobTokenIds", "volumeNum", "liquidityNum", "category",
        "feesEnabled", "feeType", "enableOrderBook", "umaResolutionStatuses", "marketType", "negRiskOther"]

def get(params, tries=6):
    for k in range(tries):
        try:
            r = S.get(G, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 422:
                return "CAP"
            time.sleep(1.5 * (k + 1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None

def window(lo: dt.datetime, hi: dt.datetime):
    """Return (rows, capped) for markets with endDate in [lo, hi]."""
    rows, off = [], 0
    while True:
        js = get(dict(closed="true", limit=100, offset=off, volume_num_min=VOL_MIN,
                      end_date_min=lo.strftime("%Y-%m-%dT%H:%M:%SZ"), end_date_max=hi.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      order="id", ascending="true"))
        if js == "CAP":
            return rows, True
        if js is None:
            print("  fetch failed", lo, off, flush=True); return rows, False
        for m in js:
            row = {k: m.get(k) for k in KEEP}
            ev = (m.get("events") or [{}])[0]
            row["event_id"] = ev.get("id"); row["event_slug"] = ev.get("slug"); row["event_title"] = ev.get("title")
            row["event_negrisk"] = ev.get("negRisk") or ev.get("enableNegRisk"); row["series_slug"] = ev.get("seriesSlug")
            row["n_markets_in_event"] = None
            rows.append(row)
        off += 100
        time.sleep(0.25)
        if len(js) < 100:
            return rows, False

def day(d: dt.datetime):
    lo = d; hi = d + dt.timedelta(days=1) - dt.timedelta(seconds=1)
    rows, capped = window(lo, hi)
    if not capped:
        return rows
    rows = []
    for h in range(24):
        lo = d + dt.timedelta(hours=h); hi = lo + dt.timedelta(hours=1) - dt.timedelta(seconds=1)
        r, capped = window(lo, hi)
        if capped:  # split into 10-minute windows
            r = []
            for mnt in range(0, 60, 10):
                lo2 = lo + dt.timedelta(minutes=mnt); hi2 = lo2 + dt.timedelta(minutes=10) - dt.timedelta(seconds=1)
                r2, c2 = window(lo2, hi2)
                if c2: print("  STILL CAPPED", lo2, flush=True)
                r += r2
        rows += r
    return rows

def main():
    d = FROM
    while d <= TO:
        mtag = d.strftime("%Y-%m")
        fp = OUT / f"markets_{mtag}.parquet"
        if fp.exists():
            d = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1); continue
        m_end = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        rows = []; t0 = time.time()
        dd = d
        while dd < m_end and dd <= TO:
            r = day(dd); rows += r
            dd += dt.timedelta(days=1)
        df = pd.DataFrame(rows)
        if len(df):
            df = df.drop_duplicates("id")
        df.to_parquet(fp, index=False)
        print(f"{mtag}: {len(df)} markets {time.time()-t0:.0f}s", flush=True)
        d = m_end
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
