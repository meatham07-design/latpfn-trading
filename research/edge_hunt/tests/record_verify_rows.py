"""Record the hl_listing_drift verify rows into quant-lab (project edge-hunt)."""
import os, sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C
STRAT="hl_listing_drift"; SRC="tests/verify_hl_listing_drift_*.py"
PER=(pd.Timestamp("2020-02-03",tz="UTC"), pd.Timestamp("2026-07-17",tz="UTC"))
def rec(variant, params, r, notes):
    full=dict(C.empty_result(1)); full.update({k:v for k,v in r.items() if k in full})
    C.record_to_lab(STRAT, variant, "binance", "1h", params, full, period=PER, source=SRC, notes=notes)
    print("lab <-", variant, round(full["net"],1))

L=json.loads(Path("verify_hl_listing_drift_leakage.json").read_text())
E=json.loads(Path("verify_hl_listing_drift_execution.json").read_text())
S=json.loads(Path("verify_hl_listing_drift_statistics.json").read_text())
D=json.loads(Path("diag_deployable.json").read_text())
P0=dict(rule="short_after",N=24,H=7,hedge=True)

rec("verify_full_sample_baseline", P0, L["baseline"], "820-listing rerun (the original md ran mid-fetch on 139)")
rec("verify_leak_ex_early_funding", P0, L["L1"]["ex any-early-funding"], "drop every symbol with any funding stamp before its first kline")
rec("verify_leak_ex_nonplaceholder", P0, L["L1"]["ex non-placeholder-early"], "drop only symbols with a real funding rate before t0")
rec("verify_leak_dedup_base", P0, L["L4"]["dedup"], "one listing per base asset")
rec("verify_leak_still_listed", P0, L["L3"]["still listed"], "survivorship: symbols still trading today")
rec("verify_leak_delisted", P0, L["L3"]["delisted since"], "survivorship: symbols delisted since")
for s, r in E["E1"].items():
    rec(f"verify_exec_slip{s}bps", P0, dict(n=r["n"],net=r["net"],pf=r["pf"],net_bps=r["bps"],folds=[0.0]+r["folds"]),
        f"{s} bps/side slippage on all four legs; 2026 net {r['net_2026']:.0f}")
for lbl, r in E["E2"].items():
    rec(f"verify_exec_{lbl.replace(' ','_')}", P0, r, "timing perturbation @10bps slippage")
for lbl, r in E["E3"].items():
    rec(f"verify_exec_fill_{lbl.split(' ')[0]}", P0, r, f"adverse fill: {lbl}")
for row in S["S1"]["rows"]:
    rec(f"verify_stats_expandingWF_{row['year']}", row["params"],
        dict(n=row["n"],net=row["net"],pf=row["pf"]), "expanding-window WF: params re-picked on all prior listings only")
rec("verify_stats_expandingWF_TOTAL", P0, dict(n=sum(r["n"] for r in S["S1"]["rows"]), net=S["S1"]["total_net"]),
    "TOTAL of the expanding-window walk-forward 2021-2026 -- the honest OOS")
rec("verify_stats_equal_n_fold2", S["S2"]["pick"], S["S2"]["fold2"], "equal-event-count folds, fold-1 pick, fold 2")
rec("verify_stats_equal_n_fold3", S["S2"]["pick"], S["S2"]["fold3"], "equal-event-count folds, fold-1 pick, fold 3")
rec("verify_stats_matched_date_control", P0,
    dict(n=S["S7"]["legs_per_draw"], net=S["S7"]["control_mean"]),
    f"same dates, seasoned coins, 300 draws; p(control>=actual)={S['S7']['p_control_ge_actual']:.4f}; actual price-only {S['S7']['actual_price_only']:.0f}")
for k, v in D.items():
    rec(f"verify_filter_{k}_2026", P0, dict(n=v["y2026_n"], net=v["y2026_net"]),
        f"filter chosen on <=2024; 2025 net {v['y2025_net']:.0f} on n={v['y2025_n']}")
print("done")
