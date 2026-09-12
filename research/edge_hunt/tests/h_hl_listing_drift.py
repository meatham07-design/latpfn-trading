"""hl_listing_drift -- new-listing drift on perps (Hyperliquid + Binance UM).

Samples (point-in-time, delisted included):
  * Binance USDT-M perps, every listing in the public archive 2019-2026,
    first 2 months of 1h klines + funding (data/binance_um_listings/).
    Hourly rules: (a) short after first N h for H d, (b) first-hour momentum,
    (c) fade the day-1 top wick.  Fees 5 bps/side taker, funding included.
  * Hyperliquid, every coin in meta (232 incl. delisted).  Listing day = first
    daily candle with volume>0 (pre-listing candles are oracle-only).  Only
    daily candles survive on HL for old listings (candleSnapshot keeps the last
    5000 bars), so HL rules are the daily analogues.  Fees 4.5 bps/side,
    hourly funding included.
Causality: signal at close of bar i-1, fill at open of bar i (same timestamp).
Walk-forward: chronological thirds by listing time; select on fold 1 only.
"""
from __future__ import annotations
import json, sys, itertools, re
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import common as C, os
NOLAB = os.environ.get("NOLAB") == "1"
_rec = C.record_to_lab
def _record(*a, **k):
    return None if NOLAB else _rec(*a, **k)
C.record_to_lab = _record

STRAT = "hl_listing_drift"
SRC = "tests/h_hl_listing_drift.py"
NOTIONAL = 1000.0
FEE_SIDE = {"binance": 0.0005, "hl": C.FEES["hl_taker"]}
BUM = C.DATA / "binance_um_listings"
HLL = C.DATA / "hl_listings"
PIT = C.DATA / "xsec_pit"
OUT_MD = ROOT / "tests" / "h_hl_listing_drift.md"
OUT_JSON = ROOT / "tests" / "h_hl_listing_drift.json"
rng = np.random.default_rng(7)
LINES = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------
def base_asset(sym, sample):
    if sample == "binance":
        b = sym[:-4]
        return re.sub(r"^1(000)+", "", b)
    return re.sub(r"^k(?=[A-Z])", "", sym)


def earliest_first_trade():
    """base asset -> earliest first-trade timestamp across Binance spot daily
    panel (2018+), Binance UM archive and Hyperliquid.  Used to flag a listing
    as 'fresh' (exchange listing within 3 days of the token's first trade
    anywhere in our sources) vs 'established' (coin already traded elsewhere)."""
    first = {}
    def upd(b, t):
        if b and (b not in first or t < first[b]): first[b] = t
    panel = pd.read_parquet(C.DATA / "binance_panel_1d.parquet", columns=["symbol", "time"])
    meta = json.loads((C.DATA / "binance_symbols.json").read_text())
    for sym, t in panel.groupby("symbol")["time"].min().items():
        upd(re.sub(r"^1(000)+", "", meta.get(sym, {}).get("base", sym[:-4])), pd.Timestamp(t).tz_convert("UTC"))
    for name in ("_index.json", "_index_rev.json"):
        pth = BUM / name
        if pth.exists():
            for sym, info in json.loads(pth.read_text()).items():
                if info.get("first_1h"): upd(base_asset(sym, "binance"), pd.Timestamp(info["first_1h"]))
    for pth in PIT.glob("hl_*_1d.parquet"):
        d = pd.read_parquet(pth, columns=["volume"]); live = d[d["volume"] > 0]
        if len(live): upd(base_asset(pth.name[3:-11], "hl"), live.index[0])
    return first


class Ev:
    __slots__ = ("sym", "t0", "bars", "fund", "sample", "flags", "day1_qv")
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)


def load_binance_events():
    idx = {}
    for name in ("_index.json", "_index_rev.json"):
        p = BUM / name
        if p.exists(): idx.update(json.loads(p.read_text()))
    btc = pd.read_parquet(C.DATA / "ext_binance_BTCUSDT_1h.parquet")
    months = [v["first_month"] for v in idx.values() if v.get("first_month")]
    earliest = min(months)
    evs, dropped = [], {"archive_start": [], "month_boundary": [], "no_data": [], "gap_first_48h": []}
    for sym, info in sorted(idx.items()):
        if not info.get("first_month") or not (BUM / f"{sym}_1h.parquet").exists():
            dropped["no_data"].append(sym); continue
        k = pd.read_parquet(BUM / f"{sym}_1h.parquet")
        t0 = k.index[0]
        if info["first_month"] == earliest:
            dropped["archive_start"].append(sym); continue
        if t0 == pd.Timestamp(info["first_month"] + "-01", tz="UTC"):
            dropped["month_boundary"].append(sym); continue
        if len(k) < 48 or (k.index[47] - t0) != pd.Timedelta(hours=47):
            dropped["gap_first_48h"].append(sym); continue
        fp = BUM / f"{sym}_funding.parquet"
        f = pd.read_parquet(fp)["fundingRate"] if fp.exists() else pd.Series(dtype=float)
        evs.append(Ev(sym=sym, t0=t0, bars=k, fund=f, sample="binance", flags={},
                      day1_qv=float(k["quote_volume"].iloc[:24].sum())))
    return evs, btc, dropped, earliest


def load_hl_events():
    """Listing day = first daily candle with volume>0 (PIT daily panel covers all
    232 meta coins incl. delisted).  Funding from data/hl_listings/ if fetched."""
    delisted = set(json.loads((PIT / "_delisted.json").read_text()))
    btc = pd.read_parquet(PIT / "hl_BTC_1d.parquet")
    evs, dropped = [], {"never_traded": [], "short": []}
    for p in sorted(PIT.glob("hl_*_1d.parquet")):
        coin = p.name[3:-11]
        d = pd.read_parquet(p)
        live = d[d["volume"] > 0]
        if len(live) == 0:
            dropped["never_traded"].append(coin); continue
        d = d[d.index >= live.index[0]]
        if len(d) < 3:
            dropped["short"].append(coin); continue
        fp = HLL / f"funding_{coin}.parquet"
        f = pd.read_parquet(fp)["fundingRate"] if fp.exists() else pd.Series(dtype=float)
        evs.append(Ev(sym=coin, t0=d.index[0], bars=d, fund=f, sample="hl",
                      flags={"delisted": coin in delisted, "has_funding": fp.exists()},
                      day1_qv=float((d["volume"] * d["close"]).iloc[0])))
    return evs, btc, dropped


# ---------------------------------------------------------------------------
# trade construction
# ---------------------------------------------------------------------------
def _px_at(btc, t, col="open"):
    i = btc.index.get_indexer([t])[0]
    return float(btc[col].iloc[i]) if i >= 0 else np.nan


def make_trade(ev, side, i_entry, i_exit, hedge, btc, step):
    """step = bar length (Timedelta). Returns trade dict (synthetic exit_px so
    that evaluate() sees gross = alt leg + funding + hedge leg) or None."""
    k = ev.bars
    if i_exit >= len(k) or i_entry >= len(k) or i_entry < 1: return None
    te, tx = k.index[i_entry], k.index[i_exit]
    if (tx - te) != step * (i_exit - i_entry): return None       # gap -> skip
    pe, px = float(k["open"].iloc[i_entry]), float(k["open"].iloc[i_exit])
    if not (pe > 0 and px > 0): return None
    qty = NOTIONAL / pe
    gross = side * (px - pe) * qty
    fr = ev.fund
    fsum = float(fr[(fr.index > te) & (fr.index <= tx)].sum()) if len(fr) else 0.0
    funding = -side * fsum * NOTIONAL                    # long pays positive funding
    fee = FEE_SIDE[ev.sample] * (NOTIONAL + qty * px)
    hpnl = 0.0
    if hedge:
        be, bx = _px_at(btc, te), _px_at(btc, tx)
        if not (np.isfinite(be) and np.isfinite(bx)): return None
        hpnl = -side * (bx - be) * (NOTIONAL / be)
        fee += FEE_SIDE[ev.sample] * (NOTIONAL + NOTIONAL * bx / be)
    total = gross + funding + hpnl
    return dict(entry_time=te, exit_time=tx, side=side, entry_px=pe,
                exit_px=pe + side * total / qty, exit_px_raw=px, qty=qty,
                notional_usd=NOTIONAL, fee_usd=fee, instrument=ev.sym,
                alt_gross=gross, funding=funding, hedge_pnl=hpnl, listing=ev.t0)


def rule_trade(ev, p, btc, hourly=True):
    """Map a param dict to (side, i_entry, i_exit) on the event's bars."""
    k = ev.bars
    step = pd.Timedelta(hours=1) if hourly else pd.Timedelta(days=1)
    per_day = 24 if hourly else 1
    r = p["rule"]
    if r == "short_after":
        n = p["N"] if hourly else 1
        return make_trade(ev, -1, n, n + per_day * p["H"], p["hedge"], btc, step)
    if r == "mom1":
        r0 = float(k["close"].iloc[0] / k["open"].iloc[0] - 1)
        if abs(r0) < p["thr"]: return None
        side = int(np.sign(r0)) * (-1 if p["contra"] else 1)
        return make_trade(ev, side, 1, 1 + p["Hh"], False, btc, step)
    if r == "wick":
        if hourly:
            if len(k) < 25: return None
            hi, c = float(k["high"].iloc[:24].max()), float(k["close"].iloc[23])
            i0 = 24
        else:
            hi, c = float(k["high"].iloc[0]), float(k["close"].iloc[0]); i0 = 1
        dist = hi / c - 1
        if p["mode"] == "near_top_short":
            if dist > p["x"]: return None
            side = -1
        else:
            if dist < p["x"]: return None
            side = +1
        return make_trade(ev, side, i0, i0 + per_day * p["H"], p["hedge"], btc, step)
    raise ValueError(r)


def grid_binance():
    g = []
    for N, H, hedge in itertools.product([4, 24], [1, 3, 7, 14], [False, True]):
        g.append(dict(rule="short_after", N=N, H=H, hedge=hedge))
    for thr, Hh, contra in itertools.product([0.0, 0.02, 0.05], [4, 24], [False, True]):
        g.append(dict(rule="mom1", thr=thr, Hh=Hh, contra=contra))
    for mode, x, H in itertools.product(["near_top_short", "deep_wick_long"], [None, None], [1, 3, 7]):
        pass
    for x, H, hedge in itertools.product([0.02, 0.05], [1, 3, 7], [False]):
        g.append(dict(rule="wick", mode="near_top_short", x=x, H=H, hedge=hedge))
    for x, H, hedge in itertools.product([0.20, 0.40], [1, 3, 7], [False]):
        g.append(dict(rule="wick", mode="deep_wick_long", x=x, H=H, hedge=hedge))
    return g


def grid_hl():
    g = []
    for H, hedge in itertools.product([1, 3, 7, 14], [False, True]):
        g.append(dict(rule="short_after", N=1, H=H, hedge=hedge))
    for thr, Hh, contra in itertools.product([0.0, 0.05], [1, 3], [False, True]):
        g.append(dict(rule="mom1", thr=thr, Hh=Hh, contra=contra))
    for x, H in itertools.product([0.05, 0.10], [1, 3, 7]):
        g.append(dict(rule="wick", mode="near_top_short", x=x, H=H, hedge=False))
    for x, H in itertools.product([0.20, 0.40], [1, 3, 7]):
        g.append(dict(rule="wick", mode="deep_wick_long", x=x, H=H, hedge=False))
    return g


def run_all(evs, p, btc, hourly, start=None, end=None):
    rows = []
    for ev in evs:
        if start is not None and not (start <= ev.t0 < end): continue
        t = rule_trade(ev, p, btc, hourly)
        if t: rows.append(t)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)


# ---------------------------------------------------------------------------
# descriptive paths
# ---------------------------------------------------------------------------
def paths_table(evs, btc, hourly, label):
    hz = [("1h", 1), ("4h", 4), ("24h", 24), ("3d", 72), ("7d", 168), ("14d", 336)] if hourly else \
         [("1d", 1), ("3d", 3), ("7d", 7), ("14d", 14)]
    step = pd.Timedelta(hours=1) if hourly else pd.Timedelta(days=1)
    P(f"\n## Descriptive: post-listing return paths ({label}), excess vs BTC, from listing open  (n={len(evs)})\n")
    P("| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |")
    P("|---|---|---|---|---|---|---|---|---|")
    rec = {}
    for name, h in hz:
        raw, exc, fnd = [], [], []
        for ev in evs:
            k = ev.bars
            if h >= len(k) or (k.index[h] - k.index[0]) != step * h: continue
            p0, p1 = float(k["open"].iloc[0]), float(k["open"].iloc[h])
            b0, b1 = _px_at(btc, k.index[0]), _px_at(btc, k.index[h])
            if not (p0 > 0 and np.isfinite(b0) and np.isfinite(b1)): continue
            r = p1 / p0 - 1; rb = b1 / b0 - 1
            raw.append(r); exc.append(r - rb)
            fr = ev.fund; fnd.append(float(fr[(fr.index > k.index[0]) & (fr.index <= k.index[h])].sum()) if len(fr) else 0.0)
        raw, exc, fnd = np.array(raw), np.array(exc), np.array(fnd)
        t = exc.mean() / exc.std(ddof=1) * np.sqrt(len(exc)) if len(exc) > 2 else np.nan
        P(f"| {name} | {len(raw)} | {100*raw.mean():.2f} | {100*np.median(raw):.2f} | {100*exc.mean():.2f} | {100*np.median(exc):.2f} | {t:.2f} | {(exc>0).mean():.2f} | {100*fnd.mean():.3f} |")
        rec[name] = dict(n=int(len(raw)), mean_raw=float(raw.mean()), med_raw=float(np.median(raw)), mean_exc=float(exc.mean()), t=float(t))
    # from hour/day 24 onward (post-day-1 drift)
    P(f"\nPost-day-1 drift ({label}): from open of bar {'24' if hourly else '1'} to later, excess vs BTC\n")
    P("| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |")
    P("|---|---|---|---|---|---|")
    i0 = 24 if hourly else 1
    for name, h in (hz[2:] if hourly else hz):
        exc = []
        for ev in evs:
            k = ev.bars
            if i0 + h >= len(k) or (k.index[i0 + h] - k.index[i0]) != step * h: continue
            p0, p1 = float(k["open"].iloc[i0]), float(k["open"].iloc[i0 + h])
            b0, b1 = _px_at(btc, k.index[i0]), _px_at(btc, k.index[i0 + h])
            if not (p0 > 0 and np.isfinite(b0) and np.isfinite(b1)): continue
            exc.append(p1 / p0 - 1 - (b1 / b0 - 1))
        exc = np.array(exc)
        t = exc.mean() / exc.std(ddof=1) * np.sqrt(len(exc)) if len(exc) > 2 else np.nan
        P(f"| +{name} | {len(exc)} | {100*exc.mean():.2f} | {100*np.median(exc):.2f} | {t:.2f} | {(exc>0).mean():.2f} |")
    return rec


# ---------------------------------------------------------------------------
# sanity checks
# ---------------------------------------------------------------------------
def sign_shuffle_p(tr, n=2000):
    t = C.add_pnl(tr)
    total = (t["alt_gross"] + t["funding"] + t["hedge_pnl"]).values
    fee = t["fee_usd"].values
    actual = float((total - fee).sum())
    sims = np.array([(total * rng.choice([-1, 1], size=len(total)) - fee).sum() for _ in range(n)])
    return actual, float((sims >= actual).mean()), float(sims.mean()), float(sims.std())


def random_timing_baseline(evs, p, btc, hourly, start, end, n_draws=200):
    """Same rule/hold applied at random entry bars OUTSIDE the listing window
    (>= day 16 after listing)."""
    per_day = 24 if hourly else 1
    step = pd.Timedelta(hours=1) if hourly else pd.Timedelta(days=1)
    if p["rule"] == "short_after": hold, side = per_day * p["H"], -1
    elif p["rule"] == "mom1": hold, side = p["Hh"], None
    else: hold, side = per_day * p["H"], (-1 if p["mode"] == "near_top_short" else 1)
    nets = []
    sel = [ev for ev in evs if start <= ev.t0 < end]
    for _ in range(n_draws):
        rows = []
        for ev in sel:
            k = ev.bars; lo = 16 * per_day; hi = len(k) - hold - 1
            if hi <= lo: continue
            i = int(rng.integers(lo, hi + 1))
            s = side
            if s is None:
                r0 = float(k["close"].iloc[i - 1] / k["open"].iloc[i - 1] - 1)
                if abs(r0) < p["thr"]: continue
                s = int(np.sign(r0)) * (-1 if p["contra"] else 1)
            t = make_trade(ev, s, i, i + hold, p.get("hedge", False), btc, step)
            if t: rows.append(t)
        if rows: nets.append((C.evaluate(pd.DataFrame(rows), 1)["net"], len(rows)))
    ns = np.array([n for _, n in nets]); nets = np.array([x for x, _ in nets])
    return float(nets.mean()), float(nets.std()), float(np.percentile(nets, 95)) if len(nets) else np.nan, float(ns.mean()) if len(ns) else 0


def neighbours(p, grid):
    """Grid points differing from p in exactly one key."""
    out = []
    for q in grid:
        if q is p or q.get("rule") != p.get("rule"): continue
        diff = [k for k in p if p[k] != q.get(k)]
        if len(diff) == 1: out.append(q)
    return out


def fmt_res(r):
    return (f"n={r['n']:4d} net={r['net']:8.1f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:.2f} "
            f"bps={r['net_bps']:6.1f} folds={[round(x,1) for x in r['folds']]} fold_n={r['fold_n']}")


def analyse_sample(evs, btc, hourly, grid, label, sample_key):
    times = (min(e.t0 for e in evs), max(e.t0 for e in evs))
    bounds = C.fold_bounds(times, 3)
    P(f"\n# {label}: walk-forward  (listings {times[0].date()} -> {times[1].date()}; fold starts {[str(b[0].date()) for b in bounds]})")
    P(f"events per fold: {[sum(1 for e in evs if s <= e.t0 < en) for (s, en) in bounds]} (last fold inclusive of end: "
      f"{sum(1 for e in evs if bounds[-1][0] <= e.t0)})")
    run_fn = lambda p, s, e: run_all(evs, p, btc, hourly, s, e)
    # note: fold_bounds' last edge == max t0 -> include the last listing in fold 3
    def run_fn_inc(p, s, e):
        e2 = e + pd.Timedelta(seconds=1) if e == bounds[-1][1] else e
        return run_all(evs, p, btc, hourly, s, e2)
    best, oos, table = C.walk_forward(grid, run_fn_inc, times, n_folds=3, min_trades=10)
    res = C.oos_result(oos, times, 3)
    P(f"\n**Walk-forward best (fold 1, by net):** `{best}`")
    P(f"\n**OOS folds 2+3:** {fmt_res(res)}\n")
    # full table
    P("### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period)\n")
    P("| params | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    full = {}
    for i, p in enumerate(grid):
        tr = run_fn_inc(p, bounds[0][0], bounds[-1][1])
        r = C.evaluate(tr, 3, start=bounds[0][0], end=bounds[-1][1])
        full[i] = (tr, r)
        row = table.iloc[i]
        P(f"| {json.dumps(p)} | {row.is_n} | {row.is_net:.1f} | {row.is_pf:.2f} | {row.is_wr:.2f} | {row.is_net_bps:.1f} | {r['n']} | "
          f"{r['folds'][0]:.1f} | {r['folds'][1]:.1f} | {r['folds'][2]:.1f} | {r['pf']:.2f} | {r['net_bps']:.1f} | {'*' if row.selected else ''} |")
        C.record_to_lab(STRAT, f"{sample_key}:{json.dumps(p, sort_keys=True)}", sample_key, "1h" if hourly else "1d", p, r,
                         period=times, source=SRC, notes=f"full-period all listings; {label}; fees {FEE_SIDE[sample_key]*1e4:.1f}bps/side + funding")
    C.record_to_lab(STRAT, f"{sample_key}:WF_OOS", sample_key, "1h" if hourly else "1d", best, res, period=times, source=SRC,
                    notes=f"walk-forward OOS folds 2+3 of fold-1 pick; {label}")
    # per-family WF picks
    P("\n### Walk-forward pick per rule family (selection on fold 1 only)\n")
    P("| family | fold-1 pick | is_net | OOS n | OOS net | OOS pf | OOS folds |")
    P("|---|---|---|---|---|---|---|")
    fam_res = {}
    for fam in ("short_after", "mom1", "wick"):
        sub = table[[grid[i]["rule"] == fam for i in table.idx]]
        elig = sub[sub.is_n >= 10]
        pick = (elig if len(elig) else sub).sort_values("is_net", ascending=False).iloc[0]
        pp = grid[int(pick.idx)]
        oo = pd.concat([run_fn_inc(pp, s, e) for (s, e) in bounds[1:]], ignore_index=True)
        rr = C.oos_result(oo, times, 3)
        fam_res[fam] = dict(params=pp, oos=rr)
        P(f"| {fam} | `{pp}` | {pick.is_net:.1f} | {rr['n']} | {rr['net']:.1f} | {rr['pf']:.2f} | {[round(x,1) for x in rr['folds'][1:]]} |")
        C.record_to_lab(STRAT, f"{sample_key}:WF_OOS_{fam}", sample_key, "1h" if hourly else "1d", pp, rr, period=times, source=SRC,
                        notes=f"walk-forward OOS folds 2+3 of the fold-1 pick within rule family {fam}; {label}")
    # sanity on the overall pick
    P("\n### Sanity checks on the walk-forward pick (OOS trades only)\n")
    checks = {}
    if len(oos):
        act, pv, mu, sd = sign_shuffle_p(oos)
        P(f"- sign-shuffle (random long/short per trade, fees kept): actual net {act:.1f}; shuffled mean {mu:.1f} sd {sd:.1f}; p(shuffled >= actual) = {pv:.3f}")
        checks["shuffle_p"] = pv
        bm, bs, b95, bn = random_timing_baseline(evs, best, btc, hourly, bounds[1][0], bounds[-1][1] + pd.Timedelta(seconds=1))
        P(f"- random-timing baseline (same rule/hold, entry at random bar >= day 16 after listing, same coins, 200 draws, avg n={bn:.0f}): mean net {bm:.1f} sd {bs:.1f} p95 {b95:.1f} vs actual {res['net']:.1f}")
        checks["random_timing_mean"] = bm; checks["random_timing_p95"] = b95
        t = C.add_pnl(oos)
        P(f"- independent decisions: {t.entry_time.dt.floor('D').nunique()} distinct entry days among {len(t)} OOS trades (Binance lists several perps on one day)")
        checks["distinct_days"] = int(t.entry_time.dt.floor('D').nunique())
        by_year = t.groupby(t.entry_time.dt.year)["net_pnl"].agg(["sum", "count"])
        P(f"- OOS net by year: " + ", ".join(f"{y}: {s:.1f} (n={int(c)})" for y, (s, c) in by_year.iterrows()))
        checks["by_year"] = {int(y): float(s) for y, (s, c) in by_year.iterrows()}
        srt = t.sort_values("net_pnl", ascending=False)
        top3 = float(srt["net_pnl"].iloc[:3].sum()); rest = float(t["net_pnl"].sum() - top3)
        P(f"- top-3 winners removed: {res['net']:.1f} -> {rest:.1f}  (top-3 = {top3:.1f}: {srt['instrument'].iloc[:3].tolist()})")
        checks["net_minus_top3"] = rest
        n10 = max(1, len(t) // 10)
        P(f"- concentration: top 10% of trades ({n10}) contribute {srt['net_pnl'].iloc[:n10].sum():.1f} of gross-positive {t.net_pnl[t.net_pnl>0].sum():.1f}; "
          f"largest single coin share of |net| = {t.groupby('instrument').net_pnl.sum().abs().max()/max(1e-9, t.net_pnl.abs().sum()):.2f}")
        P(f"- OOS components: alt leg {t.alt_gross.sum():.1f}, funding {t.funding.sum():.1f}, hedge leg {t.hedge_pnl.sum():.1f}, fees -{t.fee_usd.sum():.1f}")
        checks["components"] = dict(alt=float(t.alt_gross.sum()), funding=float(t.funding.sum()), hedge=float(t.hedge_pnl.sum()), fees=float(t.fee_usd.sum()))
        # liquidity: day-1 quote volume of the traded coins
        qv = pd.Series({e.sym: e.day1_qv for e in evs})
        tq = t.assign(qv=t.instrument.map(qv))
        lo = tq[tq.qv < tq.qv.median()]; hi = tq[tq.qv >= tq.qv.median()]
        P(f"- liquidity split (day-1 $ volume median {qv.median()/1e6:.1f}M): low-liquidity half net {lo.net_pnl.sum():.1f} (n={len(lo)}), high half {hi.net_pnl.sum():.1f} (n={len(hi)})")
        checks["low_liq_net"] = float(lo.net_pnl.sum()); checks["high_liq_net"] = float(hi.net_pnl.sum())
        fresh = {e.sym for e in evs if e.flags.get("fresh")}
        tf = t[t.instrument.isin(fresh)]; te_ = t[~t.instrument.isin(fresh)]
        P(f"- fresh vs established: fresh-token listings net {tf.net_pnl.sum():.1f} (n={len(tf)}, pf={C.evaluate(tf,1)['pf'] if len(tf) else 0:.2f}), "
          f"established-coin listings net {te_.net_pnl.sum():.1f} (n={len(te_)}, pf={C.evaluate(te_,1)['pf'] if len(te_) else 0:.2f})")
        checks["fresh_net"] = float(tf.net_pnl.sum()); checks["fresh_n"] = int(len(tf)); checks["estab_net"] = float(te_.net_pnl.sum())
        fp_ = run_fn_inc(best, bounds[0][0], bounds[-1][1]); fp_ = C.add_pnl(fp_)
        byy = fp_.groupby(fp_.entry_time.dt.year)["net_pnl"].agg(["sum", "count", "mean"])
        P("- full-period (incl. fold 1) net by year for the pick: " + ", ".join(f"{y}: {r['sum']:.0f} (n={int(r['count'])}, avg {r['mean']:.0f})" for y, r in byy.iterrows()))
        # neighbours
        P("- neighbours (one param changed), OOS folds 2+3:")
        nb = []
        for q in neighbours(best, grid):
            oo = pd.concat([run_fn_inc(q, s, e) for (s, e) in bounds[1:]], ignore_index=True)
            rr = C.oos_result(oo, times, 3)
            nb.append(rr["net"])
            P(f"    - `{q}`: n={rr['n']} net={rr['net']:.1f} pf={rr['pf']:.2f} folds={[round(x,1) for x in rr['folds'][1:]]}")
        checks["neighbour_nets"] = nb
    return dict(best=best, oos=res, oos_trades=oos, table=table, fam=fam_res, checks=checks, bounds=bounds, times=times)


def verdict(res, checks, fam=None):
    r = res
    ok = r["net"] > 0 and r["pf"] >= 1.2 and r["n"] >= 60 and all(f > 0 for f in r["folds"][1:])
    surv = (checks.get("shuffle_p", 1) < 0.05 and checks.get("net_minus_top3", -1) > 0
            and (len(checks.get("neighbour_nets", [])) == 0 or np.mean(np.array(checks["neighbour_nets"]) > 0) >= 0.5)
            and r["net"] > checks.get("random_timing_p95", np.inf))   # must beat same-coin random-timing baseline
    if ok and surv: return "edge"
    if r["net"] > 0: return "weak"
    return "none"


def main():
    P("# hl_listing_drift -- results\n")
    P("Fees: Binance UM taker 5.0 bps/side, Hyperliquid taker 4.5 bps/side; funding included (long pays positive rate); "
      "hedge = opposite BTC leg of equal notional (fees on both legs, BTC funding ignored). $1000 notional per event.")
    b_evs, b_btc, b_drop, earliest = load_binance_events()
    P(f"\nBinance UM archive: {len(b_evs)} usable listings; dropped: " + ", ".join(f"{k}={len(v)}" for k, v in b_drop.items())
      + f"; earliest archive month {earliest} (symbols starting there are excluded as unverifiable listings: {b_drop['archive_start']})")
    P(f"month-boundary starts excluded (could be archive artefacts): {b_drop['month_boundary']}")
    yrs = pd.Series([e.t0.year for e in b_evs]).value_counts().sort_index()
    P("listings per year: " + ", ".join(f"{y}: {n}" for y, n in yrs.items()))
    h_evs, h_btc, h_drop = load_hl_events()
    launch = [e.sym for e in h_evs if e.t0 == pd.Timestamp("2023-02-26", tz="UTC")]
    h_evs = [e for e in h_evs if e.t0 != pd.Timestamp("2023-02-26", tz="UTC")]
    P(f"HL exchange-launch batch (2023-02-26, not listing events) excluded: {launch}")
    first = earliest_first_trade()
    for e in b_evs + h_evs:
        b = base_asset(e.sym, e.sample)
        e.flags["fresh"] = bool(e.t0 <= first.get(b, e.t0) + pd.Timedelta(days=3))
    P(f"'fresh' listings (exchange listing <= 3 days after the token's first trade in any of our sources: Binance spot 2018+, Binance UM, HL): "
      f"Binance {sum(e.flags['fresh'] for e in b_evs)}/{len(b_evs)}, HL {sum(e.flags['fresh'] for e in h_evs)}/{len(h_evs)}")
    P(f"\nHyperliquid: {len(h_evs)} listings (meta incl. delisted; listing day = first daily candle with volume>0); dropped: "
      + ", ".join(f"{k}={len(v)}" for k, v in h_drop.items()))
    yrs = pd.Series([e.t0.year for e in h_evs]).value_counts().sort_index()
    P("listings per year: " + ", ".join(f"{y}: {n}" for y, n in yrs.items()) + f"; delisted since: {sum(1 for e in h_evs if e.flags.get('delisted'))}; funding series present: {sum(1 for e in h_evs if e.flags.get('has_funding'))}")
    hourly_hl = [e for e in h_evs if e.t0 >= pd.Timestamp('2026-02-01', tz='UTC')]
    P(f"HL listings inside the cached 1h window (>= 2026-02-01): {[e.sym for e in hourly_hl]} -> too few for an hourly test; HL rules use daily bars.")
    pb = paths_table(b_evs, b_btc, True, "Binance UM 1h")
    paths_table([e for e in b_evs if e.flags["fresh"]], b_btc, True, "Binance UM 1h, FRESH tokens only")
    ph = paths_table(h_evs, h_btc, False, "Hyperliquid 1d")
    paths_table([e for e in h_evs if e.flags["fresh"]], h_btc, False, "Hyperliquid 1d, FRESH tokens only")
    B = analyse_sample(b_evs, b_btc, True, grid_binance(), "Binance UM listings 2019-2026 (1h)", "binance")
    H = analyse_sample(h_evs, h_btc, False, grid_hl(), "Hyperliquid listings 2023-2026 (1d)", "hl")
    # cross-sample: apply Binance pick (daily analogue) to HL
    P("\n# Cross-sample transfer\n")
    bp = dict(B["best"])
    if bp["rule"] == "short_after": hp = dict(rule="short_after", N=1, H=bp["H"], hedge=bp["hedge"])
    elif bp["rule"] == "mom1": hp = dict(rule="mom1", thr=bp["thr"], Hh=max(1, bp["Hh"] // 24), contra=bp["contra"])
    else: hp = dict(bp)
    tr = run_all(h_evs, hp, h_btc, False)
    rr = C.evaluate(tr, 3, start=H["times"][0], end=H["times"][1])
    P(f"Binance fold-1 pick `{bp}` -> HL daily analogue `{hp}` on ALL HL listings: {fmt_res(rr)}")
    C.record_to_lab(STRAT, "hl:transfer_of_binance_pick", "hl", "1d", hp, rr, period=H["times"], source=SRC, notes="Binance fold-1 pick applied to all HL listings (daily analogue)")
    # capacity
    qv = pd.Series({e.sym: e.day1_qv for e in h_evs if e.t0 >= pd.Timestamp('2025-01-01', tz='UTC')})
    cap = float(np.median(qv) * 0.01)
    P(f"\nCapacity: HL listings since 2025 have median day-1 $ volume {qv.median()/1e6:.1f}M (p25 {qv.quantile(.25)/1e6:.1f}M); at 1% participation ~${cap:,.0f} per event, ~{len(qv)/ ((max(e.t0 for e in h_evs) - pd.Timestamp('2025-01-01', tz='UTC')).days/30):.1f} listings/month.")
    vb = verdict(B["oos"], B["checks"]); vh = verdict(H["oos"], H["checks"])
    P(f"\n# Verdict\n\nBinance (headline, multi-year): **{vb}**; Hyperliquid daily: **{vh}**.")
    out = dict(key="hl_listing_drift", binance=dict(best=B["best"], oos={k: v for k, v in B["oos"].items()}, checks=B["checks"],
               fam={k: dict(params=v["params"], oos_net=v["oos"]["net"], oos_n=v["oos"]["n"], oos_pf=v["oos"]["pf"], folds=v["oos"]["folds"]) for k, v in B["fam"].items()}, verdict=vb,
               paths=pb, n_events=len(b_evs)),
               hl=dict(best=H["best"], oos={k: v for k, v in H["oos"].items()}, checks=H["checks"],
               fam={k: dict(params=v["params"], oos_net=v["oos"]["net"], oos_n=v["oos"]["n"], oos_pf=v["oos"]["pf"], folds=v["oos"]["folds"]) for k, v in H["fam"].items()}, verdict=vh,
               paths=ph, n_events=len(h_evs)), transfer=dict(params=hp, res=rr), capacity_usd=cap)
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    B["oos_trades"].to_csv(ROOT / "tests" / "h_hl_listing_drift_binance_oos_trades.csv", index=False)
    return out


if __name__ == "__main__":
    out = main()
    OUT_MD.write_text("\n".join(LINES) + "\n")
