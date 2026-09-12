"""LEAKAGE lens on hl_listing_drift (Binance UM pick: short_after N=24 H=7 hedged).

Asks: is the +$18k OOS an artefact of how the event set / timestamps / universe
were built, rather than a real post-listing effect?

L1 listing-timestamp integrity   (1h archive vs funding archive vs S3 month list)
L2 hour-of-day + volume profile  (does t0 look like a real listing?)
L3 survivorship                  (delisted-since vs still-listed split)
L4 base-asset duplicates         (1000PEPE / PEPE re-listings double counted?)
L5 hedge-price drops             (events silently dropped by missing BTC bars)
L6 causality assertions          (entry == t0+24h open, exit == entry+H, no gaps)
L7 archive-edge exclusions       (the 11 dropped 2020-01 symbols)
"""
from __future__ import annotations
import os, json, re, sys, time, collections
os.environ["NOLAB"] = "1"
from pathlib import Path
import numpy as np, pandas as pd, requests
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import h_hl_listing_drift as T
import common as C

OUT = HERE / "verify_hl_listing_drift_leakage.json"
MD  = HERE / "verify_hl_listing_drift_leakage.md"
L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); L.append(s)

BEST = dict(rule="short_after", N=24, H=7, hedge=True)
res = {}

evs, btc, drop, earliest = T.load_binance_events()
idx = {}
for name in ("_index.json", "_index_rev.json"):
    p = T.BUM / name
    if p.exists(): idx.update(json.loads(p.read_text()))
P(f"# LEAKAGE — hl_listing_drift (Binance UM), pick `{BEST}`\n")
P(f"events={len(evs)}  dropped={ {k: len(v) for k, v in drop.items()} }  earliest archive month={earliest}\n")

bounds = C.fold_bounds((min(e.t0 for e in evs), max(e.t0 for e in evs)), 3)
def oos_trades(events):
    rows = []
    for ev in events:
        if ev.t0 < bounds[1][0]: continue
        t = T.rule_trade(ev, BEST, btc, True)
        if t: rows.append(t)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)

base_oos = oos_trades(evs)
base = C.evaluate(base_oos, 1)
P(f"baseline OOS (folds 2+3, all events): n={base['n']} net={base['net']:.1f} pf={base['pf']:.2f}\n")
res["baseline"] = base

# ---------------------------------------------------------------- L1
P("## L1 — listing-timestamp integrity\n")
gaps, nofund = [], 0
for ev in evs:
    fp = T.BUM / f"{ev.sym}_funding.parquet"
    if not fp.exists() or not len(ev.fund): nofund += 1; continue
    gaps.append((ev.fund.index[0] - ev.t0).total_seconds() / 3600.0)
gaps = np.array(gaps)
P(f"- funding archive present for {len(gaps)}/{len(evs)} symbols ({nofund} without).")
P(f"- hours between first 1h bar and first funding stamp: median {np.median(gaps):.1f}h, "
  f"p05 {np.percentile(gaps,5):.1f}h, p95 {np.percentile(gaps,95):.1f}h, "
  f"share in [-1, 9]h {np.mean((gaps>=-1)&(gaps<=9)):.3f}, share negative {np.mean(gaps<0):.3f}")
P("  (a real listing funds within one 8h interval; a large positive gap means the kline archive starts before funding, "
  "a negative gap means funding predates the first kline -> t0 is NOT the listing.)")
res["L1"] = dict(n=int(len(gaps)), median_h=float(np.median(gaps)), share_within_9h=float(np.mean((gaps>=-1)&(gaps<=9))),
                 share_negative=float(np.mean(gaps < 0)))
# Binance writes a PLACEHOLDER funding stamp (exactly 0.0001, or 0.0) from contract
# creation / the start of the archive month, before the perp actually trades.  Only a
# NON-placeholder rate before the first kline would mean the perp traded before t0.
PLACEHOLDER = {0.0001, 0.0, -0.0001}
early = [ev.sym for ev in evs if len(ev.fund) and (ev.fund.index[0] - ev.t0).total_seconds()/3600.0 < -1]
bad_t0 = []
for ev in evs:
    if not len(ev.fund): continue
    pre = ev.fund[ev.fund.index < ev.t0 - pd.Timedelta(hours=1)]
    if len(pre) and not set(np.round(pre.values, 6)).issubset(PLACEHOLDER):
        bad_t0.append(ev.sym)
P(f"- symbols with ANY funding stamp before the first kline: {len(early)} (mostly placeholder 0.0001/0.0 rows)")
P(f"- symbols with a NON-placeholder funding rate before the first kline (real pre-t0 trading): {len(bad_t0)} {bad_t0[:12]}")
res["L1"]["early_funding_stamp"] = len(early)
res["L1"]["suspect_t0"] = bad_t0
for lbl, drop_set in (("ex any-early-funding", set(early)), ("ex non-placeholder-early", set(bad_t0))):
    if not drop_set: continue
    keep = [e for e in evs if e.sym not in drop_set]
    r = C.evaluate(oos_trades(keep), 1)
    P(f"- OOS {lbl}: n={r['n']} net={r['net']:.1f} pf={r['pf']:.2f} avg={r['net']/max(1,r['n']):.1f}")
    res["L1"][lbl] = r
kept = [e for e in evs if e.sym in set(early)]
if kept:
    r = C.evaluate(oos_trades(kept), 1)
    P(f"- OOS on the early-funding subset ALONE: n={r['n']} net={r['net']:.1f} pf={r['pf']:.2f} avg={r['net']/max(1,r['n']):.1f}")
    res["L1"]["early_only"] = r

# S3 spot-check: is there an EARLIER monthly file than index first_month?
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
sess = requests.Session(); sess.headers["User-Agent"] = "edge-hunt-verify/1.0 (read-only)"
rng = np.random.default_rng(11)
pool = sorted(set(early)) if early else [e.sym for e in evs]
sample = list(rng.choice(pool, size=min(40, len(pool)), replace=False))
P(f"- S3 spot-check pool = the {len(pool)} symbols with an early funding stamp (the hardest cases for t0 integrity)")
ok = bad = err = 0; mism = []
for sym in sample:
    try:
        r = sess.get(S3, params={"delimiter": "/", "prefix": f"data/futures/um/monthly/klines/{sym}/1h/", "max-keys": 1000}, timeout=30)
        months = sorted(set(re.findall(rf"{sym}-1h-(\d{{4}}-\d{{2}})\.zip", r.text)))
    except Exception:
        err += 1; continue
    if not months: err += 1; continue
    if months[0] == idx[sym]["first_month"]: ok += 1
    else: bad += 1; mism.append((sym, months[0], idx[sym]["first_month"]))
    time.sleep(0.15)
P(f"- S3 re-listing spot-check on {len(sample)} random symbols: first monthly file matches the cached first_month for {ok}, "
  f"mismatch {bad} {mism[:5]}, network errors {err}")
res["L1"]["s3_spotcheck"] = dict(n=len(sample), ok=ok, mismatch=bad, errors=err, examples=mism[:5])

# ---------------------------------------------------------------- L2
P("\n## L2 — does t0 look like a real listing?\n")
hod = collections.Counter(ev.t0.hour for ev in evs)
top = ", ".join(f"{h:02d}h:{n}" for h, n in hod.most_common(6))
P(f"- entry-hour(UTC) concentration of t0: top hours {top}; distinct hours {len(hod)}; "
  f"share in the top-3 hours {sum(n for _, n in hod.most_common(3))/len(evs):.2f} (uniform would be 0.125)")
first_is_max = np.mean([float(ev.bars['quote_volume'].iloc[0]) == float(ev.bars['quote_volume'].iloc[:48].max()) for ev in evs])
day1_share = np.mean([float(ev.bars['quote_volume'].iloc[:24].sum()) / max(1e-9, float(ev.bars['quote_volume'].iloc[:168].sum())) for ev in evs if len(ev.bars) >= 168])
P(f"- bar 0 is the highest-volume hour of the first 48h for {first_is_max:.2f} of events; "
  f"day-1 volume is {day1_share:.2f} of the first week's volume (a listing spike, not a mid-life month start)")
res["L2"] = dict(hour_top3_share=float(sum(n for _, n in hod.most_common(3))/len(evs)),
                 bar0_is_max_share=float(first_is_max), day1_vol_share=float(day1_share))

# ---------------------------------------------------------------- L3
P("\n## L3 — survivorship\n")
last_month = {s: v.get("last_month") for s, v in idx.items()}
ARCHIVE_END = max(v for v in last_month.values() if v)
dead = {s for s, m in last_month.items() if m and m < ARCHIVE_END}
t = C.add_pnl(base_oos)
t["dead"] = t.instrument.map(lambda s: s in dead)
P(f"- archive ends {ARCHIVE_END}; {len(dead)}/{len(idx)} symbols stop earlier (delisted since).")
for flag, lbl in ((True, "delisted since"), (False, "still listed")):
    sub = t[t.dead == flag]
    r = C.evaluate(sub, 1) if len(sub) else C.empty_result(1)
    P(f"- {lbl:15s}: n={r['n']:4d} net={r['net']:9.1f} pf={r['pf']:.2f} avg={r['net']/max(1,r['n']):.1f}")
    res.setdefault("L3", {})[lbl] = r
P("  (the sample INCLUDES delisted symbols, so it is point-in-time; if the edge lived only in the delisted half it would "
  "still be tradable but only ex-post identifiable.)")

# ---------------------------------------------------------------- L4
P("\n## L4 — duplicate base assets (re-listings under a new ticker)\n")
byb = collections.defaultdict(list)
for ev in evs: byb[T.base_asset(ev.sym, "binance")].append(ev)
dups = {b: [e.sym for e in v] for b, v in byb.items() if len(v) > 1}
P(f"- {len(dups)} base assets appear more than once: {list(dups.items())[:8]}")
keep_first = [sorted(v, key=lambda e: e.t0)[0] for v in byb.values()]
r = C.evaluate(oos_trades(keep_first), 1)
P(f"- OOS keeping only the FIRST listing per base asset: n={r['n']} net={r['net']:.1f} pf={r['pf']:.2f} "
  f"(baseline n={base['n']} net={base['net']:.1f})")
res["L4"] = dict(n_dup_bases=len(dups), dedup=r, examples={k: v for k, v in list(dups.items())[:8]})

# ---------------------------------------------------------------- L5
P("\n## L5 — events silently dropped\n")
drops = collections.Counter()
for ev in evs:
    if ev.t0 < bounds[1][0]: continue
    k = ev.bars
    ie, ix = 24, 24 + 24 * 7
    if ix >= len(k): drops["too_short"] += 1; continue
    if (k.index[ix] - k.index[ie]) != pd.Timedelta(hours=1) * (ix - ie): drops["bar_gap"] += 1; continue
    if not np.isfinite(T._px_at(btc, k.index[ie])) or not np.isfinite(T._px_at(btc, k.index[ix])): drops["btc_missing"] += 1; continue
    drops["traded"] += 1
P(f"- OOS-window events: {dict(drops)}")
res["L5"] = dict(drops)
if drops["btc_missing"] or drops["bar_gap"]:
    keepu = []
    for ev in evs:
        if ev.t0 < bounds[1][0]: continue
        t2 = T.make_trade(ev, -1, 24, 24 + 168, False, btc, pd.Timedelta(hours=1))
        if t2: keepu.append(t2)
    r = C.evaluate(pd.DataFrame(keepu), 1)
    P(f"- unhedged variant (no BTC lookup, so no BTC-driven drops): n={r['n']} net={r['net']:.1f} pf={r['pf']:.2f}")
    res["L5"]["unhedged_all"] = r

# ---------------------------------------------------------------- L6
P("\n## L6 — causality assertions on every OOS trade\n")
bad = collections.Counter()
for ev in evs:
    if ev.t0 < bounds[1][0]: continue
    tr = T.rule_trade(ev, BEST, btc, True)
    if not tr: continue
    k = ev.bars
    if tr["entry_time"] != ev.t0 + pd.Timedelta(hours=24): bad["entry_not_t0_plus_24h"] += 1
    if tr["exit_time"] - tr["entry_time"] != pd.Timedelta(days=7): bad["hold_not_7d"] += 1
    if tr["entry_px"] != float(k.loc[tr["entry_time"], "open"]): bad["entry_px_not_open"] += 1
    if tr["exit_px_raw"] != float(k.loc[tr["exit_time"], "open"]): bad["exit_px_not_open"] += 1
    if tr["side"] != -1: bad["side"] += 1
P(f"- violations: {dict(bad) if bad else 'NONE — every entry is the open 24h after the first traded bar, every exit the open 7d later'}")
res["L6"] = dict(bad)

# ---------------------------------------------------------------- L7
P("\n## L7 — archive-edge exclusions\n")
P(f"- excluded as unverifiable (first archive month == {earliest}): {drop['archive_start']}")
P("  these are the 11 original 2020-01 perps; they have no observable listing bar, so they cannot be tested either way.")
res["L7"] = dict(excluded=drop["archive_start"])

OUT.write_text(json.dumps(res, indent=1, default=str))
MD.write_text("\n".join(L) + "\n")
print(f"\nwrote {OUT.name} / {MD.name}")
