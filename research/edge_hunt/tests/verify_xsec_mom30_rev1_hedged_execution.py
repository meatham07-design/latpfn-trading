"""Execution-realism verification of h_xsec_mom30_rev1_hedged (adversarial review).

Re-runs the author's exact strategy code (imported, not edited) with the fill
function replaced by friction variants:
  * slippage of s bps per side on every fill (longs + BTC hedge adjustments)
  * latency: fill at the 00:00 bar CLOSE (1h late) / bar midpoint / worst-of-bar
  * realized-only: drop positions still open at the end of the sample
For each variant: OOS (folds 2+3) of the author's selected arm, plus a fresh
fold-1 walk-forward re-selection over the author's 16-arm grid.
Also snapshots current HL L2 books of the OOS names to calibrate spreads.
Everything is recorded to quant-lab (project edge-hunt).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import common as C  # noqa: E402
import h_xsec_mom30_rev1_hedged as M  # noqa: E402  (runs the author's panel load)

OUT_JSON = ROOT / "tests" / "verify_xsec_mom30_rev1_hedged_execution.json"
SRC = Path(__file__).name
STRATEGY = M.STRATEGY
BEST = dict(rebal_d=7, quantile=0.2, hedge=1, exec="taker", signal="combo")
BOUNDS = C.fold_bounds(M.PERIOD, 3)
OOS_PERIOD = (BOUNDS[1][0], BOUNDS[2][1])
P = M.P

CFG = dict(fill="open", slip_bps=0.0)


def fill_patched(i, j, side, mode):
    """Replacement for the author's fill(): same semantics for mode, then apply
    the friction configured in CFG."""
    o, h, lo, cl = P["O"][i, j], P["H"][i, j], P["Lo"][i, j], P["Cl"][i, j]
    f = CFG["fill"]
    if mode == "taker" or f != "open":
        if f == "open":
            px, mk = o, False
        elif f == "close1h":          # 1h latency: fill at the 00:00 bar close
            px, mk = cl, False
        elif f == "mid":              # intrabar midpoint (VWAP-ish proxy)
            px, mk = 0.5 * (h + lo), False
        elif f == "worst":            # buy the bar high / sell the bar low
            px, mk = (h if side > 0 else lo), False
        else:
            raise ValueError(f)
    else:                              # maker_fb, author's logic
        through = lo < o if side > 0 else h > o
        px, mk = (o, True) if through else (cl, False)
    if np.isfinite(px) and CFG["slip_bps"] and not mk:
        px = px * (1.0 + side * CFG["slip_bps"] / 1e4)
    return px, mk


M.fill = fill_patched   # build_trades/_close_long/_open_hedge/_roll_hedge look this up by name


def run(params, cfg):
    CFG.update(cfg)
    p = dict(params, _verify=json.dumps(cfg, sort_keys=True))   # unique cache key
    return M.run_fn(p, *BOUNDS[1]), M.run_fn(p, *BOUNDS[2]), p


def oos_of(params, cfg, realized_only=False):
    a, b, _ = run(params, cfg)
    tr = pd.concat([a, b])
    if realized_only and len(tr):
        tr = tr[tr["exit_time"] < M.DAY_OPENS[-1]]
    return C.oos_result(tr, M.PERIOD, 3), tr


def wf_reselect(cfg):
    CFG.update(cfg)
    grid = [dict(g, _verify=json.dumps(cfg, sort_keys=True)) for g in M.GRID]
    best, oos_tr, table = C.walk_forward(grid, M.run_fn, M.PERIOD, n_folds=3, min_trades=10)
    best = {k: v for k, v in best.items() if not k.startswith("_")}
    return best, C.oos_result(oos_tr, M.PERIOD, 3), table


def fmt(r):
    return (f"n={r['n']:3d} net={r['net']:8.1f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"fees={r['fees']:.1f} f2={r['folds'][1]:.1f} f3={r['folds'][2]:.1f}")


def l2_spreads(coins):
    """Current HL L2 books (public read-only) -> spread bps and depth within 10 bps."""
    out = {}
    s = requests.Session()
    for c in coins:
        try:
            r = s.post(C.HL_INFO_URL, json={"type": "l2Book", "coin": c}, timeout=20)
            r.raise_for_status()
            lv = r.json()["levels"]
            bid = float(lv[0][0]["px"]); ask = float(lv[1][0]["px"]); mid = 0.5 * (bid + ask)
            sp = (ask - bid) / mid * 1e4
            def depth(side, lim):
                return sum(float(x["px"]) * float(x["sz"]) for x in side if abs(float(x["px"]) / mid - 1) * 1e4 <= lim)
            out[c] = dict(spread_bps=sp, bid_depth10=depth(lv[0], 10), ask_depth10=depth(lv[1], 10))
        except Exception as e:  # noqa: BLE001
            out[c] = dict(error=repr(e))
        time.sleep(0.25)
    return out


def main():
    res = {}
    base, base_tr = oos_of(BEST, dict(fill="open", slip_bps=0.0))
    print("REPRODUCE author's headline:", fmt(base))
    assert abs(base["net"] - 3737.66) < 1.0, base["net"]
    res["base"] = base

    # --- realized vs still-open (marked at the last 00:00 bar) --------------------
    t = C.add_pnl(base_tr)
    still_open = t[t["exit_time"] >= M.DAY_OPENS[-1]]
    realized, _ = oos_of(BEST, dict(fill="open", slip_bps=0.0), realized_only=True)
    print(f"\nSTILL-OPEN at sample end ({M.DAY_OPENS[-1].date()}): n={len(still_open)} "
          f"net={still_open['net_pnl'].sum():.1f} of OOS {base['net']:.1f}")
    print(still_open[["instrument", "leg", "entry_time", "net_pnl"]].sort_values("net_pnl").round(1).to_string(index=False))
    print("REALIZED-ONLY OOS:", fmt(realized))
    res["still_open_net"] = float(still_open["net_pnl"].sum()); res["still_open_n"] = int(len(still_open))
    res["realized_only"] = realized
    C.record_to_lab(STRATEGY, "VERIFY_EXEC_realized_only_" + M.pname(BEST), "HL_XSEC_PIT", "7d",
                    dict(BEST, verify="realized_only"), realized, period=OOS_PERIOD, source=SRC,
                    notes=f"drop positions still open at sample end (n={len(still_open)}, mtm={still_open['net_pnl'].sum():.1f})")

    # --- friction variants on the selected arm ---------------------------------------
    variants = [("open", 0.0), ("open", 2.0), ("open", 5.0), ("open", 10.0), ("open", 20.0),
                ("close1h", 0.0), ("close1h", 5.0), ("mid", 0.0), ("mid", 5.0), ("worst", 0.0)]
    rows = []
    print("\nFRICTION VARIANTS on the selected arm (OOS folds 2+3):")
    for f, s in variants:
        cfg = dict(fill=f, slip_bps=s)
        r, tr = oos_of(BEST, cfg)
        rr, _ = oos_of(BEST, cfg, realized_only=True)
        lg = tr[tr["leg"] == "long"]
        lg_net = C.evaluate(lg, 1)["net"] if len(lg) else 0.0
        rows.append(dict(fill=f, slip_bps=s, n=r["n"], net=r["net"], pf=r["pf"], f2=r["folds"][1], f3=r["folds"][2],
                         fees=r["fees"], long_net=lg_net, realized_net=rr["net"], realized_n=rr["n"]))
        print(f"  fill={f:8s} slip={s:4.1f}bps  {fmt(r)}  long_net={lg_net:.1f}  realized_only_net={rr['net']:.1f}")
        C.record_to_lab(STRATEGY, f"VERIFY_EXEC_fill-{f}_slip{s:g}_" + M.pname(BEST), "HL_XSEC_PIT", "7d",
                        dict(BEST, verify_fill=f, verify_slip_bps=s), r, period=OOS_PERIOD, source=SRC,
                        notes=f"execution verify: fill={f} slip={s}bps/side on all fills; realized_only_net={rr['net']:.1f}")
    res["variants"] = rows

    # --- walk-forward re-selection under frictions ---------------------------------
    print("\nWALK-FORWARD RE-SELECTION (fold-1 pick over the author's 16 arms) under frictions:")
    wf = []
    for f, s in [("open", 0.0), ("open", 5.0), ("open", 10.0), ("close1h", 0.0), ("close1h", 5.0), ("mid", 5.0)]:
        best, o, table = wf_reselect(dict(fill=f, slip_bps=s))
        wf.append(dict(fill=f, slip_bps=s, best=M.pname(best), oos_n=o["n"], oos_net=o["net"], oos_pf=o["pf"],
                       f2=o["folds"][1], f3=o["folds"][2]))
        print(f"  fill={f:8s} slip={s:4.1f}  best={M.pname(best):28s} {fmt(o)}")
        C.record_to_lab(STRATEGY, f"VERIFY_EXEC_WF_fill-{f}_slip{s:g}", "HL_XSEC_PIT", f"{best['rebal_d']}d",
                        dict(best, verify_fill=f, verify_slip_bps=s), o, period=OOS_PERIOD, source=SRC,
                        notes="walk-forward re-selected under execution frictions; OOS folds 2+3")
    res["wf"] = wf

    # --- per-rebalance t-stat under 1h latency ----------------------------------------
    _, tr_lat = oos_of(BEST, dict(fill="close1h", slip_bps=5.0))
    tl = C.add_pnl(tr_lat)
    wk = tl.groupby(tl["entry_time"].dt.floor("D"))["net_pnl"].sum()
    tstat = float(wk.mean() / wk.std() * np.sqrt(len(wk))) if len(wk) > 1 else 0.0
    print(f"\nper-rebalance book PnL (close1h+5bps): n={len(wk)} mean={wk.mean():.1f} sd={wk.std():.1f} t={tstat:.2f} pos={(wk > 0).sum()}/{len(wk)}")
    res["latency_tstat"] = tstat

    # --- current L2 spreads of the OOS names -----------------------------------------
    names = sorted(set(base_tr["instrument"]))
    sp = l2_spreads(names)
    df = pd.DataFrame(sp).T
    if "spread_bps" in df:
        df = df.sort_values("spread_bps", ascending=False)
        print("\nCURRENT HL L2 (public snapshot) for OOS names - spread bps / USD depth within 10 bps:")
        print(df.round(1).to_string())
        ok = df["spread_bps"].dropna()
        print(f"spread bps: median={ok.median():.1f} mean={ok.mean():.1f} max={ok.max():.1f}; "
              f"min depth10 USD = {df[['bid_depth10','ask_depth10']].min().min():.0f}")
        res["l2_spread_median_bps"] = float(ok.median()); res["l2_spread_max_bps"] = float(ok.max())
    res["l2"] = sp
    OUT_JSON.write_text(json.dumps(res, default=str, indent=1))
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
