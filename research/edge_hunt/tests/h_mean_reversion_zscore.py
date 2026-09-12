"""Hypothesis: short-horizon mean reversion on Hyperliquid perps.

Signal (bar t close): z = logret_K(t) / (sigma_1bar(trailing 100) * sqrt(K)).
|z| > thr -> contrarian MAKER limit at close_t. Fill only if bar t+1 trades
THROUGH the limit (short: high_{t+1} > close_t; long: low_{t+1} < close_t).
Entry time = open of bar t+1, fill price = close_t (never better than limit).
Exit: half-retrace target (checked on bars t+2..t+H, strict touch) or time
stop at the OPEN of bar t+1+H. Exit is charged TAKER. Entry MAKER.
Volume filter: bar-t USD volume >= vol_filter x trailing-100-bar mean (prior bars).
Fixed $1000 notional per trade, one position per coin at a time.

Walk-forward: parameters chosen on fold 1 only; folds 2+3 are the headline.
"""
from __future__ import annotations
import sys, json, itertools, math
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C

STRAT = "mean_reversion_zscore"
NOTIONAL = 1000.0
VOL_WIN = 100
SRC = "research/edge_hunt/tests/h_mean_reversion_zscore.py"

CFG = {
    "15m": dict(Ks=[3, 6, 12], H=8),
    "1h": dict(Ks=[1, 2, 4], H=4),
}
THRS = [2.0, 2.5, 3.0]

_BARS: dict[tuple[str, str], pd.DataFrame] = {}


def bars(coin, tf):
    k = (coin, tf)
    if k not in _BARS:
        b = C.hl_candles(coin, tf)
        b = b[~b.index.duplicated()].copy()
        b["usd_vol"] = b["volume"] * b["close"]
        _BARS[k] = b
    return _BARS[k]


def signal_frame(b: pd.DataFrame, K: int, thr: float, vol_filter: float):
    lc = np.log(b["close"])
    r1 = lc.diff()
    sig = r1.rolling(VOL_WIN).std()
    rK = lc.diff(K)
    z = rK / (sig * math.sqrt(K))
    vmean = b["usd_vol"].rolling(VOL_WIN).mean().shift(1)
    vratio = b["usd_vol"] / vmean
    side = np.where(z > thr, -1, np.where(z < -thr, 1, 0))
    ok = (vratio >= vol_filter) & np.isfinite(z) & (sig > 0)
    side = np.where(ok, side, 0)
    return pd.DataFrame({"z": z, "rK": rK, "side": side, "vratio": vratio}, index=b.index)


def simulate(coin, tf, K, thr, H, tgt, vol_filter, sides=None, sig_idx=None, seed=None):
    """Build trades for one coin. If sig_idx/sides given (shuffle test) they
    override the signal locations. Returns list of trade dicts."""
    b = bars(coin, tf)
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    idx = b.index
    n = len(b)
    if sig_idx is None:
        sf = signal_frame(b, K, thr, vol_filter)
        sig_idx = np.flatnonzero(sf["side"].values != 0)
        sides = sf["side"].values[sig_idx]
        rK = sf["rK"].values
    else:
        rK = np.log(b["close"]).diff(K).values
    trades = []
    busy_until = -1  # last bar index occupied by an open position
    for i, s in zip(sig_idx, sides):
        if i <= busy_until or i + 1 + H >= n:
            continue
        lim = c[i]
        # maker fill only if next bar trades THROUGH the limit
        if s == -1 and not (h[i + 1] > lim):
            continue
        if s == 1 and not (l[i + 1] < lim):
            continue
        entry_t = idx[i + 1]
        entry_px = lim
        exit_j, exit_px = i + 1 + H, o[i + 1 + H]
        if tgt is not None and np.isfinite(rK[i]):
            # profit target in the direction of the trade: retrace `tgt` of the K-bar move
            # (real signal: sign(rK) == -s, so this equals lim*exp(-tgt*rK))
            target = lim * math.exp(s * tgt * abs(rK[i]))
            for j in range(i + 2, i + 1 + H):
                if (s == 1 and h[j] > target) or (s == -1 and l[j] < target):
                    exit_j, exit_px = j, target
                    break
        qty = NOTIONAL / entry_px
        tr = C.crypto_trade(entry_t, idx[exit_j], int(s), float(entry_px), float(exit_px),
                            qty, coin, maker_entry=True, maker_exit=False)
        tr["signal_z"] = None
        trades.append(tr)
        busy_until = exit_j - 1  # a new signal may fire on the exit bar itself
    return trades


_CACHE: dict[str, pd.DataFrame] = {}


def all_trades(tf, params, coins):
    key = json.dumps({"tf": tf, **params}, sort_keys=True)
    if key not in _CACHE:
        rows = []
        for coin in coins:
            rows.extend(simulate(coin, tf, params["K"], params["thr"], params["H"],
                                 params["tgt"], params["vol_filter"]))
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        if len(df):
            df = df.sort_values("entry_time").reset_index(drop=True)
        _CACHE[key] = df
    return _CACHE[key]


def in_window(df, start, end):
    if not len(df):
        return df
    t = pd.to_datetime(df["entry_time"], utc=True)
    return df[(t >= start) & (t < end)].reset_index(drop=True)


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} bps={r['net_bps']:.1f} folds={[round(f,1) for f in r['folds']]}")


def shuffle_test(tf, params, coins, times, n_rep=30, seed=0):
    """Randomise signal timing (same count per coin, random sides), keep the
    fill/exit mechanics, evaluate over the OOS window (folds 2+3)."""
    rng = np.random.default_rng(seed)
    bounds = C.fold_bounds(times, 3)
    oos_s, oos_e = bounds[1][0], bounds[-1][1]
    real = in_window(all_trades(tf, params, coins), oos_s, oos_e)
    counts = real.groupby("instrument").size().to_dict() if len(real) else {}
    nets, pfs = [], []
    for rep in range(n_rep):
        rows = []
        for coin, cnt in counts.items():
            b = bars(coin, tf)
            n = len(b)
            # random signal bars; draw more than needed because fills are conditional
            k = min(n - VOL_WIN - params["H"] - 3, cnt * 3)
            cand = np.sort(rng.choice(np.arange(VOL_WIN, n - params["H"] - 2), size=k, replace=False))
            sides = rng.choice([-1, 1], size=k)
            trs = simulate(coin, tf, params["K"], params["thr"], params["H"], params["tgt"],
                           params["vol_filter"], sides=sides, sig_idx=cand, seed=rep)
            rows.extend(trs)
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        df = in_window(df, oos_s, oos_e)
        # match trade count to the real strategy
        if len(df) > len(real):
            df = df.sample(len(real), random_state=rep).sort_values("entry_time")
        r = C.evaluate(df, 3, start=bounds[0][0], end=bounds[-1][1])
        nets.append(r["net"]); pfs.append(r["pf"])
    return dict(real_net=float(C.evaluate(real, 3, start=bounds[0][0], end=bounds[-1][1])["net"]) if len(real) else 0.0,
                shuf_mean=float(np.mean(nets)), shuf_std=float(np.std(nets)),
                shuf_p95=float(np.percentile(nets, 95)), shuf_pf_mean=float(np.mean(pfs)),
                pct_rank=float((np.array(nets) < (C.evaluate(real, 3)["net"] if len(real) else 0)).mean()))


def main():
    coins = C.list_hl_coins()
    uni = C.hl_universe().set_index("coin")
    out_md = [f"# {STRAT} — results\n", "Entry MAKER limit at signal close (fill only if next bar trades through), exit TAKER. $1000 notional/trade, one position per coin.\n"]
    summary = {}
    for tf, cfg in CFG.items():
        print(f"\n=================== {tf} ===================")
        lo = min(bars(c, tf).index.min() for c in coins)
        hi = max(bars(c, tf).index.max() for c in coins)
        times = (lo, hi)
        bounds = C.fold_bounds(times, 3)
        grid = [dict(K=K, thr=thr, H=cfg["H"], tgt=0.5, vol_filter=1.0)
                for K, thr in itertools.product(cfg["Ks"], THRS)]

        def run_fn(p, s, e, tf=tf):
            return in_window(all_trades(tf, p, coins), s, e)

        best, oos_tr, table = C.walk_forward(grid, run_fn, times, n_folds=3, min_trades=10)
        oos = C.oos_result(oos_tr, times, 3)
        print(f"fold bounds: {[(str(a.date()), str(b.date())) for a, b in bounds]}")
        print(f"BEST (fold1): {best}")
        print("OOS (folds 2+3): " + fmt(oos))

        # in-sample grid + full-period folds, all recorded
        out_md.append(f"\n## {tf}  (data {lo.date()} -> {hi.date()}, folds {[str(a.date()) for a,_ in bounds]})\n")
        out_md.append(f"**Walk-forward best (fold 1):** `{best}`\n\n**OOS folds 2+3:** {fmt(oos)}\n")
        out_md.append("\n### In-sample grid (fold 1 metrics; fold nets over full period for transparency)\n")
        out_md.append("| K | thr | is_n | is_net | is_pf | is_wr | is_bps | f1 | f2 | f3 | sel |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for _, row in table.iterrows():
            p = json.loads(row["params"])
            full = C.evaluate(all_trades(tf, p, coins), 3, start=lo, end=hi)
            f = full["folds"]
            out_md.append(f"| {p['K']} | {p['thr']} | {row['is_n']} | {row['is_net']:.1f} | {row['is_pf']:.2f} | {row['is_wr']:.2f} | {row['is_net_bps']:.1f} | {f[0]:.1f} | {f[1]:.1f} | {f[2]:.1f} | {'*' if row['selected'] else ''} |")
            print(f"  grid K={p['K']} thr={p['thr']} IS: n={row['is_n']} net={row['is_net']:.1f} pf={row['is_pf']:.2f} bps={row['is_net_bps']:.1f} | full folds={[round(x,1) for x in f]} n={full['n']}")
            C.record_to_lab(STRAT, f"{tf}_K{p['K']}_z{p['thr']}_grid", "HL_basket50", tf, p, full,
                            period=times, source=SRC,
                            notes=f"grid cell, full period; fold1 (selection) net={row['is_net']:.2f} n={row['is_n']}; maker entry/taker exit")
        oos_id = C.record_to_lab(STRAT, f"{tf}_walkforward_oos", "HL_basket50", tf, best, oos, period=times,
                                 source=SRC, notes="HEADLINE walk-forward OOS folds 2+3; fold1 selection")

        # (a) shuffle
        sh = shuffle_test(tf, best, coins, times)
        print(f"SHUFFLE: real_oos_net={sh['real_net']:.1f} shuffled mean={sh['shuf_mean']:.1f} sd={sh['shuf_std']:.1f} p95={sh['shuf_p95']:.1f} pct_rank={sh['pct_rank']:.2f}")
        out_md.append(f"\n### Shuffle test (random signal timing, same fill/exit mechanics, OOS window, 30 reps)\nreal OOS net={sh['real_net']:.1f}; shuffled mean={sh['shuf_mean']:.1f} sd={sh['shuf_std']:.1f} p95={sh['shuf_p95']:.1f}; real percentile={sh['pct_rank']:.2f}\n")
        C.record_to_lab(STRAT, f"{tf}_shuffle_mean", "HL_basket50", tf, best,
                        dict(C.empty_result(), n=oos["n"], net=sh["shuf_mean"], pf=sh["shuf_pf_mean"]),
                        period=times, source=SRC, trust="synthetic", notes=f"mean of 30 shuffled-timing runs; sd={sh['shuf_std']:.2f} p95={sh['shuf_p95']:.2f}")

        # (c) neighbours: evaluate on OOS window only (no re-selection)
        oos_s, oos_e = bounds[1][0], bounds[-1][1]
        neigh = []
        variants = []
        for dK in (-1, 0, 1):
            K2 = best["K"] + dK * (1 if tf == "1h" else 3)
            if K2 < 1: continue
            for dthr in (-0.25, 0, 0.25):
                variants.append(dict(best, K=K2, thr=best["thr"] + dthr))
        for H2 in (max(1, best["H"] // 2), best["H"] * 2):
            variants.append(dict(best, H=H2))
        for tg in (None, 1.0):
            variants.append(dict(best, tgt=tg))
        for vf in (0.0, 1.5):
            variants.append(dict(best, vol_filter=vf))
        out_md.append("\n### Neighbouring parameters (OOS window folds 2+3, no re-selection)\n| K | thr | H | tgt | volf | n | net | pf | bps | f2 | f3 |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for v in variants:
            tr = in_window(all_trades(tf, v, coins), oos_s, oos_e)
            r = C.evaluate(tr, 3, start=lo, end=hi)
            neigh.append((v, r))
            print(f"  NEIGH {v}: " + fmt(r))
            out_md.append(f"| {v['K']} | {v['thr']} | {v['H']} | {v['tgt']} | {v['vol_filter']} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['net_bps']:.1f} | {r['folds'][1]:.1f} | {r['folds'][2]:.1f} |")
            C.record_to_lab(STRAT, f"{tf}_neigh_K{v['K']}_z{v['thr']}_H{v['H']}_t{v['tgt']}_v{v['vol_filter']}", "HL_basket50", tf, v, r,
                            period=times, source=SRC, notes="neighbour of WF-best, OOS window only")
        n_pos = sum(1 for _, r in neigh if r["net"] > 0)

        # (d) per coin, liquidity split
        per = []
        if len(oos_tr):
            t = C.add_pnl(oos_tr)
            g = t.groupby("instrument")["net_pnl"].agg(["count", "sum"])
            g["dayNtlVlm"] = [uni["dayNtlVlm"].get(c, np.nan) for c in g.index]
            g["illiquid"] = g["dayNtlVlm"] < 5e6
            g = g.sort_values("sum", ascending=False)
            liq = g[~g["illiquid"]]["sum"].sum(); ill = g[g["illiquid"]]["sum"].sum()
            print(f"PER-COIN OOS: liquid(>=5M) net={liq:.1f} (n={int(g[~g['illiquid']]['count'].sum())}), illiquid(<5M) net={ill:.1f} (n={int(g[g['illiquid']]['count'].sum())})")
            print(g.to_string())
            out_md.append(f"\n### Per-coin OOS\nliquid (24h vol >= $5M) net={liq:.1f} n={int(g[~g['illiquid']]['count'].sum())}; illiquid (< $5M) net={ill:.1f} n={int(g[g['illiquid']]['count'].sum())}\n")
            out_md.append("| coin | n | net | dayNtlVlm | illiquid |\n|---|---|---|---|---|")
            for coin, row in g.iterrows():
                out_md.append(f"| {coin} | {int(row['count'])} | {row['sum']:.1f} | {row['dayNtlVlm']/1e6:.1f}M | {row['illiquid']} |")
            C.record_to_lab(STRAT, f"{tf}_oos_liquid_only", "HL_liquid", tf, best,
                            C.evaluate(t[~t["instrument"].isin(g[g["illiquid"]].index)], 3, start=lo, end=hi),
                            period=times, source=SRC, notes="WF-best OOS trades, coins with dayNtlVlm>=5M only")
        summary[tf] = dict(best=best, oos=oos, shuffle=sh, neigh_pos=n_pos, neigh_total=len(neigh),
                           oos_id=oos_id, times=(str(lo), str(hi)))
    Path(__file__).with_suffix(".md").write_text("\n".join(out_md) + "\n")
    print("\nSUMMARY:", json.dumps({k: dict(best=v["best"], oos_net=v["oos"]["net"], oos_n=v["oos"]["n"], oos_pf=v["oos"]["pf"],
                                              folds=v["oos"]["folds"], shuffle=v["shuffle"], neigh=f"{v['neigh_pos']}/{v['neigh_total']}")
                                     for k, v in summary.items()}, default=str, indent=1))


if __name__ == "__main__":
    main()
