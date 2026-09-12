"""Hypothesis latpfn_reversal_fade (round 4): fade the repo's LaT-PFN forecaster.

The deployed zero-shot forecaster (forecaster/, lagged context mode) produced
confident counter-trend 'layup' calls that lost badly in the 60-day CME
backtests (MNQ lagged: PF 0.27, layup tier 22% WR).  Is the OPPOSITE side of
its calls a real, fee-adjusted, out-of-sample edge - or is the model usable as a
trend-continuation filter?

Two evidence sources, both NET OF FEES, chronological folds, walk-forward:

PART A - CME mirror test (reports/backtest_*lagged*_2026*.json, MNQ/MES/MYM/MBT,
  context modes 'lagged' and 'lagged-bc', 60 days of 5m bars to 2026-08-26).
  The JSONs carry per-trade direction/confidence/shot_type/entry/exit/pnl but NO
  timestamps; the trades are chronological by construction (backtest.py walks
  forward on a 60-bar cadence), so folds are thirds of trade ORDER per instrument
  (= calendar thirds of the same 60-day window), pooled across instruments.
  A fade trade is the exact MIRROR of the model's trade: same fill, opposite
  side, closed when the model's trade closes (SL/TP/timeout), so its gross P&L
  is -pnl.  Fees: FEES['cme_round_trip'] (commission + 1 tick slippage per
  side) per contract, 1 contract per trade.  Fill caveat: backtest.py fills at
  the CLOSE of the signal bar (not the t+1 open); the 1-tick-per-side slippage
  in the fee model is the only allowance for that.  Because of this the CME
  part is supporting evidence; Part B is the strict test.
  Arms: RAW (model side), INV (mirror every call), INV_LAYUP (mirror layup
  tier only), INV_CONF60 / INV_CONF52 (mirror calls with confidence >= .60 /
  .52), INV_LOW (mirror calls < .52).  Grid = arm x context mode.

PART B - Hyperliquid, exact timestamps, strict causality (signal at the close of
  bar t from the cached forecaster outputs in data/latpfn_preds/, fill at the
  open of bar t+1, hold H bars, taker fees + funding).  Run by
  tests/h_latpfn_reversal_fade_hl.py (1h: 20 coins / 13.7k forecasts; 15m:
  BTC/ETH/SOL fresh forecasts generated for this round).  Its arms include the
  pure inverse (INV/INV_CONF/INV_HI), the trend-filter variants (F_AGREE /
  F_DISAGR) and the fade-when-counter-trend variant (FADE).

Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_latpfn_reversal_fade.py [--no-lab] [--skip-hl]
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

STRATEGY = "latpfn_reversal_fade"
SRC = "tests/h_latpfn_reversal_fade.py"
PY = "/Users/molt_bot/latpfn-trading/venv/bin/python"
REPORTS = Path("/Users/molt_bot/latpfn-trading/reports")

ap = argparse.ArgumentParser()
ap.add_argument("--no-lab", action="store_true")
ap.add_argument("--skip-hl", action="store_true")
ap.add_argument("--hl-intervals", default="1h,15m")
ap.add_argument("--shuffle-reps", type=int, default=2000)
ap.add_argument("--hl-reuse", action="store_true", help="reuse existing tests/h_latpfn_reversal_fade_hl_<tf>.json/.md instead of re-running")
ARGS = ap.parse_args()

lines = []


def say(s=""):
    print(s, flush=True)
    lines.append(s)


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.3f} "
            f"sh={r['sharpe']:6.2f} folds={[round(f, 1) for f in r['folds']]}")


def record(variant, instrument, tf, params, res, notes=None, period=(None, None)):
    if ARGS.no_lab:
        return
    C.record_to_lab(STRATEGY, variant, instrument, tf, params, res, period=period, source=SRC, notes=notes)


# ---------------------------------------------------------------------------
# PART A: CME mirror test
# ---------------------------------------------------------------------------
say("# latpfn_reversal_fade - round 4\n")
say("## Part A - CME mirror test (saved lagged-mode backtests, 60 days of 5m bars to 2026-08-26)\n")

rows = []
for f in sorted(glob.glob(str(REPORTS / "backtest_*lagged*_2026*.json"))):
    d = json.load(open(f))
    inst, mode = d["instrument"], d["context_mode"]
    gen = pd.Timestamp(d["generated_at"]).tz_localize("UTC")
    t_end = gen.floor("D")
    t_start = t_end - pd.Timedelta(days=d["days"])
    tr = d["trades"]
    n = len(tr)
    mult = C.cme_multiplier(inst)
    for k, t in enumerate(tr):
        side = 1 if t["direction"] == "long" else -1
        gross_chk = side * (t["exit_price"] - t["entry_price"]) * mult
        assert abs(gross_chk - t["pnl"]) < 1e-6, (f, k, gross_chk, t["pnl"])
        # pseudo timestamps: trade order is chronological; place trade k in its order-third
        et = t_start + (t_end - t_start) * ((k + 0.5) / n)
        rows.append(dict(instrument=inst, mode=mode, k=k, n_inst=n, order_frac=(k + 0.5) / n,
                         entry_time=et, exit_time=et + pd.Timedelta(hours=5),
                         model_side=side, entry_px=t["entry_price"], exit_px=t["exit_price"],
                         confidence=t["confidence"], tier=t["shot_type"], reason=t["reason"],
                         model_pnl=t["pnl"], multiplier=mult, fee_usd=C.cme_fee(inst, 1)))
A = pd.DataFrame(rows)
A["fold"] = np.clip(np.floor(A["order_frac"] * 3).astype(int), 0, 2)
TA0, TA1 = A["entry_time"].min(), A["entry_time"].max()

say(f"trades loaded: {len(A)}  by mode {A['mode'].value_counts().to_dict()}  by instrument {A['instrument'].value_counts().to_dict()}")
say(f"tiers: {A['tier'].value_counts().to_dict()}  exit reasons: {A['reason'].value_counts().to_dict()}")
say("model (RAW) gross P&L per instrument/mode, as saved:")
g = A.groupby(["mode", "instrument"])["model_pnl"].agg(["count", "sum", lambda x: (x > 0).mean()])
g.columns = ["n", "gross", "wr"]
say(g.round(2).to_string())
say("")
say("model-side hit rate by tier (gross pnl > 0), pooled, and by order-third:")
for tier, gg in A.groupby("tier"):
    by_fold = [f"{(gg[gg.fold == k].model_pnl > 0).mean():.2f}(n={int((gg.fold == k).sum())})" for k in range(3)]
    say(f"- {tier:14s} n={len(gg):3d} wr={(gg.model_pnl > 0).mean():.2f} gross={gg.model_pnl.sum():8.1f} | folds {by_fold}")
say("")


def cme_arm_sides(df: pd.DataFrame, arm: str) -> np.ndarray:
    d = df["model_side"].values
    c = df["confidence"].values
    tier = df["tier"].values
    if arm == "RAW":
        return d
    if arm == "INV":
        return -d
    if arm == "INV_LAYUP":
        return np.where(tier == "layup", -d, 0)
    if arm == "INV_CONF60":
        return np.where(c >= 0.60, -d, 0)
    if arm == "INV_CONF52":
        return np.where(c >= 0.52, -d, 0)
    if arm == "INV_LOW":
        return np.where(c < 0.52, -d, 0)
    if arm == "RAW_LOW":
        return np.where(c < 0.52, d, 0)
    raise ValueError(arm)


def cme_trades(params: dict, sides: np.ndarray | None = None, df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = A if df is None else df
    m = df["mode"].isin(params["modes"]).values
    s = df[m]
    side = cme_arm_sides(s, params["arm"]) if sides is None else sides[m]
    keep = side != 0
    s, side = s[keep], side[keep]
    if len(s) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return pd.DataFrame(dict(entry_time=s["entry_time"].values, exit_time=s["exit_time"].values, side=side,
                             entry_px=s["entry_px"].values, exit_px=s["exit_px"].values, qty=1.0,
                             notional_usd=s["entry_px"].values * s["multiplier"].values,
                             fee_usd=s["fee_usd"].values, instrument=s["instrument"].values,
                             multiplier=s["multiplier"].values, fold=s["fold"].values,
                             tier=s["tier"].values, confidence=s["confidence"].values,
                             reason=s["reason"].values, order_frac=s["order_frac"].values))


def in_fold(t: pd.DataFrame, folds) -> pd.DataFrame:
    if len(t) == 0:
        return t
    return t[t["fold"].isin(folds)].reset_index(drop=True)


def ev(t: pd.DataFrame) -> dict:
    """evaluate() with folds = order-thirds (stored in the 'fold' column)."""
    r = C.evaluate(t, n_folds=3, start=TA0, end=TA1)
    if len(t):
        p = C.add_pnl(t)
        r["folds"] = [float(p.loc[p["fold"] == k, "net_pnl"].sum()) for k in range(3)]
        r["fold_n"] = [int((p["fold"] == k).sum()) for k in range(3)]
        r["fold_consistent"] = all(f > 0 for f in r["folds"])
    return r


ARMS = ["RAW", "INV", "INV_LAYUP", "INV_CONF60", "INV_CONF52", "INV_LOW", "RAW_LOW"]
MODESETS = {"lagged": ["lagged"], "lagged-bc": ["lagged-bc"], "both": ["lagged", "lagged-bc"]}
GRID = [dict(arm=a, modes=ms, modeset=name) for name, ms in MODESETS.items() for a in ARMS]

say("## Part A walk-forward: select on order-third 1 (pooled across instruments), OOS = thirds 2+3\n")
say("| arm | modes | f1 n | f1 net | f1 pf | OOS n | OOS net | OOS pf | OOS wr | f1 | f2 | f3 | sel |")
say("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
table = []
for p in GRID:
    t_all = cme_trades(p)
    r_full = ev(t_all)
    r1 = ev(in_fold(t_all, [0]))
    r_oos = ev(in_fold(t_all, [1, 2]))
    table.append(dict(p=p, f1=r1, oos=r_oos, full=r_full))
    record(f"cme|{p['arm']}|{p['modeset']}|full", "CME_MNQ_MES_MYM_MBT", "5m", dict(arm=p["arm"], modes=p["modeset"], scope="full3fold_orderthirds"),
           r_full, notes=f"CME mirror test, in-sample grid cell; fold1 net={r1['net']:.2f} pf={r1['pf']:.2f}", period=(TA0, TA1))
elig = [x for x in table if x["f1"]["n"] >= 10]
best = max(elig or table, key=lambda x: x["f1"]["net"])
for x in table:
    p, r1, ro, rf = x["p"], x["f1"], x["oos"], x["full"]
    say(f"| {p['arm']} | {p['modeset']} | {r1['n']} | {r1['net']:.1f} | {r1['pf']:.2f} | {ro['n']} | {ro['net']:.1f} | {ro['pf']:.2f} | {ro['wr']:.2f} | "
        f"{rf['folds'][0]:.1f} | {rf['folds'][1]:.1f} | {rf['folds'][2]:.1f} | {'*' if x is best else ''} |")
bp = best["p"]
oos = best["oos"]
oos_t = in_fold(cme_trades(bp), [1, 2])
say("")
say(f"selected on third 1: arm={bp['arm']} modes={bp['modeset']}")
say(f"**Part A OOS (thirds 2+3): {fmt(oos)} bps={oos['net_bps']:.2f}**")
record(f"cme|OOS|{bp['arm']}|{bp['modeset']}", "CME_MNQ_MES_MYM_MBT", "5m", dict(arm=bp["arm"], modes=bp["modeset"], scope="walkforward_oos"), oos,
       notes="WALK-FORWARD OOS order-thirds 2+3, selected on third 1; fold1 empty by construction", period=(TA0, TA1))

say("\n### Part A sanity (selected variant, OOS period)")
# neighbours: every arm on the selected modeset, and selected arm on every modeset
say("neighbours (no reselection):")
for a in ARMS:
    r = ev(in_fold(cme_trades(dict(bp, arm=a)), [1, 2]))
    say(f"- arm={a:10s}: {fmt(r)}")
    record(f"cme|OOSneighbour|{a}|{bp['modeset']}", "CME_MNQ_MES_MYM_MBT", "5m", dict(arm=a, modes=bp["modeset"], scope="oos_neighbour"), r, period=(TA0, TA1))
for name, ms in MODESETS.items():
    r = ev(in_fold(cme_trades(dict(bp, modes=ms, modeset=name)), [1, 2]))
    say(f"- modes={name:9s}: {fmt(r)}")
# per instrument, per tier
if len(oos_t):
    pi = C.add_pnl(oos_t).groupby("instrument")["net_pnl"].agg(["count", "sum", lambda x: (x > 0).mean()])
    pi.columns = ["n", "net", "wr"]
    say("per-instrument OOS:\n" + pi.round(2).to_string())
    say(f"positive instruments: {(pi['net'] > 0).sum()}/{len(pi)}")
    for a in ("INV_LAYUP", "INV"):
        ta = in_fold(cme_trades(dict(bp, arm=a)), [1, 2])
        pa = C.add_pnl(ta).groupby("instrument")["net_pnl"].agg(["count", "sum"]).round(1)
        pr_a = C.add_pnl(ta).groupby("reason")["net_pnl"].agg(["count", "sum"]).round(1)
        say(f"neighbour {a} OOS per-instrument: {pa['sum'].to_dict()} (n {pa['count'].to_dict()}) | by model exit reason: {pr_a['sum'].to_dict()}")
    pt = C.add_pnl(oos_t).groupby("tier")["net_pnl"].agg(["count", "sum", lambda x: (x > 0).mean()])
    pt.columns = ["n", "net", "wr"]
    say("per-tier OOS:\n" + pt.round(2).to_string())
    # exit-reason decomposition: mirror wins when the model was stopped
    pr = C.add_pnl(oos_t).groupby("reason")["net_pnl"].agg(["count", "sum"])
    say("by model exit reason OOS:\n" + pr.round(2).to_string())
    # top-3 removal
    pn = C.add_pnl(oos_t)["net_pnl"].values
    keep = np.sort(np.argsort(-pn)[3:])
    r3 = ev(oos_t.iloc[keep])
    say(f"top-3 removal: net {pn.sum():.1f} -> {r3['net']:.1f} pf {r3['pf']:.2f} folds {[round(f, 1) for f in r3['folds']]}")
    # shuffle: permute model directions within instrument x mode (OOS period) -> the mirror rule applied to random labels
    rng = np.random.default_rng(11)
    A_oos = A[A["fold"].isin([1, 2])]
    nets = []
    for _ in range(ARGS.shuffle_reps):
        Ash = A_oos.copy()
        for _, idx in Ash.groupby(["instrument", "mode"]).indices.items():
            v = Ash["model_side"].values.copy()
            v[idx] = v[idx][rng.permutation(len(idx))]
            Ash["model_side"] = v
        t = cme_trades(bp, df=Ash)
        nets.append(C.evaluate(t)["net"] if len(t) else 0.0)
    nets = np.array(nets)
    p_sh = float((nets >= oos["net"]).mean())
    say(f"shuffle (model sides permuted within instrument x mode, {ARGS.shuffle_reps} reps): actual {oos['net']:.1f}; "
        f"shuffled mean {nets.mean():.1f} sd {nets.std():.1f} p95 {np.percentile(nets, 95):.1f}; P(shuffle >= actual) = {p_sh:.3f}")
    # sign-flip: is the mirror's edge just 'the market drifted against the model's tilt'?  random-sign coin-flip baseline
    nets_c = []
    for _ in range(ARGS.shuffle_reps):
        sides = rng.choice([-1, 1], size=len(A))
        t = cme_trades(bp, sides=sides)
        t = t[t["fold"].isin([1, 2])]
        nets_c.append(C.evaluate(t)["net"] if len(t) else 0.0)
    nets_c = np.array(nets_c)
    say(f"coin-flip sides on the same trades (OOS): mean {nets_c.mean():.1f} sd {nets_c.std():.1f}; P(coinflip >= actual) = {(nets_c >= oos['net']).mean():.3f}")
    # sub-period signs finer: order-sixths
    p6 = C.add_pnl(oos_t)
    A6 = np.clip(np.floor(oos_t["order_frac"].values * 6).astype(int), 0, 5)
    say("order-sixths net (OOS covers sixths 3-6): " + str({int(k): round(float(p6["net_pnl"].values[A6 == k].sum()), 1) for k in range(2, 6)}))
    # dependence on tiny n: the model's own trades per instrument in OOS
    say(f"OOS decisions: {len(oos_t)} mirror trades ({oos_t['instrument'].nunique()} instruments); the same 60 days for every instrument -> "
        f"effective independent periods are far fewer than trades.")
crit_a = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=oos["n"] >= 60, folds=all(f > 0 for f in oos["folds"][1:]))
PARTA = dict(best=dict(arm=bp["arm"], modes=bp["modeset"]), n=oos["n"], net=oos["net"], pf=oos["pf"], wr=oos["wr"],
             sharpe=oos["sharpe"], folds=oos["folds"], criteria=crit_a,
             shuffle_p=p_sh if len(oos_t) else None, top3_net=float(r3["net"]) if len(oos_t) else None,
             top3_folds=r3["folds"] if len(oos_t) else None)
say("\nPart A criteria: " + json.dumps(crit_a))
say("")

# ---------------------------------------------------------------------------
# PART B: Hyperliquid (exact timestamps, t+1 open fills)
# ---------------------------------------------------------------------------
PARTB = {}
if not ARGS.skip_hl:
    for tf in ARGS.hl_intervals.split(","):
        say(f"## Part B - Hyperliquid {tf} (tests/h_latpfn_reversal_fade_hl.py)")
        cmd = [PY, str(ROOT / "tests" / "h_latpfn_reversal_fade_hl.py"), "--interval", tf, "--shuffle-reps", "200"]
        if ARGS.no_lab:
            cmd.append("--no-lab")
        js = ROOT / "tests" / f"h_latpfn_reversal_fade_hl_{tf}.json"
        if not (ARGS.hl_reuse and js.exists()):
            res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            if res.returncode != 0:
                say(f"HL {tf} run failed:\n{res.stderr[-2000:]}")
                continue
        PARTB[tf] = json.loads(js.read_text())
        md = (ROOT / "tests" / f"h_latpfn_reversal_fade_hl_{tf}.md").read_text().splitlines()
        # pull the key lines into this report
        keep_prefix = ("Forecasts:", "Period", "selected on fold 1", "OOS (folds 2+3)", "- arm=", "shuffle", "random-bar",
                       "top-3", "positive coins", "## Walk-forward", "### Sanity", "- H=", "secondary [", "  shuffle", "  by side")
        for l in md:
            if l.startswith(keep_prefix):
                say(l)
        say(f"full HL {tf} report: tests/h_latpfn_reversal_fade_hl_{tf}.md")
        say("")

# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------
summary = dict(partA_cme=PARTA, partB_hl=PARTB)
say("## Summary")
say("```")
say(json.dumps(summary, indent=1, default=str))
say("```")
(ROOT / "tests" / "h_latpfn_reversal_fade.md").write_text("\n".join(lines))
(ROOT / "tests" / "h_latpfn_reversal_fade_result.json").write_text(json.dumps(summary, indent=1, default=str))
print("written", ROOT / "tests" / "h_latpfn_reversal_fade.md")
