"""EXECUTION lens on hl_listing_drift (Binance UM pick: short_after N=24 H=7 hedged).

Asks: does the +$18k OOS survive real fills, real funding, and real size?

E1 slippage sweep + break-even      E2 entry/exit timing perturbation
E3 adverse-fill bounds              E4 funding realism (it is the biggest cost)
E5 capacity per event               E6 concurrency / capital / margin
E7 2026-only under friction         E8 combined realistic scenario
"""
from __future__ import annotations
import os, json, sys, collections
os.environ["NOLAB"] = "1"
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import h_hl_listing_drift as T
import common as C

OUT = HERE / "verify_hl_listing_drift_execution.json"
MD  = HERE / "verify_hl_listing_drift_execution.md"
L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); L.append(s)

Y26 = pd.Timestamp("2026-01-01", tz="UTC")
NOT = T.NOTIONAL
FEE = T.FEE_SIDE["binance"]
HOLD_H = 24 * 7
IENT = 24
res = {}

evs, btc, drop, earliest = T.load_binance_events()
bounds = C.fold_bounds((min(e.t0 for e in evs), max(e.t0 for e in evs)), 3)
OOS_START = bounds[1][0]
P(f"# EXECUTION — hl_listing_drift (Binance UM), short at listing+24h, hold 7d, BTC-hedged\n")
P(f"events={len(evs)}; OOS = listings from {OOS_START.date()}; ${NOT:.0f}/event; taker {FEE*1e4:.1f} bps/side both legs.\n")


def mk(ev, ient=IENT, hold=HOLD_H, slip_bps=0.0, hedge=True, fee_bps=FEE * 1e4,
       entry_col="open", exit_col="open", fund_mult=1.0):
    """Short the alt at ient, cover at ient+hold. slip_bps is paid on every leg
    of every side (sell lower, buy higher)."""
    k = ev.bars; ix = ient + hold
    if ient < 1 or ix >= len(k): return None
    te, tx = k.index[ient], k.index[ix]
    if (tx - te) != pd.Timedelta(hours=1) * hold: return None
    pe, px = float(k[entry_col].iloc[ient]), float(k[exit_col].iloc[ix])
    if not (pe > 0 and px > 0): return None
    s = slip_bps / 1e4
    pe_f, px_f = pe * (1 - s), px * (1 + s)          # sell into entry, buy back at exit
    qty = NOT / pe_f
    alt = -(px_f - pe_f) * qty
    fr = ev.fund
    fsum = float(fr[(fr.index > te) & (fr.index <= tx)].sum()) if len(fr) else 0.0
    funding = fsum * NOT * fund_mult                  # short receives positive funding
    fee = (fee_bps / 1e4) * (NOT + qty * px_f)
    hp = 0.0
    if hedge:
        be, bx = T._px_at(btc, te), T._px_at(btc, tx)
        if not (np.isfinite(be) and np.isfinite(bx)): return None
        be_f, bx_f = be * (1 + s), bx * (1 - s)       # long BTC
        hp = (bx_f - be_f) * (NOT / be_f)
        fee += (fee_bps / 1e4) * (NOT + NOT * bx_f / be_f)
    tot = alt + funding + hp
    return dict(entry_time=te, exit_time=tx, side=-1.0, entry_px=pe_f,
                exit_px=pe_f - tot / qty, qty=qty, notional_usd=NOT, fee_usd=fee,
                instrument=ev.sym, alt_gross=alt, funding=funding, hedge_pnl=hp,
                qv_entry=float(k["quote_volume"].iloc[ient]), qv_exit=float(k["quote_volume"].iloc[ix]))


def run(**kw):
    rows = [t for ev in evs if ev.t0 >= OOS_START for t in [mk(ev, **kw)] if t]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    r = C.evaluate(df, 1)
    r["folds2"] = [float(C.evaluate(df[df.entry_time < bounds[2][0]], 1)["net"]),
                   float(C.evaluate(df[df.entry_time >= bounds[2][0]], 1)["net"])] if len(df) else [0, 0]
    return df, r


base_df, base = run()
P(f"baseline (0 bps slippage): n={base['n']} net={base['net']:.1f} pf={base['pf']:.2f} bps={base['net_bps']:.1f} folds={[round(x) for x in base['folds2']]}\n")
res["baseline"] = {k: v for k, v in base.items()}

# ---------------------------------------------------------------- E1
P("## E1 — slippage sweep (bps per side, applied to alt AND hedge legs)\n")
P("| slip bps/side | n | net | pf | net bps/trade | fold2 | fold3 | 2026 net |")
P("|---|---|---|---|---|---|---|---|")
sweep = {}
for s in (0, 2, 5, 10, 15, 20, 30, 50):
    df, r = run(slip_bps=s)
    _t = C.add_pnl(df) if len(df) else None
    y26 = float(_t.loc[_t.entry_time >= Y26, "net_pnl"].sum()) if _t is not None else 0.0
    P(f"| {s} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['net_bps']:.1f} | {r['folds2'][0]:.0f} | {r['folds2'][1]:.0f} | {y26:.1f} |")
    sweep[s] = dict(n=r["n"], net=r["net"], pf=r["pf"], bps=r["net_bps"], folds=r["folds2"], net_2026=y26)
res["E1"] = sweep
be = next((s for s in sorted(sweep) if sweep[s]["net"] <= 0), None)
P(f"\n- break-even slippage: {'>50' if be is None else f'between {max([x for x in sweep if x < be])} and {be}'} bps per side "
  f"(4 legs per trade, so total round-trip friction = 4x this + {FEE*4*1e4:.0f} bps of fees).")
res["E1_breakeven_bps"] = be

# ---------------------------------------------------------------- E2
P("\n## E2 — entry / exit timing perturbation (10 bps slippage throughout)\n")
P("| variant | n | net | pf | bps |")
P("|---|---|---|---|---|")
pert = {}
for lbl, kw in [("entry h-6", dict(ient=18)), ("entry h-2", dict(ient=22)), ("entry h24 (base)", dict()),
                ("entry h+2", dict(ient=26)), ("entry h+6", dict(ient=30)), ("entry h+24 (day 2)", dict(ient=48)),
                ("entry at close of h24", dict(entry_col="close")), ("exit at close", dict(exit_col="close")),
                ("hold 5d", dict(hold=24*5)), ("hold 10d", dict(hold=24*10)), ("hold 14d", dict(hold=24*14))]:
    df, r = run(slip_bps=10, **kw)
    P(f"| {lbl} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['net_bps']:.1f} |")
    pert[lbl] = dict(n=r["n"], net=r["net"], pf=r["pf"], bps=r["net_bps"])
res["E2"] = pert

# ---------------------------------------------------------------- E3
P("\n## E3 — adverse-fill bounds (no extra slippage; fills taken from the bar's own range)\n")
def adverse(frac):
    """Short entry filled `frac` of the way from open toward the bar LOW,
    cover filled `frac` of the way from open toward the bar HIGH."""
    rows = []
    for ev in evs:
        if ev.t0 < OOS_START: continue
        k = ev.bars; ix = IENT + HOLD_H
        if ix >= len(k): continue
        o1, l1 = float(k["open"].iloc[IENT]), float(k["low"].iloc[IENT])
        o2, h2 = float(k["open"].iloc[ix]), float(k["high"].iloc[ix])
        t = mk(ev)
        if t is None: continue
        pe_f = o1 - frac * (o1 - l1); px_f = o2 + frac * (h2 - o2)
        qty = NOT / pe_f; alt = -(px_f - pe_f) * qty
        fee = FEE * (NOT + qty * px_f) + (t["fee_usd"] - FEE * (NOT + t["qty"] * (t["entry_px"] - t["alt_gross"] / t["qty"])))
        tot = alt + t["funding"] + t["hedge_pnl"]
        rows.append(dict(entry_time=t["entry_time"], exit_time=t["exit_time"], side=-1.0, entry_px=pe_f,
                         exit_px=pe_f - tot / qty, qty=qty, notional_usd=NOT, fee_usd=t["fee_usd"],
                         instrument=ev.sym))
    return C.evaluate(pd.DataFrame(rows), 1)
P("| fill quality | n | net | pf |")
P("|---|---|---|---|")
adv = {}
for lbl, f in [("open (base)", 0.0), ("25% toward the adverse extreme", 0.25), ("50% (mid of open->extreme)", 0.5), ("worst price of the bar", 1.0)]:
    r = adverse(f); P(f"| {lbl} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} |"); adv[lbl] = dict(n=r["n"], net=r["net"], pf=r["pf"])
res["E3"] = adv

# ---------------------------------------------------------------- E4
P("\n## E4 — funding realism (the short PAYS on net here)\n")
iv = collections.Counter()
for ev in evs:
    fp = T.BUM / f"{ev.sym}_funding.parquet"
    if fp.exists():
        d = pd.read_parquet(fp)
        if "interval_h" in d.columns: iv.update(d["interval_h"].dropna().astype(int).tolist())
P(f"- funding interval hours across the archive: {dict(iv.most_common(5))}")
t = C.add_pnl(base_df)
P(f"- OOS components at 0 bps: alt {t.alt_gross.sum():.0f}, funding {t.funding.sum():.0f}, hedge {t.hedge_pnl.sum():.0f}, fees -{t.fee_usd.sum():.0f}")
fund_stats = t.funding.describe()
P(f"- per-trade funding: mean {t.funding.mean():.2f} USD on ${NOT:.0f} ({1e4*t.funding.mean()/NOT:.1f} bps), "
  f"p05 {t.funding.quantile(.05):.1f}, p95 {t.funding.quantile(.95):.1f}, share negative {float((t.funding<0).mean()):.2f}")
for lbl, m in [("funding x0 (ignored)", 0.0), ("funding x1 (base)", 1.0), ("funding x1.5 (worse)", 1.5), ("funding x2", 2.0)]:
    df, r = run(slip_bps=10, fund_mult=m)
    P(f"- {lbl:24s} net={r['net']:9.1f} pf={r['pf']:.2f}")
    res.setdefault("E4", {})[lbl] = dict(net=r["net"], pf=r["pf"])
res["E4"]["interval_h"] = {str(k): int(v) for k, v in iv.items()}
res["E4"]["per_trade_funding_bps"] = float(1e4 * t.funding.mean() / NOT)

# ---------------------------------------------------------------- E5
P("\n## E5 — capacity per event\n")
q = pd.DataFrame({"sym": base_df.instrument, "t": base_df.entry_time,
                  "qv_e": base_df.qv_entry, "qv_x": base_df.qv_exit})
q["cap1"] = q[["qv_e", "qv_x"]].min(axis=1) * 0.01
q["yr"] = q.t.dt.year
P(f"- entry-hour $ volume: median ${q.qv_e.median()/1e6:.1f}M, p25 ${q.qv_e.quantile(.25)/1e6:.1f}M, p05 ${q.qv_e.quantile(.05)/1e6:.2f}M")
P(f"- at 1% of the thinner of the entry/exit hour: median size ${q.cap1.median():,.0f}, p25 ${q.cap1.quantile(.25):,.0f}, p05 ${q.cap1.quantile(.05):,.0f}")
P("- by year (median 1%-of-hour capacity): " + ", ".join(f"{y}: ${v:,.0f}" for y, v in q.groupby('yr').cap1.median().items()))
res["E5"] = dict(median_cap_1pct=float(q.cap1.median()), p25=float(q.cap1.quantile(.25)), p05=float(q.cap1.quantile(.05)),
                 by_year={int(y): float(v) for y, v in q.groupby('yr').cap1.median().items()})
# scaled P&L: size each event at min(target, cap), P&L scales linearly with notional
tt = C.add_pnl(base_df).assign(cap=q.cap1.values)
for target in (1_000, 5_000, 25_000, 100_000, 250_000):
    size = np.minimum(target, tt.cap.values)
    scaled = float((tt.net_pnl.values * size / NOT).sum())
    P(f"- target ${target:,}/event -> realised avg size ${size.mean():,.0f}, OOS net ${scaled:,.0f} "
      f"({scaled/ (bounds[-1][1]-OOS_START).days*30:,.0f}/month)")
    res["E5"].setdefault("scaled", {})[str(target)] = dict(avg_size=float(size.mean()), net=scaled)

# ---------------------------------------------------------------- E6
P("\n## E6 — concurrency, capital and margin\n")
ev_t = base_df.sort_values("entry_time")
grid = pd.date_range(ev_t.entry_time.min(), ev_t.exit_time.max(), freq="1h")
open_n = np.zeros(len(grid), dtype=int)
gi = pd.Series(np.arange(len(grid)), index=grid)
for _, r0 in ev_t.iterrows():
    a, b = gi.index.searchsorted(r0.entry_time), gi.index.searchsorted(r0.exit_time)
    open_n[a:b] += 1
P(f"- concurrent open positions: median {int(np.median(open_n))}, p95 {int(np.percentile(open_n,95))}, max {int(open_n.max())}")
recent = (grid >= pd.Timestamp("2025-01-01", tz="UTC"))
P(f"- since 2025-01: median {int(np.median(open_n[recent]))}, p95 {int(np.percentile(open_n[recent],95))}, max {int(open_n[recent].max())}")
for target in (1_000, 5_000, 25_000):
    peak = int(open_n.max()) * target * 2          # alt short + BTC hedge
    P(f"- at ${target:,}/event: peak gross notional ${peak:,} -> initial margin ${peak/5:,.0f} at 5x, ${peak/3:,.0f} at 3x")
    res.setdefault("E6", {})[str(target)] = dict(peak_gross=peak, margin_5x=peak / 5)
res["E6"]["max_concurrent"] = int(open_n.max()); res["E6"]["median_concurrent"] = int(np.median(open_n))
res["E6"]["max_concurrent_2025plus"] = int(open_n[recent].max())

# ---------------------------------------------------------------- E7 / E8
P("\n## E7/E8 — realistic combined scenario\n")
df10, r10 = run(slip_bps=10)
t10 = C.add_pnl(df10)
by_year = t10.groupby(t10.entry_time.dt.year)["net_pnl"].agg(["sum", "count", "mean"])
P("| year | n | net (10 bps slip) | avg/trade | bps/trade |")
P("|---|---|---|---|---|")
for y, r0 in by_year.iterrows():
    P(f"| {y} | {int(r0['count'])} | {r0['sum']:.1f} | {r0['mean']:.2f} | {1e4*r0['mean']/NOT:.1f} |")
res["E8_by_year_10bps"] = {int(y): dict(n=int(r0["count"]), net=float(r0["sum"]), bps=float(1e4 * r0["mean"] / NOT)) for y, r0 in by_year.iterrows()}
df20, r20 = run(slip_bps=20)
t20 = C.add_pnl(df20)
y26 = t20[t20.entry_time >= Y26]
P(f"\n- at 20 bps/side: total net {r20['net']:.0f} (pf {r20['pf']:.2f}); 2026 alone net {y26.net_pnl.sum():.0f} on n={len(y26)} "
  f"({1e4*y26.net_pnl.mean()/NOT:.1f} bps/trade)")
res["E8_20bps"] = dict(net=r20["net"], pf=r20["pf"], net_2026=float(y26.net_pnl.sum()), n_2026=int(len(y26)))

OUT.write_text(json.dumps(res, indent=1, default=str))
MD.write_text("\n".join(L) + "\n")
print(f"\nwrote {OUT.name} / {MD.name}")
