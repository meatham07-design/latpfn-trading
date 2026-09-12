"""Fetch Polymarket 'above X' strike-ladder families (Gamma metadata + data-api prints
+ CLOB prices-history) into data/polymarket_consistency/. Public read-only. Resumable.
Series: 45 btc-multi-strikes-weekly (daily noon-ET ladders), 42 eth-multi-strikes-weekly,
11372 bitcoin-multi-strikes-hourly (+ eth hourly if found). Run: venv/bin/python fetch_polymarket_ladders.py
"""
from __future__ import annotations
import json, sys, time, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "polymarket_consistency"; OUT.mkdir(parents=True, exist_ok=True)
(OUT / "prints").mkdir(exist_ok=True); (OUT / "hist").mkdir(exist_ok=True)
GAMMA = "https://gamma-api.polymarket.com/events"
TRADES = "https://data-api.polymarket.com/trades"
HIST = "https://clob.polymarket.com/prices-history"
S = requests.Session()
LOG = open(OUT / "_fetch.log", "a")
def log(*a):
    print(*a, flush=True); print(*a, file=LOG, flush=True)
def get(url, params, tries=6):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200: return r.json()
            if r.status_code in (429, 500, 502, 503, 504): time.sleep(1.5 * (k + 1)); continue
            return None
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None
def strike_of(m):
    g = (m.get("groupItemTitle") or "").replace(",", "").replace("$", "").strip()
    try: return float(g)
    except Exception:
        q = m.get("question", ""); mm = re.search(r"\$([\d,\.]+)", q)
        return float(mm.group(1).replace(",", "")) if mm else np.nan
def enumerate_series(sid, prefix):
    rows = []
    for closed in (True, False):
        off = 0
        while True:
            r = get(GAMMA, dict(series_id=sid, limit=100, offset=off, closed=closed))
            if not r: break
            for e in r:
                if not e["slug"].startswith(prefix): continue
                for m in e.get("markets", []):
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                    op = json.loads(m.get("outcomePrices") or "[]")
                    rows.append(dict(series=sid, event_id=e["id"], slug=e["slug"], ev_start=e.get("startDate"), ev_end=e.get("endDate"),
                                     ev_closed=bool(e.get("closed")), closed_time=e.get("closedTime"), mid=m["id"], cid=m["conditionId"],
                                     question=m.get("question"), strike=strike_of(m), tok_yes=toks[0] if toks else None,
                                     tok_no=toks[1] if len(toks) > 1 else None, yes_final=float(op[0]) if op else np.nan,
                                     m_start=m.get("startDate"), m_end=m.get("endDate"), m_closed_time=m.get("closedTime"),
                                     uma=m.get("umaResolutionStatus"), volume=float(m.get("volumeNum") or 0),
                                     fee_rate=float((m.get("feeSchedule") or {}).get("rate", np.nan)),
                                     tick=float(m.get("orderPriceMinTickSize") or np.nan), min_size=float(m.get("orderMinSize") or np.nan),
                                     created=m.get("createdAt")))
            off += 100; time.sleep(0.4)
    return rows
def fetch_prints(cid):
    out, off = [], 0
    while True:
        tr = get(TRADES, dict(market=cid, limit=5000, offset=off))
        if tr is None: return None
        for t in tr:
            out.append((int(t["timestamp"]), 1 if t["side"] == "BUY" else 0, int(t.get("outcomeIndex", 0)), float(t["price"]), float(t["size"])))
        if len(tr) < 5000: break
        off += 5000; time.sleep(0.3)
    return out
def fetch_hist(tok):
    r = get(HIST, dict(market=tok, interval="max", fidelity=1))
    if r is None: return None
    return [(int(h["t"]), float(h["p"])) for h in r.get("history", [])]
def do_event(grp):
    slug = grp.iloc[0]["slug"]
    pp = OUT / "prints" / f"{slug}.parquet"; hp = OUT / "hist" / f"{slug}.parquet"
    if pp.exists() and hp.exists(): return slug, "cached"
    P, H, bad = [], [], 0
    for _, m in grp.iterrows():
        if not pp.exists():
            tr = fetch_prints(m["cid"])
            if tr is None: bad += 1
            else: P += [(m["mid"], m["strike"]) + x for x in tr]
        if not hp.exists():
            h = fetch_hist(m["tok_yes"])
            if h is None: bad += 1
            else: H += [(m["mid"], m["strike"]) + x for x in h]
        time.sleep(0.15)
    if bad: return slug, f"bad={bad}"
    if not pp.exists():
        pd.DataFrame(P, columns=["mid", "strike", "t", "buy", "outcome", "price", "size"]).to_parquet(pp, index=False)
    if not hp.exists():
        pd.DataFrame(H, columns=["mid", "strike", "t", "p"]).to_parquet(hp, index=False)
    return slug, f"ok prints={len(P)} hist={len(H)}"
def main():
    series = [(45, "bitcoin-above-on"), (42, "ethereum-above-on"), (11372, "bitcoin-above-on")]
    e = get(GAMMA, dict(slug="ethereum-above-on-august-28-2026-2am-et"))
    if e:
        for s in e[0].get("series", []):
            if "hourly" in s["slug"]: series.append((int(s["id"]), "ethereum-above-on")); log("eth hourly series", s["id"], s["slug"])
    mp = OUT / "markets.parquet"
    if mp.exists():
        meta = pd.read_parquet(mp)
    else:
        rows = []
        for sid, pre in series:
            r = enumerate_series(sid, pre); log("series", sid, pre, "markets", len(r)); rows += r
        meta = pd.DataFrame(rows).drop_duplicates("mid"); meta.to_parquet(mp, index=False)
    log("markets", len(meta), "events", meta.slug.nunique())
    # daily series first (resolved before active), then hourly
    meta["hourly"] = meta.series.isin([s for s, _ in series if s not in (45, 42)])
    meta = meta.sort_values(["hourly", "ev_closed", "ev_start"], ascending=[True, False, True])
    groups = [g for _, g in meta.groupby("slug", sort=False)]
    groups.sort(key=lambda g: (bool(g.iloc[0]["hourly"]), not bool(g.iloc[0]["ev_closed"]), str(g.iloc[0]["ev_start"])))
    t0 = time.time(); n = 0
    with ThreadPoolExecutor(6) as ex:
        for slug, st in ex.map(do_event, groups):
            n += 1
            if st != "cached" or n % 50 == 0: log(f"[{n}/{len(groups)} {time.time()-t0:.0f}s] {slug} {st}")
    log("DONE")
if __name__ == "__main__":
    main()
