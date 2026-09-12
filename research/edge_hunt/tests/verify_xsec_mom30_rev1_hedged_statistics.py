"""Statistics-lens verification of key=xsec_mom30_rev1_hedged.

Does NOT edit the author's script; imports it as a module (its panel / mask
are built at import time) and re-uses build_trades / run_fn.

Checks:
  1. reproduce the walk-forward headline
  2. bootstrap p-values (10k): trade-level, per-rebalance-decision level and
     weekly mark-to-market book level (the latter two are the honest units,
     trades inside one rebalance are not independent)
  3. concentration: ex-top-1/3 trades, per-fold and per-month sign
  4. shuffle control with 1000 (not 40) random buckets
  5. parameter neighbours OUTSIDE the searched grid: signal lookbacks
     L_MOM in {14,20,30,45,60} x L_REV in {1,2,3} at the selected structure
  6. weekly-anchor phase distribution (7 equally valid anchors)
  7. hidden multiple comparisons: round-1 (h_xsec_momentum) searched
     lookback {1,7,30} x mom/rev on the same folds; its two best OOS cells are
     the two components of this round-2 signal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import common as C  # noqa: E402
import h_xsec_mom30_rev1_hedged as M  # noqa: E402  (builds the panel at import)

OUT_JSON = ROOT / "tests" / "verify_xsec_mom30_rev1_hedged_statistics.json"
SRC = Path(__file__).name
STRATEGY = M.STRATEGY
NB = 10_000
rng = np.random.default_rng(2024)

BEST = dict(rebal_d=7, quantile=0.2, hedge=1, exec="taker", signal="combo")
PERIOD = M.PERIOD
bounds = C.fold_bounds(PERIOD, 3)
OOS_PERIOD = (bounds[1][0], bounds[2][1])


def oos_trades(params):
    return pd.concat([M.run_fn(params, *bounds[1]), M.run_fn(params, *bounds[2])], ignore_index=True)


def boot_p(x, nb=NB):
    """P(bootstrap mean <= 0) for the sum/mean of x (one-sided, H1: mean > 0)."""
    x = np.asarray(x, float)
    if len(x) == 0:
        return 1.0, (0.0, 0.0)
    idx = rng.integers(0, len(x), size=(nb, len(x)))
    sums = x[idx].sum(axis=1)
    return float((sums <= 0).mean()), (float(np.percentile(sums, 2.5)), float(np.percentile(sums, 97.5)))


def block_boot_p(x, block=4, nb=NB):
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return 1.0
    nblk = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(nb, nblk))
    sums = np.zeros(nb)
    for b in range(nblk):
        for k in range(block):
            sums += x[(starts[:, b] + k) % n]
    # scale to n observations
    sums *= n / (nblk * block)
    return float((sums <= 0).mean())


def weekly_mtm(tr, R=7):
    """Mark-to-market book PnL per rebalance interval (using the 00:00 opens)."""
    dO = M.DAY_OPENS
    O = M.P["O"]
    grid_i = list(range(0, len(dO), R))
    if grid_i[-1] != len(dO) - 1:
        grid_i.append(len(dO) - 1)
    edges = [dO[i] for i in grid_i]
    pnl = pd.Series(0.0, index=pd.DatetimeIndex(edges[:-1]))
    for _, r in tr.iterrows():
        j = M.CIDX[r["instrument"]]
        side, qty = float(r["side"]), float(r["qty"])
        for k in range(len(edges) - 1):
            a, b = edges[k], edges[k + 1]
            if r["exit_time"] <= a or r["entry_time"] >= b:
                continue
            pa = r["entry_px"] if r["entry_time"] >= a else O[grid_i[k], j]
            pb = r["exit_px"] if r["exit_time"] <= b else O[grid_i[k + 1], j]
            if not (np.isfinite(pa) and np.isfinite(pb)):
                continue
            pnl.iloc[k] += side * qty * (pb - pa)
            if r["exit_time"] <= b:
                pnl.iloc[k] -= abs(float(r["fee_usd"]))
    return pnl


def main():
    res = {}
    # ---------------------------------------------------------------- 1. reproduce
    best, oos_tr, table = C.walk_forward(M.GRID, M.run_fn, PERIOD, n_folds=3, min_trades=10)
    oos = C.oos_result(oos_tr, PERIOD, 3)
    print("reproduced best:", best, "\nOOS:", M.fmt(oos))
    assert best == BEST, best
    t = C.add_pnl(oos_tr)
    lg = t[t["leg"] == "long"].copy()
    hd = t[t["leg"] == "hedge"].copy()
    res["headline"] = dict(n=oos["n"], net=oos["net"], pf=oos["pf"], folds=oos["folds"],
                           n_long=int(len(lg)), long_net=float(lg["net_pnl"].sum()), hedge_net=float(hd["net_pnl"].sum()))

    # all 16 grid cells OOS: how many are positive?  (fold-3 alt beta check)
    cells = []
    for p in M.GRID:
        o = C.oos_result(oos_trades(p), PERIOD, 3)
        cells.append(dict(name=M.pname(p), oos_net=o["net"], f2=o["folds"][1], f3=o["folds"][2]))
    cells = pd.DataFrame(cells)
    res["grid_cells_oos_pos"] = int((cells["oos_net"] > 0).sum())
    res["grid_cells_f2_pos"] = int((cells["f2"] > 0).sum())
    res["grid_cells_f3_pos"] = int((cells["f3"] > 0).sum())
    print(f"\ngrid cells with OOS>0: {res['grid_cells_oos_pos']}/16, fold2>0: {res['grid_cells_f2_pos']}/16, "
          f"fold3>0: {res['grid_cells_f3_pos']}/16")

    # ---------------------------------------------------------------- 2. bootstraps
    p_trade, ci_trade = boot_p(t["net_pnl"].values)
    p_long, ci_long = boot_p(lg["net_pnl"].values)
    dec = t.groupby(t["entry_time"].dt.floor("D"))["net_pnl"].sum()          # per rebalance decision
    p_dec, ci_dec = boot_p(dec.values)
    wk = weekly_mtm(t, R=7)
    wk = wk[(wk.index >= OOS_PERIOD[0])]
    p_wk, ci_wk = boot_p(wk.values)
    p_wk_block = block_boot_p(wk.values, block=4)
    t_wk = float(wk.mean() / wk.std(ddof=1) * np.sqrt(len(wk))) if wk.std(ddof=1) > 0 else 0.0
    t_dec = float(dec.mean() / dec.std(ddof=1) * np.sqrt(len(dec))) if dec.std(ddof=1) > 0 else 0.0
    print(f"\nBOOTSTRAP (10k): trade-level p={p_trade:.4f} CI={np.round(ci_trade,0)}; long-only p={p_long:.4f}; "
          f"per-decision n={len(dec)} t={t_dec:.2f} p={p_dec:.4f} CI={np.round(ci_dec,0)}; "
          f"weekly MTM n={len(wk)} sum={wk.sum():.1f} t={t_wk:.2f} p={p_wk:.4f} block-p={p_wk_block:.4f} CI={np.round(ci_wk,0)}")
    print("weekly MTM:", wk.round(0).to_dict())
    res["bootstrap"] = dict(p_trade=p_trade, ci_trade=ci_trade, p_long=p_long, n_dec=int(len(dec)), t_dec=t_dec,
                            p_dec=p_dec, ci_dec=ci_dec, n_wk=int(len(wk)), wk_sum=float(wk.sum()), t_wk=t_wk,
                            p_wk=p_wk, p_wk_block=p_wk_block, ci_wk=ci_wk, wk_pos=int((wk > 0).sum()))

    # ---------------------------------------------------------------- 3. concentration
    s = np.sort(t["net_pnl"].values)
    top3 = lg.nlargest(3, "net_pnl")[["instrument", "entry_time", "exit_time", "net_pnl", "vol24_entry"]]
    ex1 = t.drop(lg["net_pnl"].idxmax())
    ex3 = t.drop(top3.index)
    r_ex3 = C.oos_result(ex3, PERIOD, 3)
    p_ex3, _ = boot_p(ex3["net_pnl"].values)
    dec_ex3 = ex3.groupby(ex3["entry_time"].dt.floor("D"))["net_pnl"].sum()
    p_dec_ex3, _ = boot_p(dec_ex3.values)
    wk_ex3 = weekly_mtm(ex3, 7); wk_ex3 = wk_ex3[wk_ex3.index >= OOS_PERIOD[0]]
    p_wk_ex3, _ = boot_p(wk_ex3.values)
    print("\nTOP-3 long trades:\n", top3.to_string())
    print(f"ex-top1 net={ex1['net_pnl'].sum():.1f}; ex-top3 net={r_ex3['net']:.1f} folds={np.round(r_ex3['folds'],1)} "
          f"pf={r_ex3['pf']:.2f} p_trade={p_ex3:.3f} p_dec={p_dec_ex3:.3f} p_wk={p_wk_ex3:.3f}")
    share_top3 = float(top3["net_pnl"].sum() / oos["net"])
    # per-fold / per-month sign (by entry month and by MTM week month)
    mon_entry = t.groupby(t["entry_time"].dt.to_period("M"))["net_pnl"].sum()
    mon_mtm = wk.groupby(wk.index.to_period("M")).sum()
    print("per-month (entry):", mon_entry.round(0).to_dict())
    print("per-month (MTM):  ", mon_mtm.round(0).to_dict())
    res["concentration"] = dict(top3=top3.assign(entry_time=top3["entry_time"].astype(str), exit_time=top3["exit_time"].astype(str)).to_dict("records"),
                                share_top3=share_top3, ex1_net=float(ex1["net_pnl"].sum()), ex3_net=r_ex3["net"],
                                ex3_folds=r_ex3["folds"], ex3_pf=r_ex3["pf"], p_ex3_trade=p_ex3, p_ex3_dec=p_dec_ex3, p_ex3_wk=p_wk_ex3,
                                months_entry={str(k): float(v) for k, v in mon_entry.items()},
                                months_mtm={str(k): float(v) for k, v in mon_mtm.items()},
                                months_mtm_pos=int((mon_mtm > 0).sum()), months_mtm_n=int(len(mon_mtm)))
    C.record_to_lab(STRATEGY, "VERIFY_STATS_extop3_" + M.pname(BEST), "HL_XSEC_PIT", "7d", dict(BEST, drop="top3"), r_ex3,
                    period=OOS_PERIOD, source=SRC, notes="statistics verify: OOS with the 3 largest long trades removed")

    # ---------------------------------------------------------------- 4. shuffle x1000
    NSH = 1000
    sh = np.empty(NSH); sh_ex3 = np.empty(NSH)
    for k in range(NSH):
        ps = dict(BEST, _shuffle=1000 + k)
        tr = oos_trades(ps)
        if len(tr) == 0:
            sh[k] = 0.0; sh_ex3[k] = 0.0; continue
        x = C.add_pnl(tr)["net_pnl"].values
        sh[k] = x.sum(); sh_ex3[k] = np.sort(x)[:-3].sum()
        M._CACHE.pop(json.dumps(ps, sort_keys=True), None)
    p_sh = float((sh >= oos["net"]).mean())
    p_sh_ex3 = float((sh_ex3 >= r_ex3["net"]).mean())
    print(f"\nSHUFFLE x{NSH}: mean={sh.mean():.1f} sd={sh.std():.1f} p95={np.percentile(sh,95):.0f} p99={np.percentile(sh,99):.0f} "
          f"max={sh.max():.0f} P(>=real {oos['net']:.0f})={p_sh:.4f}; ex-top3: shuffle mean={sh_ex3.mean():.0f} "
          f"P(>= real ex-top3 {r_ex3['net']:.0f})={p_sh_ex3:.3f}")
    res["shuffle"] = dict(n=NSH, mean=float(sh.mean()), sd=float(sh.std()), p95=float(np.percentile(sh, 95)),
                          p99=float(np.percentile(sh, 99)), max=float(sh.max()), p=p_sh, p_ex3=p_sh_ex3,
                          ex3_mean=float(sh_ex3.mean()))
    C.record_to_lab(STRATEGY, "VERIFY_STATS_shuffle1000_" + M.pname(BEST), "HL_XSEC_PIT", "7d", dict(BEST, shuffle="mean_of_1000"),
                    dict(C.empty_result(), n=int(oos["n"]), net=float(sh.mean())), period=OOS_PERIOD, source=SRC,
                    notes=f"statistics verify: 1000 random buckets sd={sh.std():.0f} p95={np.percentile(sh,95):.0f} P(>=real)={p_sh:.4f}")

    # ---------------------------------------------------------------- 5. lookback neighbours (outside the grid)
    d_close = M.P["d_close"]; days = M.P["days"]
    base_mom, base_rev, base_mask = M.P["ret_mom"], M.P["ret_rev"], M.MASK
    lb_rows = []
    for Lm in (14, 20, 30, 45, 60):
        for Lr in (1, 2, 3):
            M.P["ret_mom"] = (d_close / d_close.shift(Lm) - 1.0).reindex(days).values
            M.P["ret_rev"] = (d_close / d_close.shift(Lr) - 1.0).reindex(days).values
            M.MASK = M.universe_mask(M.P)
            M._CACHE.clear()
            p = dict(BEST, _lm=Lm, _lr=Lr)
            full = C.evaluate(M.build_trades(p)[0], 3, *PERIOD)
            o = C.oos_result(oos_trades(p), PERIOD, 3)
            lb_rows.append(dict(L_mom=Lm, L_rev=Lr, f1=full["folds"][0], oos_net=o["net"], oos_pf=o["pf"], f2=o["folds"][1], f3=o["folds"][2], n=o["n"]))
            C.record_to_lab(STRATEGY, f"VERIFY_STATS_lb{Lm}_{Lr}_" + M.pname(BEST), "HL_XSEC_PIT", "7d", p, o, period=OOS_PERIOD,
                            source=SRC, notes=f"statistics verify: lookback neighbour L_mom={Lm} L_rev={Lr}, OOS folds 2+3; fold1={full['folds'][0]:.0f}")
    M.P["ret_mom"], M.P["ret_rev"], M.MASK = base_mom, base_rev, base_mask
    M._CACHE.clear()
    lb = pd.DataFrame(lb_rows)
    print("\nLOOKBACK NEIGHBOURS (selected structure R7 q0.2 hedged taker):\n", lb.round(0).to_string(index=False))
    res["lookback"] = dict(rows=lb.to_dict("records"), pos=int((lb["oos_net"] > 0).sum()), n=int(len(lb)),
                           median=float(lb["oos_net"].median()), mean=float(lb["oos_net"].mean()),
                           rank_of_30_1=int((lb["oos_net"] > lb[(lb.L_mom == 30) & (lb.L_rev == 1)]["oos_net"].iloc[0]).sum() + 1),
                           both_folds_pos=int(((lb["f2"] > 0) & (lb["f3"] > 0)).sum()))

    # ---------------------------------------------------------------- 6. phases
    ph = []
    for k in range(7):
        o = C.oos_result(oos_trades(dict(BEST, _phase=k)), PERIOD, 3)
        ph.append(o["net"])
    ph = np.array(ph)
    print(f"\nPHASES OOS nets: {np.round(ph,0)} mean={ph.mean():.0f} median={np.median(ph):.0f} selected(phase0) rank={int((ph > ph[0]).sum())+1}/7")
    res["phase"] = dict(nets=ph.tolist(), mean=float(ph.mean()), median=float(np.median(ph)))

    # ---------------------------------------------------------------- 7. hidden multiple comparisons
    r1 = ROOT / "tests" / "h_xsec_momentum.md"
    r1_note = ("round-1 h_xsec_momentum searched lookback {1,7,30} x rebal {1,7} x q {0.1,0.2} x {mom,rev} = 24 cells on the SAME folds; "
               "best OOS cells there: L1_R7_q0.2_rev +5022 and L30_R7_q0.2_mom +2239 -> round-2 signal = z(30d mom) - z(1d) at R7/q0.2 "
               "was composed from the two best round-1 OOS cells, so folds 2+3 are not out-of-sample for the hypothesis choice.")
    res["hidden_search"] = dict(round1_exists=r1.exists(), note=r1_note, grid_cells=len(M.GRID), arms=16, phases=7,
                                edge_hunt_strategies=14, edge_hunt_lab_runs=1266)

    # ---------------------------------------------------------------- corrected numbers
    corrected = dict(phase_mean=float(ph.mean()), lookback_median=float(lb["oos_net"].median()), ex_top3=r_ex3["net"])
    res["corrected"] = corrected
    print("\nCORRECTED candidates:", corrected)
    OUT_JSON.write_text(json.dumps(res, default=str, indent=1))
    print("wrote", OUT_JSON)
    return res


if __name__ == "__main__":
    main()
