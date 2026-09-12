"""Adversarial verification (lens: leakage / code correctness) of
h_mean_reversion_zscore.py, 1h headline.

1. Reproduce the author's walk-forward numbers exactly (import the author's module).
2. Fill-rule sensitivity: the author's maker fill counts a fill whenever bar t+1
   trades through close_t by ANY amount (strict >), and always at the limit price
   with the maker fee -- even when bar t+1 OPENS already beyond the limit (in
   which case a resting limit could not have been a maker fill at that price).
   Re-run with (a) trade-through margins of 1 tick / 1 / 2 / 5 bps,
   (b) gap-at-open cases excluded, (c) gap-at-open cases filled at the open as taker.
3. Rolling walk-forward: select on fold 2 -> test fold 3 (the author's fold-1
   selection happened in a period where every cell lost money).
4. Survivorship: the 50-coin universe is the top-50 by 24h volume at the END of
   the period (snapshot 2026-08-27). Re-run the WF-best params over the OOS
   window on coins ranked 51-100 today and on delisted coins that traded in 2026.
All variants recorded to quant-lab (project edge-hunt).
"""
from __future__ import annotations
import sys, json, math, itertools
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/Users/molt_bot/latpfn-trading/research/edge_hunt")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import common as C
import h_mean_reversion_zscore as M

SCRATCH = Path("/private/tmp/claude-501/-Users-molt-bot/78c80aee-b9a8-40f2-986e-38cb35c978c8/scratchpad/extra_hl")
STRAT = "mean_reversion_zscore"
SRC = "research/edge_hunt/tests/verify_mean_reversion_zscore_leakage.py"
TF = "1h"
NOTIONAL = 1000.0
VOL_WIN = 100


def tick(px):
    # HL perps: 5 significant figures -> tick = 10^(floor(log10 px) - 4)
    return 10.0 ** (math.floor(math.log10(px)) - 4)


def simulate2(b, coin, K, thr, H, tgt, vol_filter, through_bps=0.0, through_tick=False, gap_mode="author"):
    """Author's mechanics + fill-rule knobs.
    through_bps  : bar t+1 must trade through the limit by >= this many bps (0 = author's strict >).
    through_tick : require trade-through by >= 1 tick.
    gap_mode     : 'author'     fill at limit, maker fee even if bar t+1 opens beyond the limit
                   'exclude'    skip signals where bar t+1 opens beyond the limit (not a maker fill)
                   'taker_open' fill at bar t+1 open with TAKER fee when it opens beyond the limit
    Returns (trades, n_gap, n_fill)."""
    sf = M.signal_frame(b, K, thr, vol_filter)
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    idx = b.index; n = len(b)
    sig_idx = np.flatnonzero(sf["side"].values != 0)
    sides = sf["side"].values[sig_idx]
    rK = sf["rK"].values
    trades = []; busy_until = -1; n_gap = 0; n_fill = 0
    for i, s in zip(sig_idx, sides):
        if i <= busy_until or i + 1 + H >= n:
            continue
        lim = c[i]
        m = lim * through_bps / 1e4
        if through_tick:
            m = max(m, tick(lim))
        if s == -1 and not (h[i + 1] > lim + m):
            continue
        if s == 1 and not (l[i + 1] < lim - m):
            continue
        gap = (s == -1 and o[i + 1] > lim) or (s == 1 and o[i + 1] < lim)
        maker = True; entry_px = lim
        if gap:
            n_gap += 1
            if gap_mode == "exclude":
                continue
            if gap_mode == "taker_open":
                maker = False; entry_px = o[i + 1]
        n_fill += 1
        entry_t = idx[i + 1]
        exit_j, exit_px = i + 1 + H, o[i + 1 + H]
        if tgt is not None and np.isfinite(rK[i]):
            target = lim * math.exp(s * tgt * abs(rK[i]))
            for j in range(i + 2, i + 1 + H):
                if (s == 1 and h[j] > target) or (s == -1 and l[j] < target):
                    exit_j, exit_px = j, target
                    break
        qty = NOTIONAL / entry_px
        trades.append(C.crypto_trade(entry_t, idx[exit_j], int(s), float(entry_px), float(exit_px),
                                     qty, coin, maker_entry=maker, maker_exit=False))
        busy_until = exit_j - 1
    return trades, n_gap, n_fill


def run_variant(coins, loader, p, **kw):
    rows = []; ng = nf = 0
    for coin in coins:
        b = loader(coin)
        tr, g, f = simulate2(b, coin, p["K"], p["thr"], p["H"], p["tgt"], p["vol_filter"], **kw)
        rows.extend(tr); ng += g; nf += f
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    if len(df):
        df = df.sort_values("entry_time").reset_index(drop=True)
    return df, ng, nf


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} gross={r['gross']:9.2f} pf={r['pf']:.3f} wr={r['wr']:.3f} "
            f"bps={r['net_bps']:.1f} folds={[round(f,1) for f in r['folds']]} fold_n={r['fold_n']}")


def main():
    coins = C.list_hl_coins()
    lo = min(M.bars(c, TF).index.min() for c in coins)
    hi = max(M.bars(c, TF).index.max() for c in coins)
    times = (lo, hi)
    bounds = C.fold_bounds(times, 3)
    oos_s, oos_e = bounds[1][0], bounds[-1][1]
    print("fold bounds:", [(str(a)[:16], str(b)[:16]) for a, b in bounds])
    grid = [dict(K=K, thr=thr, H=4, tgt=0.5, vol_filter=1.0) for K, thr in itertools.product([1, 2, 4], [2.0, 2.5, 3.0])]

    def run_fn(p, s, e):
        return M.in_window(M.all_trades(TF, p, coins), s, e)

    # ---- 1. reproduce ----
    best, oos_tr, table = C.walk_forward(grid, run_fn, times, 3, min_trades=10)
    oos = C.oos_result(oos_tr, times, 3)
    print("\n[1] REPRODUCE author's 1h WF: best=", best); print("    OOS:", fmt(oos))
    # my simulate2 with author settings must match exactly
    mine, ng, nf = run_variant(coins, lambda c: M.bars(c, TF), best)
    r0 = C.evaluate(M.in_window(mine, oos_s, oos_e), 3, start=lo, end=hi)
    print("    simulate2(author mode):", fmt(r0), f"| gap-at-open fills={ng}/{nf} over full period")
    assert abs(r0["net"] - oos["net"]) < 1e-6 and r0["n"] == oos["n"], "simulate2 does not reproduce author"

    # OOS of every grid cell (no selection) for context
    print("\n    OOS (folds 2+3) of every grid cell, author's mechanics:")
    for p in grid:
        r = C.evaluate(run_fn(p, oos_s, oos_e), 3, start=lo, end=hi)
        print(f"      K={p['K']} thr={p['thr']}: " + fmt(r))

    # ---- 2. fill-rule sensitivity (WF-best, OOS window, no re-selection) ----
    print("\n[2] FILL RULE sensitivity, WF-best params, OOS window folds 2+3")
    variants = [
        ("through_1tick", dict(through_tick=True)),
        ("through_1bp", dict(through_bps=1.0)),
        ("through_2bp", dict(through_bps=2.0)),
        ("through_5bp", dict(through_bps=5.0)),
        ("gap_exclude", dict(gap_mode="exclude")),
        ("gap_taker_open", dict(gap_mode="taker_open")),
        ("through_1tick_gap_exclude", dict(through_tick=True, gap_mode="exclude")),
        ("through_2bp_gap_taker", dict(through_bps=2.0, gap_mode="taker_open")),
    ]
    results = {}
    for name, kw in variants:
        df, ng, nf = run_variant(coins, lambda c: M.bars(c, TF), best, **kw)
        r = C.evaluate(M.in_window(df, oos_s, oos_e), 3, start=lo, end=hi)
        results[name] = r
        print(f"    {name:28s}: " + fmt(r) + f" | gap fills {ng}/{nf} (full period)")
        C.record_to_lab(STRAT, f"{TF}_verify_fill_{name}", "HL_basket50", TF, dict(best, fill=name), r,
                        period=times, source=SRC, notes=f"leakage verify: fill-rule variant {kw}; WF-best OOS folds 2+3")

    # gap-at-open diagnostics: PnL of gap vs non-gap fills in the author's run
    df_a, _, _ = run_variant(coins, lambda c: M.bars(c, TF), best)
    df_g, _, _ = run_variant(coins, lambda c: M.bars(c, TF), best, gap_mode="exclude")
    a = C.add_pnl(M.in_window(df_a, oos_s, oos_e)); g = C.add_pnl(M.in_window(df_g, oos_s, oos_e))
    key = lambda d: list(zip(d["instrument"], pd.to_datetime(d["entry_time"], utc=True)))
    gk = set(key(g)); is_gap = np.array([k not in gk for k in key(a)])
    print(f"    author OOS trades: gap-at-open n={is_gap.sum()} net={a.loc[is_gap,'net_pnl'].sum():.1f} "
          f"| non-gap n={(~is_gap).sum()} net={a.loc[~is_gap,'net_pnl'].sum():.1f}")

    # ---- 3. rolling walk-forward: select on fold 2 -> fold 3 ----
    print("\n[3] ROLLING WF")
    f2s, f2e = bounds[1]; f3s, f3e = bounds[2]
    rows = []
    for p in grid:
        r2 = C.evaluate(run_fn(p, f2s, f2e), 1)
        r3 = C.evaluate(run_fn(p, f3s, f3e), 1)
        r12 = C.evaluate(run_fn(p, bounds[0][0], f2e), 1)
        rows.append(dict(K=p["K"], thr=p["thr"], f2_net=r2["net"], f2_n=r2["n"], f12_net=r12["net"], f3_net=r3["net"], f3_n=r3["n"]))
    t = pd.DataFrame(rows); print(t.to_string())
    pick2 = t.sort_values("f2_net", ascending=False).iloc[0]
    pick12 = t.sort_values("f12_net", ascending=False).iloc[0]
    print(f"    select on fold2 -> K={pick2.K} thr={pick2.thr}: fold3 net={pick2.f3_net:.1f} n={int(pick2.f3_n)}")
    print(f"    select on folds1+2 -> K={pick12.K} thr={pick12.thr}: fold3 net={pick12.f3_net:.1f} n={int(pick12.f3_n)}")
    # 2-step rolling OOS = fold2 from fold1-pick + fold3 from fold2-pick
    roll = oos["folds"][1] + pick2.f3_net
    print(f"    2-step rolling OOS (fold2 via fold1 pick + fold3 via fold2 pick) = {roll:.1f}")
    p2 = dict(best, K=int(pick2.K), thr=float(pick2.thr))
    r3 = C.evaluate(run_fn(p2, f3s, f3e), 3, start=lo, end=hi)
    C.record_to_lab(STRAT, f"{TF}_verify_rolling_fold2pick_fold3", "HL_basket50", TF, p2, r3, period=times, source=SRC,
                    notes=f"leakage verify: rolling WF, params picked on fold 2, tested on fold 3; 2-step rolling OOS={roll:.1f}")

    # ---- 4. survivorship: coins outside the end-of-period top-50 ----
    print("\n[4] SURVIVORSHIP: WF-best params on coins NOT in the end-of-period top-50, OOS window")
    extra = sorted(p.name[3:-11] for p in SCRATCH.glob("hl_*_1h.parquet"))
    uall = pd.read_parquet(ROOT / "data" / "hl_universe_all.parquet")
    rank = {c: i for i, c in enumerate(uall["coin"])}
    _EX = {}
    def load_extra(c):
        if c not in _EX:
            b = C._read(SCRATCH / f"hl_{c}_1h.parquet")
            b = b[~b.index.duplicated()].copy()
            if c not in rank:  # delisted: drop the final 24 bars (delisting/settlement artefacts)
                b = b.iloc[:-24]
            b = b[b.index >= lo - pd.Timedelta(hours=VOL_WIN + 5)]
            b["usd_vol"] = b["volume"] * b["close"]; _EX[c] = b
        return _EX[c]
    ex51 = [c for c in extra if c in rank and 50 <= rank[c] < 100]
    dl = [c for c in extra if c not in rank]
    for label, cs in (("rank51_100", ex51), ("delisted", dl), ("all_extra", ex51 + dl)):
        cs = [c for c in cs if len(load_extra(c)) > VOL_WIN + 10]
        if not cs:
            print(f"    {label}: no data"); continue
        df, ng, nf = run_variant(cs, load_extra, best)
        w = M.in_window(df, oos_s, oos_e)
        r = C.evaluate(w, 3, start=lo, end=hi)
        print(f"    {label:12s} ({len(cs)} coins): " + fmt(r))
        if len(w):
            pc = C.add_pnl(w).groupby("instrument")["net_pnl"].agg(["count", "sum"]).sort_values("sum")
            print("      per-coin (worst 8):"); print(pc.head(8).to_string())
        C.record_to_lab(STRAT, f"{TF}_verify_survivorship_{label}", f"HL_{label}", TF, best, r, period=times, source=SRC,
                        notes=f"leakage verify: WF-best on {len(cs)} coins outside end-of-period top-50 ({label}); OOS window")
        results[f"surv_{label}"] = r
    # pooled: top-50 + rank 51-100 (a universe you could have chosen without hindsight = top-100 today, still biased but wider)
    df50 = M.in_window(df_a, oos_s, oos_e)
    dfx, _, _ = run_variant([c for c in ex51 if len(load_extra(c)) > VOL_WIN + 10], load_extra, best)
    pooled = pd.concat([df50, M.in_window(dfx, oos_s, oos_e)], ignore_index=True)
    rp = C.evaluate(pooled, 3, start=lo, end=hi)
    print("    pooled top-100:", fmt(rp))
    C.record_to_lab(STRAT, f"{TF}_verify_survivorship_top100_pooled", "HL_top100", TF, best, rp, period=times, source=SRC,
                    notes="leakage verify: WF-best on top-50 + rank 51-100 pooled; OOS window")

    # ---- 5. point-in-time universe: top-50 by FOLD-1 mean USD volume (no hindsight), then WF ----
    print("\n[5] POINT-IN-TIME UNIVERSE: rank ALL 117 coins (top-50 + rank 51-100 + delisted) by fold-1 mean USD volume, keep top 50")
    f1s, f1e = bounds[0]
    def loader_any(c):
        return M.bars(c, TF) if c in coins else load_extra(c)
    allc = [c for c in coins + extra if len(loader_any(c)) > VOL_WIN + 10]
    vol1 = {}
    for c in allc:
        b = loader_any(c); w = b[(b.index >= f1s) & (b.index < f1e)]
        if len(w) >= 24 * 30:  # need at least 30 days of fold-1 history to be rankable
            vol1[c] = float(w["usd_vol"].mean())
    pit = sorted(vol1, key=vol1.get, reverse=True)[:50]
    overlap = len(set(pit) & set(coins))
    print(f"    rankable={len(vol1)}; PIT top-50 overlaps end-of-period top-50 on {overlap} coins")
    print("    PIT-only coins:", sorted(set(pit) - set(coins)))
    print("    dropped from author's universe:", sorted(set(coins) - set(pit)))
    _PC = {}
    def run_pit(p, s, e, **kw):
        key = json.dumps(dict(p, **kw), sort_keys=True, default=str)
        if key not in _PC:
            _PC[key] = run_variant(pit, loader_any, p, **kw)[0]
        return M.in_window(_PC[key], s, e)
    bestp, oosp, tabp = C.walk_forward(grid, run_pit, times, 3, min_trades=10)
    rp = C.oos_result(oosp, times, 3)
    print(f"    PIT universe WF: best={bestp}  OOS: " + fmt(rp))
    C.record_to_lab(STRAT, f"{TF}_verify_pit_universe_walkforward_oos", "HL_pit_top50", TF, bestp, rp, period=times, source=SRC,
                    notes="leakage verify: universe = top-50 by fold-1 USD volume (point-in-time), WF fold-1 selection, OOS folds 2+3")
    results["pit_wf"] = rp
    r_same = C.evaluate(run_pit(best, oos_s, oos_e), 3, start=lo, end=hi)
    print(f"    PIT universe, author's best params {best}: " + fmt(r_same))
    C.record_to_lab(STRAT, f"{TF}_verify_pit_universe_authorparams", "HL_pit_top50", TF, best, r_same, period=times, source=SRC,
                    notes="leakage verify: point-in-time top-50 universe, author's WF-best params, OOS folds 2+3")
    results["pit_authorparams"] = r_same
    r_tick = C.evaluate(run_pit(best, oos_s, oos_e, through_tick=True), 3, start=lo, end=hi)
    print(f"    PIT universe, author's best params, trade-through >= 1 tick: " + fmt(r_tick))
    C.record_to_lab(STRAT, f"{TF}_verify_pit_universe_authorparams_1tick", "HL_pit_top50", TF, dict(best, fill="through_1tick"), r_tick,
                    period=times, source=SRC, notes="leakage verify: point-in-time top-50 universe, author's params, fill requires trade-through >= 1 tick")
    results["pit_authorparams_1tick"] = r_tick
    for p in grid:
        r = C.evaluate(run_pit(p, oos_s, oos_e), 3, start=lo, end=hi)
        print(f"      PIT grid K={p['K']} thr={p['thr']}: " + fmt(r))

    print("\nSUMMARY:", json.dumps({k: dict(n=v["n"], net=round(v["net"], 1), pf=round(v["pf"], 3), folds=[round(x, 1) for x in v["folds"]])
                                     for k, v in results.items()}, indent=1))


if __name__ == "__main__":
    main()
