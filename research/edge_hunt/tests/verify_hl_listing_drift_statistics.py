"""STATISTICS lens on hl_listing_drift (Binance UM: short at listing+24h, hold 7d, BTC-hedged).

Asks: is +$18k OOS a real repeatable effect, or selection + luck + a decaying regime?

S1 expanding-window walk-forward, re-selected every calendar year (the honest OOS)
S2 equal-event-count folds instead of calendar thirds
S3 bootstrap (iid / day-cluster / month-block)      S4 cluster-robust t
S5 trimming: top-k trades, best year, best month, winsorised
S6 breadth: how much of the parameter grid is OOS-positive
S7 MATCHED-DATE CONTROL: same dates, seasoned coins -- is this just "short alts vs BTC"?
S8 decay: is 2026 statistically different from 2020-2025?
S9 underlying event study: excess return vs BTC, day1 -> day8, clustered
"""
from __future__ import annotations
import os, json, sys, collections
os.environ["NOLAB"] = "1"
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import h_hl_listing_drift as T
import common as C

OUT = HERE / "verify_hl_listing_drift_statistics.json"
MD  = HERE / "verify_hl_listing_drift_statistics.md"
L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); L.append(s)

rng = np.random.default_rng(23)
BEST = dict(rule="short_after", N=24, H=7, hedge=True)
NOT = T.NOTIONAL
res = {}
UTC = lambda s: pd.Timestamp(s, tz="UTC")

evs, btc, drop, earliest = T.load_binance_events()
bounds = C.fold_bounds((min(e.t0 for e in evs), max(e.t0 for e in evs)), 3)
P(f"# STATISTICS — hl_listing_drift (Binance UM), pick `{BEST}`\n")
P(f"events={len(evs)} listings {min(e.t0 for e in evs).date()} -> {max(e.t0 for e in evs).date()}\n")

def trades(events, p=BEST, lo=None, hi=None):
    rows = []
    for ev in events:
        if lo is not None and ev.t0 < lo: continue
        if hi is not None and ev.t0 >= hi: continue
        t = T.rule_trade(ev, p, btc, True)
        if t: rows.append(t)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)

oos = trades(evs, lo=bounds[1][0])
base = C.evaluate(oos, 1)
t = C.add_pnl(oos)
P(f"baseline OOS: n={base['n']} net={base['net']:.1f} pf={base['pf']:.2f} avg={base['net']/base['n']:.2f} "
  f"({1e4*base['net']/base['n']/NOT:.1f} bps/trade)\n")
res["baseline"] = base

# ------------------------------------------------------------------ S1
P("## S1 — expanding-window walk-forward: re-pick the parameters every year\n")
grid = T.grid_binance()
P("| test year | picked on all prior listings | train n | test n | test net | test pf | bps/trade |")
P("|---|---|---|---|---|---|---|")
s1_rows, s1_net = [], 0.0
for y in range(2021, 2027):
    lo, hi = UTC(f"{y}-01-01"), UTC(f"{y+1}-01-01")
    best_p, best_net, best_n = None, -1e18, 0
    for p in grid:
        tr = trades(evs, p, hi=lo)
        if len(tr) < 20: continue
        r = C.evaluate(tr, 1)
        if r["net"] > best_net: best_p, best_net, best_n = p, r["net"], r["n"]
    if best_p is None: continue
    te = trades(evs, best_p, lo=lo, hi=hi)
    r = C.evaluate(te, 1) if len(te) else C.empty_result(1)
    s1_net += r["net"]
    bp = f"{best_p['rule']} " + " ".join(f"{k}={v}" for k, v in best_p.items() if k != "rule")
    P(f"| {y} | `{bp}` | {best_n} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {1e4*r['net']/max(1,r['n'])/NOT:.1f} |")
    s1_rows.append(dict(year=y, params=best_p, train_n=best_n, n=r["n"], net=r["net"], pf=r["pf"]))
P(f"\n**Expanding-window OOS total 2021-2026: ${s1_net:,.0f}** across {sum(r['n'] for r in s1_rows)} trades "
  f"(this is the number to believe: parameters are re-chosen only on the past, every year).")
res["S1"] = dict(rows=s1_rows, total_net=s1_net)

# ------------------------------------------------------------------ S2
P("\n## S2 — equal-event-count folds (calendar thirds put 0 events in fold 1)\n")
srt = sorted(evs, key=lambda e: e.t0); k3 = len(srt) // 3
f1, f2, f3 = srt[:k3], srt[k3:2*k3], srt[2*k3:]
P(f"- fold sizes {len(f1)}/{len(f2)}/{len(f3)}; boundaries {f1[-1].t0.date()} | {f2[-1].t0.date()}")
best_p, best_net = None, -1e18
for p in grid:
    r = C.evaluate(trades(f1, p), 1)
    if r["n"] >= 20 and r["net"] > best_net: best_p, best_net = p, r["net"]
r2, r3 = C.evaluate(trades(f2, best_p), 1), C.evaluate(trades(f3, best_p), 1)
P(f"- fold-1 pick `{best_p}` (is net {best_net:.0f}) -> fold2 n={r2['n']} net={r2['net']:.1f} pf={r2['pf']:.2f}; "
  f"fold3 n={r3['n']} net={r3['net']:.1f} pf={r3['pf']:.2f}")
res["S2"] = dict(pick=best_p, fold2=r2, fold3=r3)

# ------------------------------------------------------------------ S3 / S4
P("\n## S3/S4 — resampling and clustering\n")
net = t.net_pnl.values
day = t.entry_time.dt.floor("D"); mon = t.entry_time.dt.to_period("M")
def boot(groups, n=5000):
    keys = groups.unique(); byk = {k: net[(groups == k).values] for k in keys}
    sims = np.empty(n)
    for i in range(n):
        pick = rng.choice(keys, size=len(keys), replace=True)
        sims[i] = sum(byk[k].sum() for k in pick)
    return sims
for lbl, g in (("iid trades", pd.Series(np.arange(len(net)))), ("clustered by entry day", day), ("clustered by month", mon)):
    sims = boot(g)
    P(f"- bootstrap ({lbl}, {g.nunique()} units): mean {sims.mean():.0f}, P(net<=0) = {float((sims<=0).mean()):.4f}")
    res.setdefault("S3", {})[lbl] = dict(units=int(g.nunique()), p_le_0=float((sims <= 0).mean()))
for lbl, g in (("entry day", day), ("month", mon)):
    gs = pd.Series(net).groupby(g.values).sum()
    tstat = gs.mean() / gs.std(ddof=1) * np.sqrt(len(gs))
    P(f"- cluster-robust t (clusters = {lbl}, {len(gs)} clusters): t = {tstat:.2f}")
    res.setdefault("S4", {})[lbl] = dict(clusters=int(len(gs)), t=float(tstat))

# ------------------------------------------------------------------ S5
P("\n## S5 — trimming\n")
s = t.sort_values("net_pnl", ascending=False)
for k in (3, 5, 10, 25):
    P(f"- remove top-{k} winners: {base['net']:.0f} -> {base['net'] - s.net_pnl.iloc[:k].sum():.0f}")
    res.setdefault("S5", {})[f"ex_top{k}"] = float(base["net"] - s.net_pnl.iloc[:k].sum())
byy = t.groupby(t.entry_time.dt.year).net_pnl.sum()
P(f"- remove the best year ({byy.idxmax()}, {byy.max():.0f}): {base['net'] - byy.max():.0f}")
bym = t.groupby(t.entry_time.dt.to_period('M')).net_pnl.sum()
P(f"- remove the best month ({bym.idxmax()}, {bym.max():.0f}): {base['net'] - bym.max():.0f}")
P(f"- positive months {int((bym>0).sum())}/{len(bym)}; median month {bym.median():.0f}")
w = np.clip(net, np.percentile(net, 1), np.percentile(net, 99))
P(f"- winsorised at 1/99 pct: {w.sum():.0f} (raw {net.sum():.0f})")
res["S5"].update(ex_best_year=float(base["net"] - byy.max()), ex_best_month=float(base["net"] - bym.max()),
                 pos_months=int((bym > 0).sum()), n_months=int(len(bym)), winsorised=float(w.sum()))

# ------------------------------------------------------------------ S6
P("\n## S6 — breadth of the parameter grid (OOS folds 2+3)\n")
allr = {}
for p in grid:
    r = C.evaluate(trades(evs, p, lo=bounds[1][0]), 1)
    allr[json.dumps(p, sort_keys=True)] = r
pos = sum(1 for r in allr.values() if r["net"] > 0 and r["n"] >= 30)
tot = sum(1 for r in allr.values() if r["n"] >= 30)
P(f"- {pos}/{tot} grid variants with n>=30 are OOS-positive.")
sa = {k: v for k, v in allr.items() if '"short_after"' in k and v["n"] >= 30}
P(f"- short_after family: {sum(1 for v in sa.values() if v['net']>0)}/{len(sa)} positive; "
  f"nets {sorted(round(v['net']) for v in sa.values())}")
res["S6"] = dict(positive=pos, total=tot, short_after_nets=sorted(float(v["net"]) for v in sa.values()))

# ------------------------------------------------------------------ S7
P("\n## S7 — matched-date control: same dates, SEASONED coins (spot daily panel)\n")
panel = pd.read_parquet(C.DATA / "binance_panel_1d.parquet")
panel["time"] = pd.to_datetime(panel["time"], utc=True)
pv = panel.pivot_table(index="time", columns="symbol", values="open")
first_seen = panel.groupby("symbol")["time"].min()
BTCD = pv["BTCUSDT"]
dates = pv.index
def control_book(draws=300):
    """For every OOS trade, short a random coin that had already been trading for
    >= 90 days on that date, 7-day hold, BTC-hedged, same fees. Same dates, same
    count, same market -- everything except the listing event."""
    ent = t.entry_time.dt.floor("D") + pd.Timedelta(days=1)
    nets = []
    idxmap = dates.searchsorted(pd.DatetimeIndex(ent))
    for _ in range(draws):
        tot = 0.0; used = 0
        for i in range(len(t)):
            di = idxmap[i]
            if di + 7 >= len(dates): continue
            d0, d1 = dates[di], dates[di + 7]
            row0, row1 = pv.iloc[di], pv.iloc[di + 7]
            ok = row0.notna() & row1.notna() & (first_seen <= d0 - pd.Timedelta(days=90)).reindex(row0.index).fillna(False)
            cand = row0.index[ok.values]
            if len(cand) < 5: continue
            sym = cand[rng.integers(len(cand))]
            p0, p1 = float(row0[sym]), float(row1[sym])
            b0, b1 = float(BTCD.iloc[di]), float(BTCD.iloc[di + 7])
            if not (p0 > 0 and p1 > 0 and b0 > 0 and b1 > 0): continue
            alt = -(p1 - p0) / p0 * NOT
            hed = (b1 - b0) / b0 * NOT
            fee = T.FEE_SIDE["binance"] * (NOT + NOT * p1 / p0) + T.FEE_SIDE["binance"] * (NOT + NOT * b1 / b0)
            tot += alt + hed - fee; used += 1
        nets.append(tot)
    return np.array(nets), used
ctrl, used_n = control_book(300)
price_only = float((t.alt_gross + t.hedge_pnl - t.fee_usd).sum())   # exclude funding, to match the control
P(f"- control book: {used_n} legs per draw, 300 draws. mean ${ctrl.mean():,.0f}, sd ${ctrl.std():,.0f}, "
  f"p95 ${np.percentile(ctrl,95):,.0f}, max ${ctrl.max():,.0f}")
P(f"- actual listing book, price component only (alt + hedge - fees, funding excluded): ${price_only:,.0f}")
P(f"- **p(control >= actual) = {float((ctrl >= price_only).mean()):.4f}**")
P(f"- actual including funding: ${base['net']:,.0f} (funding costs ${t.funding.sum():,.0f})")
res["S7"] = dict(control_mean=float(ctrl.mean()), control_sd=float(ctrl.std()), control_p95=float(np.percentile(ctrl, 95)),
                 actual_price_only=price_only, p_control_ge_actual=float((ctrl >= price_only).mean()),
                 legs_per_draw=int(used_n))

# ------------------------------------------------------------------ S8
P("\n## S8 — decay\n")
bps = 1e4 * t.net_pnl / NOT
yr = t.entry_time.dt.year
tab = pd.DataFrame({"bps": bps, "yr": yr}).groupby("yr")["bps"].agg(["count", "mean", "std"])
P("| year | n | mean bps/trade | t |")
P("|---|---|---|---|")
for y, r0 in tab.iterrows():
    tt = r0["mean"] / r0["std"] * np.sqrt(r0["count"]) if r0["std"] > 0 else np.nan
    P(f"| {y} | {int(r0['count'])} | {r0['mean']:.1f} | {tt:.2f} |")
pre = bps[yr < 2026]; cur = bps[yr == 2026]
se = np.sqrt(pre.var(ddof=1)/len(pre) + cur.var(ddof=1)/len(cur))
P(f"\n- 2026 mean {cur.mean():.1f} bps (n={len(cur)}) vs 2022-2025 mean {pre.mean():.1f} bps (n={len(pre)}); "
  f"difference {cur.mean()-pre.mean():.1f} bps, t = {(cur.mean()-pre.mean())/se:.2f}")
P(f"- 2026 alone: t = {cur.mean()/cur.std(ddof=1)*np.sqrt(len(cur)):.2f}, net ${float(t.net_pnl[yr==2026].sum()):,.0f}")
sl = np.polyfit(t.entry_time.map(pd.Timestamp.timestamp).values / 86400 / 365.25, bps.values, 1)[0]
P(f"- OLS trend in per-trade bps: {sl:.1f} bps per year")
res["S8"] = dict(by_year={int(y): dict(n=int(r0["count"]), mean_bps=float(r0["mean"])) for y, r0 in tab.iterrows()},
                 t_2026_vs_prior=float((cur.mean()-pre.mean())/se), t_2026=float(cur.mean()/cur.std(ddof=1)*np.sqrt(len(cur))),
                 trend_bps_per_year=float(sl))

# ------------------------------------------------------------------ S9
P("\n## S9 — underlying event study (no trading rule): excess return vs BTC, hour 24 -> hour 192\n")
rows = []
for ev in evs:
    k = ev.bars
    if 24 + 168 >= len(k): continue
    if (k.index[24+168] - k.index[24]) != pd.Timedelta(hours=168): continue
    p0, p1 = float(k["open"].iloc[24]), float(k["open"].iloc[24+168])
    b0, b1 = T._px_at(btc, k.index[24]), T._px_at(btc, k.index[24+168])
    if not (p0 > 0 and np.isfinite(b0) and np.isfinite(b1)): continue
    rows.append(dict(sym=ev.sym, t=k.index[24], exc=(p1/p0 - 1) - (b1/b0 - 1), yr=k.index[24].year))
ed = pd.DataFrame(rows)
g = ed.groupby(ed.t.dt.floor("D"))["exc"].mean()
P(f"- n={len(ed)} listings; mean excess {100*ed.exc.mean():.2f}%, median {100*ed.exc.median():.2f}%, "
  f"share negative {float((ed.exc<0).mean()):.2f}")
P(f"- naive t = {ed.exc.mean()/ed.exc.std(ddof=1)*np.sqrt(len(ed)):.2f}; "
  f"day-clustered t = {g.mean()/g.std(ddof=1)*np.sqrt(len(g)):.2f} ({len(g)} distinct days)")
ey = ed.groupby("yr")["exc"].agg(["count", "mean", "median"])
P("- by year: " + ", ".join(f"{y}: {100*r0['mean']:.1f}% (med {100*r0['median']:.1f}%, n={int(r0['count'])})" for y, r0 in ey.iterrows()))
res["S9"] = dict(n=int(len(ed)), mean_exc=float(ed.exc.mean()), median_exc=float(ed.exc.median()),
                 t_day_clustered=float(g.mean()/g.std(ddof=1)*np.sqrt(len(g))),
                 by_year={int(y): dict(n=int(r0["count"]), mean=float(r0["mean"]), median=float(r0["median"])) for y, r0 in ey.iterrows()})

OUT.write_text(json.dumps(res, indent=1, default=str))
MD.write_text("\n".join(L) + "\n")
print(f"\nwrote {OUT.name} / {MD.name}")
