"""Leakage / code-correctness verification for h_xsec_mom30_rev1_hedged.

Does NOT edit the author's script; imports it as a module and
  1. reproduces the walk-forward headline,
  2. checks every long/hedge fill price against the raw 1h bars (open of the
     00:00 bar at entry_time / exit_time) and that the signal row is the 1d
     candle that CLOSED at that open (no same-day information),
  3. quantifies the fold-1 selection boundary leak (fold-1 entries that settle
     inside fold 2) and re-selects with those trades marked-to-market at the
     fold-1 boundary,
  4. runs a signal lagged by one extra day, a fill delayed by one bar (01:00
     open), and a no-funding variant, all with the fold-1-selected params,
  5. records every variant to quant-lab.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import common as C            # noqa: E402
import h_xsec_mom30_rev1_hedged as A   # noqa: E402  (module import builds the panel only)

SRC = Path(__file__).name
OUT = ROOT / "tests" / "verify_xsec_mom30_rev1_hedged_leakage.json"
P, MASK0, COINS, DAY_OPENS, PERIOD = A.P, A.MASK.copy(), A.COINS, A.DAY_OPENS, A.PERIOD
bounds = C.fold_bounds(PERIOD, 3)
f1s, f1e = bounds[0]
res = {}


def fmt(r):
    return (f"n={r['n']} net={r['net']:.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"folds={[round(f, 1) for f in r['folds']]}")


def oos_of(params):
    tr = pd.concat([A.run_fn(params, *bounds[1]), A.run_fn(params, *bounds[2])])
    return C.oos_result(tr, PERIOD, 3), tr


# ---------------------------------------------------------------------------
# 1. reproduce
# ---------------------------------------------------------------------------
best, oos_tr, table = C.walk_forward(A.GRID, A.run_fn, PERIOD, n_folds=3, min_trades=10)
oos = C.oos_result(oos_tr, PERIOD, 3)
print("REPRODUCE best:", best); print("  OOS:", fmt(oos))
res["reproduce"] = dict(best=best, oos_net=oos["net"], oos_n=oos["n"], oos_pf=oos["pf"], folds=oos["folds"])
full_tr, diag = A.build_trades(best)
full_tr = C.add_pnl(full_tr)

# ---------------------------------------------------------------------------
# 2. fill / signal alignment against raw 1h + 1d data
# ---------------------------------------------------------------------------
import xsec_pit_data as D   # noqa: E402
bad_entry = bad_exit = bad_sig = 0; checked = 0; sig_gap_h = []
d_close_raw = {}
for _, r in full_tr.iterrows():
    c = r["instrument"]; b = P["bars"][c]
    if r["leg"] == "long":
        checked += 1
        eo = b["open"].get(r["entry_time"], np.nan)
        if not np.isclose(eo, r["entry_px"]):
            bad_entry += 1
        if not r["delist"]:
            xo = b["open"].get(r["exit_time"], np.nan)
            if not np.isclose(xo, r["exit_px_raw"]):
                bad_exit += 1
        # signal row used at entry = 1d candle with open time entry_time - 1d; it closes at entry_time
        if c not in d_close_raw:
            d_close_raw[c] = D.read(D.path_1d(c))["close"]
        dc = d_close_raw[c]
        sig_day = r["entry_time"] - pd.Timedelta(days=1)
        i = DAY_OPENS.get_loc(r["entry_time"])
        # ret_rev row i must equal close(sig_day)/close(sig_day-1)-1 from the raw 1d file
        rr = dc.get(sig_day, np.nan) / dc.get(sig_day - pd.Timedelta(days=1), np.nan) - 1
        if not np.isclose(rr, P["ret_rev"][i, A.CIDX[c]], equal_nan=True):
            bad_sig += 1
        # the 1d candle's close must equal the 1h close of the bar BEFORE entry (23:00), i.e. info ends at entry_time
        h23 = b["close"].get(r["entry_time"] - pd.Timedelta(hours=1), np.nan)
        if np.isfinite(h23) and not np.isclose(h23, dc.get(sig_day, np.nan)):
            bad_sig += 1
    else:
        eo = P["bars"]["BTC"]["open"].get(r["entry_time"], np.nan)
        if not (np.isclose(eo, r["entry_px"])):
            bad_entry += 1
# every trade: exit strictly after entry, entry at a 00:00 bar
assert (full_tr["exit_time"] > full_tr["entry_time"]).all()
assert (full_tr["entry_time"].dt.hour == 0).all()
print(f"ALIGNMENT: long trades checked={checked} bad_entry_fill={bad_entry} bad_exit_fill={bad_exit} bad_signal_rows={bad_sig}")
res["alignment"] = dict(checked=checked, bad_entry=bad_entry, bad_exit=bad_exit, bad_sig=bad_sig)

# funding index sanity: cum funding used for a trade only covers (entry, exit]
cum = P["fund_cum"]["BTC"]
assert (cum.index.minute == 0).all() and (cum.index.second == 0).all()
print("FUNDING: cum index hourly-floored OK; sample funding for BTC in first OOS hedge row:",
      float(full_tr[(full_tr.leg == 'hedge') & (full_tr.entry_time >= bounds[1][0])].iloc[0]['funding_usd']))

# stale 00:00 bar at entry (volume == 0) -> execution note
stale = 0
for _, r in full_tr[full_tr.leg == "long"].iterrows():
    v = P["bars"][r["instrument"]]["volume"].get(r["entry_time"], np.nan)
    stale += int(v == 0)
print("stale (zero-volume) 00:00 entry bars among longs:", stale)
res["stale_entry_bars"] = stale

# ---------------------------------------------------------------------------
# 3. fold-1 selection boundary leak
# ---------------------------------------------------------------------------
i_b = int(np.searchsorted(DAY_OPENS, f1e))       # first 00:00 open >= fold-1 end
t_b = DAY_OPENS[i_b]


def truncate_f1(tr):
    """Fold-1 view of a trade list with any position still open at the fold-1
    boundary marked-to-market at the boundary 00:00 open (taker exit fee)."""
    t = tr[(tr.entry_time >= f1s) & (tr.entry_time < f1e)].copy()
    if len(t) == 0:
        return t
    over = t.exit_time > t_b
    for k in t.index[over]:
        j = A.CIDX[t.at[k, "instrument"]]
        px = P["O"][i_b, j]
        if not np.isfinite(px):
            continue
        side = t.at[k, "side"]; q = t.at[k, "qty"]
        fu = A.funding_usd(t.at[k, "instrument"], side, t.at[k, "notional_usd"], t.at[k, "entry_time"], t_b)
        t.at[k, "exit_time"] = t_b
        t.at[k, "exit_px"] = px + side * fu / q
        t.at[k, "fee_usd"] = C.hl_fee(t.at[k, "notional_usd"], t.at[k, "maker_entry"]) + C.hl_fee(q * px, False)
    return t


rows = []
for i, p in enumerate(A.GRID):
    tr, _ = A.build_trades(p)
    f1 = tr[(tr.entry_time >= f1s) & (tr.entry_time < f1e)]
    n_over = int((f1.exit_time > f1e).sum())
    r_raw = C.evaluate(f1, 1); r_tr = C.evaluate(truncate_f1(tr), 1)
    rows.append(dict(idx=i, name=A.pname(p), is_n=r_raw["n"], is_net_raw=r_raw["net"], n_settle_in_f2=n_over,
                     pnl_settle_in_f2=float(C.add_pnl(f1[f1.exit_time > f1e])["net_pnl"].sum()) if n_over else 0.0,
                     is_net_mtm=r_tr["net"]))
sel = pd.DataFrame(rows)
elig = sel[sel.is_n >= 10]
best_mtm = A.GRID[int(elig.sort_values("is_net_mtm", ascending=False).iloc[0]["idx"])]
print("\nFOLD-1 SELECTION with boundary positions marked-to-market at", t_b.date())
print(sel.round(1).to_string(index=False))
print("selected (author, raw):", best, "\nselected (MTM-truncated):", best_mtm)
oos_mtm, _ = oos_of(best_mtm)
print("OOS of MTM-selected params:", fmt(oos_mtm))
res["selection_leak"] = dict(table=sel.to_dict("records"), best_mtm=best_mtm, oos_mtm_net=oos_mtm["net"],
                             selection_changed=(best_mtm != best))
C.record_to_lab(A.STRATEGY, "VERIFY_LEAK_mtmselect_" + A.pname(best_mtm), "HL_XSEC_PIT", f"{best_mtm['rebal_d']}d",
                best_mtm, oos_mtm, period=(bounds[1][0], bounds[2][1]), source=SRC,
                notes="leakage verify: fold-1 selection redone with boundary positions MTM at fold-1 end; OOS folds 2+3")

# positions carried across the fold-2 start that the OOS omits (entered in fold 1, settle in OOS)
carry = full_tr[(full_tr.entry_time < bounds[1][0]) & (full_tr.exit_time > bounds[1][0])]
print(f"positions entered in fold 1 that settle inside OOS (excluded from OOS by entry_time): n={len(carry)} "
      f"net={carry['net_pnl'].sum():.1f}")
res["carry_into_oos"] = dict(n=int(len(carry)), net=float(carry["net_pnl"].sum()))

# ---------------------------------------------------------------------------
# 4. variants with the selected params
# ---------------------------------------------------------------------------
def with_patch(name, patch_fn, params=best):
    saved = {k: P[k] for k in ("ret_mom", "ret_rev", "vol30", "vol24", "O", "H", "Lo", "Cl")}
    saved_mask = A.MASK; saved_cum = dict(P["fund_cum"])
    A._CACHE.clear()
    try:
        patch_fn()
        r, tr = oos_of(params)
        full = C.evaluate(A.build_trades(params)[0], 3, *PERIOD)
    finally:
        P.update(saved); A.MASK = saved_mask; P["fund_cum"] = saved_cum; A._CACHE.clear()
    print(f"{name}: OOS {fmt(r)} | full folds {[round(f,1) for f in full['folds']]}")
    C.record_to_lab(A.STRATEGY, "VERIFY_LEAK_" + name + "_" + A.pname(params), "HL_XSEC_PIT", f"{params['rebal_d']}d",
                    dict(params, verify=name), r, period=(bounds[1][0], bounds[2][1]), source=SRC,
                    notes=f"leakage verify variant {name}; OOS folds 2+3; full folds={np.round(full['folds'],1).tolist()}")
    res[name] = dict(oos_net=r["net"], oos_n=r["n"], oos_pf=r["pf"], folds=r["folds"], full_folds=full["folds"])
    return r


def shift_rows(a, k=1):
    out = np.full_like(a, np.nan); out[k:] = a[:-k]; return out


def patch_lag1():
    for k in ("ret_mom", "ret_rev", "vol30", "vol24"):
        P[k] = shift_rows(P[k])
    A.MASK = A.universe_mask(P)


def patch_fill_01():
    """Fill at the 01:00 bar open instead of the 00:00 open (signal unchanged)."""
    O2 = np.full_like(P["O"], np.nan)
    t01 = DAY_OPENS + pd.Timedelta(hours=1)
    for j, c in enumerate(COINS):
        O2[:, j] = P["bars"][c]["open"].reindex(t01).values
    P["O"] = O2
    A.MASK = A.universe_mask(P)


def patch_no_funding():
    P["fund_cum"] = {}


def patch_rev_lag1():
    """Only the 1d-reversal leg lagged by one day (momentum leg unchanged)."""
    P["ret_rev"] = shift_rows(P["ret_rev"])
    A.MASK = A.universe_mask(P)


print("\nVARIANTS (fold-1-selected params, OOS folds 2+3):")
with_patch("base_check", lambda: None)
with_patch("signal_lag1d", patch_lag1)
with_patch("rev_leg_lag1d", patch_rev_lag1)
with_patch("fill_at_0100_open", patch_fill_01)
with_patch("no_funding", patch_no_funding)

# unhedged neighbour under the same variants (to see whether the long leg itself is timing-fragile)
unh = dict(best, hedge=0)
with_patch("unhedged_signal_lag1d", patch_lag1, params=unh)
with_patch("unhedged_fill_at_0100_open", patch_fill_01, params=unh)

OUT.write_text(json.dumps(res, default=str, indent=1))
print("wrote", OUT)
