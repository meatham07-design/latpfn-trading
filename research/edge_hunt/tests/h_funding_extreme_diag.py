"""Diagnostics for funding_extreme (not part of the headline)."""
import sys, json
sys.path.insert(0, "/Users/molt_bot/latpfn-trading/research/edge_hunt")
sys.path.insert(0, "/Users/molt_bot/latpfn-trading/research/edge_hunt/tests")
import numpy as np, pandas as pd
import common as C
import h_funding_extreme as H

data = H.load_all()
best = dict(measure="m1", pct=0.10, hold=24)
tr = H.slice_trades(H.build_trades(data, **best), *H.PERIOD)
t = C.add_pnl(tr)
t["fold"] = C.fold_labels(t["entry_time"], 3, *H.PERIOD) + 1
t["price_pnl"] = t["side"] * (t["exit_px_raw"] - t["entry_px"]) * t["qty"]
t["absm_bps"] = t["measure_val"].abs() * 1e4
print("== side x fold (net, n, funding) ==")
print(t.pivot_table(index="fold", columns="side", values="net_pnl", aggfunc=["sum", "size"]).round(1))
print("funding per trade (USD):", t["funding_usd"].mean().round(3), " fee per trade:", t["fee_usd"].mean().round(3))
print("\n== |measure| bucket x fold (net) ==")
t["bkt"] = pd.cut(t["absm_bps"], [0, 0.25, 0.5, 1, 2, 5, 100], labels=["<0.25", "0.25-0.5", "0.5-1", "1-2", "2-5", ">5"])
pv = t.pivot_table(index="bkt", columns="fold", values="net_pnl", aggfunc=["sum", "size"], observed=True).round(1)
print(pv)
print("\n== |measure| bucket x side, OOS folds 2+3 (net, n, avg bps) ==")
oos = t[t["fold"] > 1]
g = oos.groupby(["bkt", "side"], observed=True).agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), funding=("funding_usd", "sum"), price=("price_pnl", "sum"))
g["bps"] = g["net"] / (g["n"] * H.NOTIONAL) * 1e4
print(g.round(2))
# market drift per fold: equal-weight basket of the 50 coins, 24h fwd return
print("\n== market: mean 24h forward return by fold (all coins, %), and mean |24h ret| ==")
rows = []
for coin, df in data.items():
    r = df["open"].shift(-24) / df["open"] - 1
    d = pd.DataFrame({"r": r, "fold": C.fold_labels(pd.Series(df.index), 3, *H.PERIOD) + 1}, index=df.index)
    d = d[(df.index >= H.PERIOD[0]) & (df.index < H.PERIOD[1])]
    rows.append(d)
m = pd.concat(rows)
print(m.groupby("fold")["r"].agg(mean=lambda x: x.mean() * 100, absmean=lambda x: x.abs().mean() * 100, n="size").round(3))
# long-only / short-only record
for side, name in ((1, "long_only"), (-1, "short_only")):
    r = C.evaluate(t[t["side"] == side], 3, *H.PERIOD)
    print(name, H.fmt_res(r))
    C.record_to_lab(H.STRATEGY, f"diag_{name}_m1_p10_h24", "HL_ALL", "1h", dict(best, mode="taker", side=side), r,
                    period=H.PERIOD, source="tests/h_funding_extreme_diag.py", notes="diagnostic split by side")
# large-magnitude only (|m1| > 2 bps/h)
for thr in (1.0, 2.0, 5.0):
    r = C.evaluate(t[t["absm_bps"] > thr], 3, *H.PERIOD)
    print(f"abs>{thr}bps", H.fmt_res(r))
    C.record_to_lab(H.STRATEGY, f"diag_absgt{thr}bps_m1_p10_h24", "HL_ALL", "1h", dict(best, mode="taker", min_abs_bps=thr), r,
                    period=H.PERIOD, source="tests/h_funding_extreme_diag.py", notes="diagnostic: absolute magnitude filter on top of rank")
# duplicate-trigger check: how many entries are re-entries right after an exit (persistent extreme)?
t = t.sort_values(["coin", "entry_time"])
gap = t.groupby("coin")["entry_time"].diff().dt.total_seconds() / 3600
print("\nre-entry within 1h of previous exit (hold=24 -> gap==24h):", (gap == 24).mean().round(3))
