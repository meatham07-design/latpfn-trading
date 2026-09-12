"""Adversarial statistics check of h_mean_reversion_zscore (1h walk-forward OOS).

Reuses the author's simulate()/all_trades() unchanged (imported), so trade
mechanics and fees are identical. Adds:
  * iid bootstrap (10k) of OOS trade PnL -> P(net<=0)
  * cluster bootstrap by entry hour and by entry day (trades across 50 coins
    fire on the same bar and are correlated)
  * remove top-3 / top-5 trades, best day, best week
  * per-fold, per-month, per-week sign
  * fine parameter neighbourhood (OOS window, no re-selection)
  * multiple-comparison accounting: 9 grid cells x 2 timeframes, plus the
    OOS distribution over all 9 cells
Writes a JSON next to this file and records variants to quant-lab.
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import common as C
import h_mean_reversion_zscore as H

SRC = "research/edge_hunt/tests/verify_mean_reversion_zscore_statistics.py"
STRAT = "mean_reversion_zscore"
TF = "1h"
BEST = dict(K=2, thr=3.0, H=4, tgt=0.5, vol_filter=1.0)
OUT = {}

coins = C.list_hl_coins()
lo = min(H.bars(c, TF).index.min() for c in coins)
hi = max(H.bars(c, TF).index.max() for c in coins)
times = (lo, hi)
bounds = C.fold_bounds(times, 3)
oos_s, oos_e = bounds[1][0], bounds[-1][1]
print("fold bounds", [(str(a.date()), str(b.date())) for a, b in bounds])

def ev(tr):
    return C.evaluate(tr, 3, start=lo, end=hi)

def oos_trades(p):
    return H.in_window(H.all_trades(TF, p, coins), oos_s, oos_e)

# ---- 1. reproduce headline -------------------------------------------------
oos = oos_trades(BEST)
r0 = ev(oos)
print("REPRO OOS:", H.fmt(r0))
OUT["repro"] = dict(n=r0["n"], net=r0["net"], pf=r0["pf"], folds=r0["folds"], sharpe=r0["sharpe"])
t = C.add_pnl(oos)
pnl = t["net_pnl"].values
n = len(pnl)

# ---- 2. iid bootstrap + t-test --------------------------------------------
rng = np.random.default_rng(0)
boot = rng.choice(pnl, size=(10000, n), replace=True).sum(axis=1)
p_iid = float((boot <= 0).mean())
ci = np.percentile(boot, [2.5, 97.5])
tstat, p_t = stats.ttest_1samp(pnl, 0.0)
print(f"iid bootstrap: P(net<=0)={p_iid:.4f}  95%CI=[{ci[0]:.0f},{ci[1]:.0f}]  t={tstat:.2f} p_one_sided={p_t/2:.4f}")
OUT["boot_iid"] = dict(p_net_le_0=p_iid, ci95=[float(ci[0]), float(ci[1])], t=float(tstat), p_one_sided=float(p_t / 2),
                       mean_per_trade=float(pnl.mean()), sd_per_trade=float(pnl.std(ddof=1)))

# ---- 3. cluster bootstrap (entry hour / entry day / entry week) -----------
def cluster_boot(keys, label):
    g = pd.Series(pnl).groupby(keys).sum()
    vals = g.values; m = len(vals)
    b = rng.choice(vals, size=(10000, m), replace=True).sum(axis=1)
    p = float((b <= 0).mean())
    ts, pt = stats.ttest_1samp(vals, 0.0)
    print(f"cluster[{label}]: clusters={m} P(net<=0)={p:.4f} t={ts:.2f} p1s={pt/2:.4f} "
          f"share positive clusters={(vals>0).mean():.2f}")
    return dict(n_clusters=int(m), p_net_le_0=p, t=float(ts), p_one_sided=float(pt / 2),
                frac_pos=float((vals > 0).mean()))
et = t["entry_time"]
OUT["boot_hour"] = cluster_boot(et.dt.floor("h").values, "entry hour")
OUT["boot_day"] = cluster_boot(et.dt.floor("D").values, "entry day")
OUT["boot_week"] = cluster_boot(et.dt.to_period("W").astype(str).values, "entry week")
# concurrency: how many trades share an entry hour
conc = t.groupby(et.dt.floor("h")).size()
print(f"entries per hour: mean={conc.mean():.2f} max={conc.max()} p90={conc.quantile(.9):.0f}; distinct hours={len(conc)}")
OUT["concurrency"] = dict(mean=float(conc.mean()), max=int(conc.max()), distinct_hours=int(len(conc)))

# ---- 4. trimming -----------------------------------------------------------
srt = np.sort(pnl)[::-1]
for k in (3, 5, 10):
    OUT[f"drop_top{k}"] = float(pnl.sum() - srt[:k].sum())
    print(f"drop top {k} trades: net={OUT[f'drop_top{k}']:.1f}  (top{k} sum={srt[:k].sum():.1f})")
OUT["top5_trades"] = srt[:5].tolist(); OUT["bottom5_trades"] = srt[-5:].tolist()
by_day = t.groupby(et.dt.floor("D"))["net_pnl"].sum().sort_values(ascending=False)
by_week = t.groupby(et.dt.to_period("W"))["net_pnl"].sum().sort_values(ascending=False)
by_month = t.groupby(et.dt.to_period("M"))["net_pnl"].agg(["sum", "count"])
OUT["drop_best_day"] = float(pnl.sum() - by_day.iloc[0]); OUT["best_day"] = [str(by_day.index[0].date()), float(by_day.iloc[0])]
OUT["drop_best_week"] = float(pnl.sum() - by_week.iloc[0]); OUT["best_week"] = [str(by_week.index[0]), float(by_week.iloc[0])]
OUT["drop_best_2days"] = float(pnl.sum() - by_day.iloc[:2].sum())
print(f"best day {by_day.index[0].date()} = {by_day.iloc[0]:.1f}; net w/o it {OUT['drop_best_day']:.1f}; w/o best 2 days {OUT['drop_best_2days']:.1f}")
print(f"best week {by_week.index[0]} = {by_week.iloc[0]:.1f}; net w/o it {OUT['drop_best_week']:.1f}")
print("per-month:\n", by_month.to_string())
print(f"weeks positive: {(by_week>0).sum()}/{len(by_week)}; days positive: {(by_day>0).sum()}/{len(by_day)}")
OUT["per_month"] = {str(k): [float(v["sum"]), int(v["count"])] for k, v in by_month.iterrows()}
OUT["weeks_pos"] = [int((by_week > 0).sum()), int(len(by_week))]
OUT["days_pos"] = [int((by_day > 0).sum()), int(len(by_day))]

# per-coin: drop best 3 coins
by_coin = t.groupby("instrument")["net_pnl"].sum().sort_values(ascending=False)
OUT["drop_best3_coins"] = float(pnl.sum() - by_coin.iloc[:3].sum())
OUT["coins_pos"] = [int((by_coin > 0).sum()), int(len(by_coin))]
print(f"drop best 3 coins net={OUT['drop_best3_coins']:.1f}; coins positive {OUT['coins_pos']}")

# long vs short
for s in (1, -1):
    sub = t[t["side"] == s]
    print(f"side {s:+d}: n={len(sub)} net={sub['net_pnl'].sum():.1f}")
    OUT[f"side_{s:+d}"] = [int(len(sub)), float(sub["net_pnl"].sum())]

# ---- 5. multiple comparisons: OOS over all 9 grid cells --------------------
grid = [dict(K=K, thr=thr, H=4, tgt=0.5, vol_filter=1.0) for K, thr in itertools.product([1, 2, 4], [2.0, 2.5, 3.0])]
cells = []
for p in grid:
    r = ev(oos_trades(p))
    cells.append(dict(K=p["K"], thr=p["thr"], n=r["n"], oos_net=r["net"], pf=r["pf"], f2=r["folds"][1], f3=r["folds"][2]))
    C.record_to_lab(STRAT, f"{TF}_verify_cell_K{p['K']}_z{p['thr']}_oos", "HL_basket50", TF, p, r, period=times,
                    source=SRC, notes="verify: grid cell evaluated on OOS window only (folds 2+3)")
cdf = pd.DataFrame(cells)
print("OOS net by grid cell:\n", cdf.to_string())
OUT["grid_oos"] = cells
OUT["grid_oos_rank_of_selected"] = int((cdf["oos_net"] > r0["net"]).sum() + 1)
OUT["grid_oos_frac_pos"] = float((cdf["oos_net"] > 0).mean())
OUT["grid_oos_mean"] = float(cdf["oos_net"].mean())

# ---- 6. fine neighbourhood (OOS window, no re-selection) -------------------
neigh = []
for K in (2, 3):
    for thr in (2.5, 2.75, 3.0, 3.25, 3.5, 4.0):
        for Hh in (3, 4, 5):
            p = dict(K=K, thr=thr, H=Hh, tgt=0.5, vol_filter=1.0)
            r = ev(oos_trades(p))
            neigh.append(dict(K=K, thr=thr, H=Hh, n=r["n"], net=r["net"], pf=r["pf"], bps=r["net_bps"], f2=r["folds"][1], f3=r["folds"][2]))
            C.record_to_lab(STRAT, f"{TF}_verify_neigh_K{K}_z{thr}_H{Hh}", "HL_basket50", TF, p, r, period=times,
                            source=SRC, notes="verify: fine neighbour of WF-best, OOS window only")
ndf = pd.DataFrame(neigh)
print("fine neighbourhood:\n", ndf.to_string())
OUT["neigh_frac_pos"] = float((ndf["net"] > 0).mean())
OUT["neigh_frac_both_folds_pos"] = float(((ndf["f2"] > 0) & (ndf["f3"] > 0)).mean())
OUT["neigh_median_bps"] = float(ndf["bps"].median())
OUT["neigh_f3_frac_pos"] = float((ndf["f3"] > 0).mean())

# ---- 7. hypothesis count across the campaign -------------------------------
hyps = sorted(p.name for p in HERE.glob("h_*.py") if not p.name.endswith("_diag.py"))
OUT["campaign_hypothesis_scripts"] = hyps
OUT["n_selections"] = dict(grid_cells_per_tf=9, timeframes=2, neighbours_reported=15 * 2)
print("hypothesis scripts in campaign:", len(hyps), hyps)

# ---- 8. record headline verify rows ---------------------------------------
trim = t.drop(t["net_pnl"].nlargest(3).index)
C.record_to_lab(STRAT, f"{TF}_verify_oos_drop_top3", "HL_basket50", TF, BEST, ev(trim), period=times, source=SRC,
                notes=f"verify: WF-best OOS with top-3 trades removed; iid boot P(net<=0)={p_iid:.3f}; day-cluster P={OUT['boot_day']['p_net_le_0']:.3f}")
C.record_to_lab(STRAT, f"{TF}_verify_oos_bootstrap", "HL_basket50", TF, BEST,
                dict(C.empty_result(), n=n, net=float(np.median(boot)), pf=r0["pf"], folds=r0["folds"]),
                period=times, source=SRC, trust="synthetic",
                notes=f"verify: iid bootstrap median of OOS net; P(net<=0)={p_iid:.4f} CI95=[{ci[0]:.0f},{ci[1]:.0f}]; hour-cluster P={OUT['boot_hour']['p_net_le_0']:.4f}; day-cluster P={OUT['boot_day']['p_net_le_0']:.4f}; week-cluster P={OUT['boot_week']['p_net_le_0']:.4f}")

Path(__file__).with_suffix(".json").write_text(json.dumps(OUT, indent=1, default=str))
print("\nJSON:", json.dumps({k: OUT[k] for k in ("repro", "boot_iid", "boot_hour", "boot_day", "boot_week", "drop_top3", "drop_top5", "drop_best_day", "drop_best_week", "grid_oos_rank_of_selected", "grid_oos_frac_pos", "neigh_frac_pos", "neigh_frac_both_folds_pos")}, default=str, indent=1))
