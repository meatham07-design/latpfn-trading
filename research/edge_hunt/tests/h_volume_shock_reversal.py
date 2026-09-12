"""Hypothesis: volume/wick shock reversal on Hyperliquid perps (5m / 15m).

Signal at bar t (all inputs known at the close of bar t):
  * usd_vol_t  > vol_x * median(usd_vol over the 100 PRIOR bars)
  * range_t    > rng_y * ATR14 (ATR over PRIOR bars, shifted by 1)
  * long wick against the move: lower_wick >= wick_w * range and lower wick >
    upper wick -> the move was a downside cascade that got rejected -> LONG.
    Mirror for upper wick -> SHORT.  (liquidation-cascade signature)
Execution (all TAKER):
  * entry at the OPEN of bar t+1 (market order)
  * stop  = wick extreme of bar t (long: low_t, short: high_t), filled at the
    stop price; if stop and target both touch in the same bar the stop is
    assumed to hit first (conservative)
  * target = entry +/- tgt * range_t
  * time stop: exit at the OPEN of bar t+1+H (H=12 bars)
  * $1000 notional per trade, one position per coin at a time.
Walk-forward: parameters chosen on fold 1 (earliest calendar third) only;
folds 2+3 are the headline out-of-sample result.
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C

STRAT = "volume_shock_reversal"
NOTIONAL = 1000.0
VOL_WIN = 100
ATR_WIN = 14
H_BARS = 12
SRC = "research/edge_hunt/tests/h_volume_shock_reversal.py"
TFS = ["15m", "5m"]   # 15m = headline (52d history), 5m = secondary (17d)

VOL_X = [4, 8]
RNG_Y = [2.0, 3.0]
WICK_W = [0.3, 0.5]
TGT = [0.5, 1.0]

_BARS: dict[tuple[str, str], pd.DataFrame] = {}


def bars(coin, tf):
    k = (coin, tf)
    if k not in _BARS:
        b = C.hl_candles(coin, tf)
        b = b[~b.index.duplicated()].copy()
        b["usd_vol"] = b["volume"] * b["close"]
        pc = b["close"].shift(1)
        tr = pd.concat([b["high"] - b["low"], (b["high"] - pc).abs(), (b["low"] - pc).abs()], axis=1).max(axis=1)
        b["atr"] = tr.rolling(ATR_WIN).mean().shift(1)          # prior bars only
        b["vmed"] = b["usd_vol"].rolling(VOL_WIN).median().shift(1)  # prior bars only
        b["vratio"] = b["usd_vol"] / b["vmed"]
        b["rng"] = b["high"] - b["low"]
        b["rratio"] = b["rng"] / b["atr"]
        body_lo = np.minimum(b["open"], b["close"]); body_hi = np.maximum(b["open"], b["close"])
        b["lw"] = body_lo - b["low"]
        b["uw"] = b["high"] - body_hi
        _BARS[k] = b
    return _BARS[k]


def signals(b: pd.DataFrame, vol_x, rng_y, wick_w):
    ok = (b["vratio"] > vol_x) & (b["rratio"] > rng_y) & (b["rng"] > 0) & np.isfinite(b["vratio"]) & np.isfinite(b["rratio"])
    lwf = b["lw"] / b["rng"]; uwf = b["uw"] / b["rng"]
    side = np.where((lwf >= wick_w) & (b["lw"] > b["uw"]), 1,
                    np.where((uwf >= wick_w) & (b["uw"] > b["lw"]), -1, 0))
    side = np.where(ok.values, side, 0)
    return np.flatnonzero(side != 0), side[side != 0]


def simulate(coin, tf, vol_x, rng_y, wick_w, tgt, H=H_BARS, sig_idx=None, sides=None):
    b = bars(coin, tf)
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    idx = b.index; n = len(b)
    if sig_idx is None:
        sig_idx, sides = signals(b, vol_x, rng_y, wick_w)
    trades = []; busy_until = -1
    for i, s in zip(sig_idx, sides):
        if i <= busy_until or i + 1 + H >= n:
            continue
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        entry_px = o[i + 1]
        stop = l[i] if s == 1 else h[i]
        target = entry_px + s * tgt * rng
        # if the next open already gapped through the stop, skip (no sensible fill)
        if (s == 1 and entry_px <= stop) or (s == -1 and entry_px >= stop):
            continue
        exit_j, exit_px, reason = i + 1 + H, o[i + 1 + H], "time"
        for j in range(i + 1, i + 1 + H):
            if (s == 1 and l[j] <= stop) or (s == -1 and h[j] >= stop):
                exit_j, exit_px, reason = j, stop, "stop"; break
            if (s == 1 and h[j] >= target) or (s == -1 and l[j] <= target):
                exit_j, exit_px, reason = j, target, "target"; break
        qty = NOTIONAL / entry_px
        tr = C.crypto_trade(idx[i + 1], idx[exit_j], int(s), float(entry_px), float(exit_px),
                            qty, coin, maker_entry=False, maker_exit=False)
        tr["reason"] = reason; tr["sig_time"] = idx[i]; tr["vratio"] = float(b["vratio"].values[i])
        tr["rratio"] = float(b["rratio"].values[i])
        trades.append(tr)
        busy_until = exit_j - 1
    return trades


_CACHE: dict[str, pd.DataFrame] = {}


def all_trades(tf, p, coins):
    key = json.dumps({"tf": tf, **p}, sort_keys=True)
    if key not in _CACHE:
        rows = []
        for coin in coins:
            rows.extend(simulate(coin, tf, p["vol_x"], p["rng_y"], p["wick_w"], p["tgt"], p.get("H", H_BARS)))
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
            f"sharpe={r['sharpe']:.2f} bps={r['net_bps']:.1f} folds={[round(f,1) for f in r['folds']]} fold_n={r['fold_n']}")


def pname(p):
    return f"v{p['vol_x']}_r{p['rng_y']}_w{p['wick_w']}_t{p['tgt']}_H{p.get('H', H_BARS)}"


def shuffle_test(tf, p, coins, times, n_rep=30, seed=0):
    """Random signal bars (same per-coin count in the OOS window, random side),
    identical entry/stop/target/time-stop mechanics using the random bar's own
    range and wick extreme."""
    rng = np.random.default_rng(seed)
    bounds = C.fold_bounds(times, 3)
    oos_s, oos_e = bounds[1][0], bounds[-1][1]
    real = in_window(all_trades(tf, p, coins), oos_s, oos_e)
    real_r = C.evaluate(real, 3, start=bounds[0][0], end=bounds[-1][1])
    counts = real.groupby("instrument").size().to_dict() if len(real) else {}
    nets, pfs = [], []
    H = p.get("H", H_BARS)
    for rep in range(n_rep):
        rows = []
        for coin, cnt in counts.items():
            b = bars(coin, tf); n = len(b)
            # restrict candidates to the OOS window so counts match
            pos = np.arange(VOL_WIN, n - H - 2)
            pos = pos[(b.index[pos + 1] >= oos_s) & (b.index[pos + 1] < oos_e)]
            k = min(len(pos), cnt * 3)
            cand = np.sort(rng.choice(pos, size=k, replace=False))
            sides = rng.choice([-1, 1], size=k)
            rows.extend(simulate(coin, tf, p["vol_x"], p["rng_y"], p["wick_w"], p["tgt"], H, sig_idx=cand, sides=sides))
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        df = in_window(df, oos_s, oos_e)
        if len(df) > len(real):
            df = df.sample(len(real), random_state=rep).sort_values("entry_time")
        r = C.evaluate(df, 3, start=bounds[0][0], end=bounds[-1][1])
        nets.append(r["net"]); pfs.append(r["pf"])
    nets = np.array(nets)
    return dict(real_net=float(real_r["net"]), real_n=int(real_r["n"]), shuf_mean=float(nets.mean()), shuf_std=float(nets.std()),
                shuf_p95=float(np.percentile(nets, 95)), shuf_pf_mean=float(np.mean(pfs)),
                pct_rank=float((nets < real_r["net"]).mean()))


def main():
    coins = [c for c in C.list_hl_coins() if (C.DATA / f"hl_{c}_15m.parquet").exists()]
    uni = C.hl_universe().set_index("coin")
    out = [f"# {STRAT} — results\n",
           "Volume shock (usd vol > X x trailing-100 median) + range > Y x ATR14 + long wick against the move -> fade at next open. "
           "All TAKER fills. Stop at wick extreme (stop assumed first when stop & target touch in the same bar), target = tgt x candle range, time stop 12 bars (exit at open of bar t+13). "
           "$1000 notional per trade, one position per coin. Headline timeframe = 15m (52d, folds ~17d); 5m (17d, folds ~6d) is secondary.\n"]
    summary = {}
    for tf in TFS:
        print(f"\n=================== {tf} ===================")
        lo = min(bars(c, tf).index.min() for c in coins); hi = max(bars(c, tf).index.max() for c in coins)
        times = (lo, hi); bounds = C.fold_bounds(times, 3)
        grid = [dict(vol_x=vx, rng_y=ry, wick_w=w, tgt=t, H=H_BARS)
                for vx, ry, w, t in itertools.product(VOL_X, RNG_Y, WICK_W, TGT)]

        def run_fn(p, s, e, tf=tf):
            return in_window(all_trades(tf, p, coins), s, e)

        best, oos_tr, table = C.walk_forward(grid, run_fn, times, n_folds=3, min_trades=10)
        oos = C.oos_result(oos_tr, times, 3)
        print(f"fold bounds: {[(str(a.date()), str(b.date())) for a, b in bounds]}")
        print(f"BEST (fold1): {best}")
        print("OOS (folds 2+3): " + fmt(oos))
        out.append(f"\n## {tf}  (data {lo.date()} -> {hi.date()}, fold starts {[str(a.date()) for a,_ in bounds]})\n")
        out.append(f"**Walk-forward best (fold 1):** `{best}`\n\n**OOS folds 2+3 (HEADLINE):** {fmt(oos)}\n")
        out.append("\n### In-sample grid (fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period, n=full-period trades)\n")
        out.append("| vol_x | rng_y | wick_w | tgt | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | sel |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, row in table.iterrows():
            p = json.loads(row["params"])
            full = C.evaluate(all_trades(tf, p, coins), 3, start=lo, end=hi); f = full["folds"]
            out.append(f"| {p['vol_x']} | {p['rng_y']} | {p['wick_w']} | {p['tgt']} | {row['is_n']} | {row['is_net']:.1f} | {row['is_pf']:.2f} | {row['is_wr']:.2f} | {row['is_net_bps']:.1f} | {full['n']} | {f[0]:.1f} | {f[1]:.1f} | {f[2]:.1f} | {'*' if row['selected'] else ''} |")
            print(f"  grid {pname(p)} IS: n={row['is_n']} net={row['is_net']:.1f} pf={row['is_pf']:.2f} bps={row['is_net_bps']:.1f} | full n={full['n']} folds={[round(x,1) for x in f]}")
            C.record_to_lab(STRAT, f"{tf}_grid_{pname(p)}", "HL_basket50", tf, p, full, period=times, source=SRC,
                            notes=f"grid cell, full period; fold1 (selection) net={row['is_net']:.2f} n={row['is_n']}; all taker")
        oos_id = C.record_to_lab(STRAT, f"{tf}_walkforward_oos", "HL_basket50", tf, best, oos, period=times, source=SRC,
                                 notes="HEADLINE walk-forward OOS folds 2+3; fold1 selection; all taker")

        # exit-reason / side breakdown (OOS)
        if len(oos_tr):
            t = C.add_pnl(oos_tr)
            br = t.groupby("reason")["net_pnl"].agg(["count", "sum"])
            bs = t.groupby("side")["net_pnl"].agg(["count", "sum"])
            print("OOS by exit reason:\n" + br.to_string()); print("OOS by side:\n" + bs.to_string())
            out.append("\n### OOS breakdown\nBy exit reason:\n\n| reason | n | net |\n|---|---|---|")
            out += [f"| {r} | {int(v['count'])} | {v['sum']:.1f} |" for r, v in br.iterrows()]
            out.append("\nBy side:\n\n| side | n | net |\n|---|---|---|")
            out += [f"| {'long' if s == 1 else 'short'} | {int(v['count'])} | {v['sum']:.1f} |" for s, v in bs.iterrows()]
            for s in (1, -1):
                C.record_to_lab(STRAT, f"{tf}_oos_{'long' if s == 1 else 'short'}_only", "HL_basket50", tf, best,
                                C.evaluate(t[t["side"] == s], 3, start=lo, end=hi), period=times, source=SRC, notes="WF-best OOS trades, one side only")

        # (a) shuffle
        sh = shuffle_test(tf, best, coins, times)
        print(f"SHUFFLE: real_oos_net={sh['real_net']:.1f} (n={sh['real_n']}) shuffled mean={sh['shuf_mean']:.1f} sd={sh['shuf_std']:.1f} p95={sh['shuf_p95']:.1f} pct_rank={sh['pct_rank']:.2f}")
        out.append(f"\n### Shuffle test (random signal bars, random side, same mechanics, OOS window, 30 reps)\nreal OOS net={sh['real_net']:.1f} (n={sh['real_n']}); shuffled mean={sh['shuf_mean']:.1f} sd={sh['shuf_std']:.1f} p95={sh['shuf_p95']:.1f}; real percentile among shuffles={sh['pct_rank']:.2f}\n")
        C.record_to_lab(STRAT, f"{tf}_shuffle_mean", "HL_basket50", tf, best,
                        dict(C.empty_result(), n=oos["n"], net=sh["shuf_mean"], pf=sh["shuf_pf_mean"]), period=times, source=SRC,
                        trust="synthetic", notes=f"mean of 30 shuffled-timing runs; sd={sh['shuf_std']:.2f} p95={sh['shuf_p95']:.2f}")

        # (c) neighbours on OOS window only
        oos_s, oos_e = bounds[1][0], bounds[-1][1]
        variants = []
        for vx in sorted({best["vol_x"] * 0.75, best["vol_x"] * 1.5}):
            variants.append(dict(best, vol_x=vx))
        for ry in (best["rng_y"] - 0.5, best["rng_y"] + 0.5):
            variants.append(dict(best, rng_y=ry))
        for w in (round(best["wick_w"] - 0.1, 2), round(best["wick_w"] + 0.1, 2)):
            variants.append(dict(best, wick_w=w))
        for tg in (best["tgt"] - 0.25, best["tgt"] + 0.25):
            variants.append(dict(best, tgt=tg))
        for H2 in (8, 16):
            variants.append(dict(best, H=H2))
        out.append("\n### Neighbouring parameters (OOS window folds 2+3, no re-selection)\n| vol_x | rng_y | wick_w | tgt | H | n | net | pf | wr | bps | f2 | f3 |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
        neigh = []
        for v in variants:
            r = C.evaluate(in_window(all_trades(tf, v, coins), oos_s, oos_e), 3, start=lo, end=hi)
            neigh.append((v, r))
            print(f"  NEIGH {pname(v)}: " + fmt(r))
            out.append(f"| {v['vol_x']} | {v['rng_y']} | {v['wick_w']} | {v['tgt']} | {v['H']} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['net_bps']:.1f} | {r['folds'][1]:.1f} | {r['folds'][2]:.1f} |")
            C.record_to_lab(STRAT, f"{tf}_neigh_{pname(v)}", "HL_basket50", tf, v, r, period=times, source=SRC, notes="neighbour of WF-best, OOS window only")
        n_pos = sum(1 for _, r in neigh if r["net"] > 0)

        # (d) per coin + liquidity, and hour-of-day concentration
        per_txt = ""
        if len(oos_tr):
            t = C.add_pnl(oos_tr)
            g = t.groupby("instrument")["net_pnl"].agg(["count", "sum"])
            g["dayNtlVlm"] = [uni["dayNtlVlm"].get(c, np.nan) for c in g.index]
            g["illiquid"] = g["dayNtlVlm"] < 5e6
            g = g.sort_values("sum", ascending=False)
            liq = g[~g["illiquid"]]["sum"].sum(); ill = g[g["illiquid"]]["sum"].sum()
            nl, ni = int(g[~g["illiquid"]]["count"].sum()), int(g[g["illiquid"]]["count"].sum())
            per_txt = f"liquid(>=5M) net={liq:.1f} n={nl}; illiquid(<5M) net={ill:.1f} n={ni}"
            print("PER-COIN OOS: " + per_txt); print(g.to_string())
            out.append(f"\n### Per-coin OOS\n{per_txt}\n\n| coin | n | net | dayNtlVlm | illiquid |\n|---|---|---|---|---|")
            out += [f"| {coin} | {int(r['count'])} | {r['sum']:.1f} | {r['dayNtlVlm']/1e6:.1f}M | {r['illiquid']} |" for coin, r in g.iterrows()]
            C.record_to_lab(STRAT, f"{tf}_oos_liquid_only", "HL_liquid", tf, best,
                            C.evaluate(t[~t["instrument"].isin(g[g["illiquid"]].index)], 3, start=lo, end=hi),
                            period=times, source=SRC, notes="WF-best OOS trades, coins with dayNtlVlm>=5M only")
            # hours (full period for the WF-best params: descriptive, where the pattern concentrates)
            tf_all = C.add_pnl(all_trades(tf, best, coins))
            hr = tf_all.assign(hour=pd.to_datetime(tf_all["sig_time"], utc=True).dt.hour).groupby("hour")["net_pnl"].agg(["count", "sum"])
            print("SIGNAL HOUR (UTC) concentration, full period:\n" + hr.to_string())
            out.append("\n### Signal hour (UTC) concentration, WF-best params, FULL period (descriptive only)\n| hour | n | net |\n|---|---|---|")
            out += [f"| {h:02d} | {int(r['count'])} | {r['sum']:.1f} |" for h, r in hr.iterrows()]
            top_hours = hr.sort_values("count", ascending=False).head(6)
            summary_hours = ", ".join(f"{h:02d}h n={int(r['count'])} net={r['sum']:.0f}" for h, r in top_hours.iterrows())
        else:
            summary_hours = ""
        summary[tf] = dict(best=best, oos=oos, shuffle=sh, neigh_pos=n_pos, neigh_total=len(neigh), oos_id=oos_id,
                           per_coin=per_txt, hours=summary_hours, times=(str(lo), str(hi)))
    Path(__file__).with_suffix(".md").write_text("\n".join(out) + "\n")
    js = {k: dict(best=v["best"], oos_net=v["oos"]["net"], oos_n=v["oos"]["n"], oos_pf=v["oos"]["pf"], oos_wr=v["oos"]["wr"],
                  oos_sharpe=v["oos"]["sharpe"], folds=v["oos"]["folds"], shuffle=v["shuffle"], neigh=f"{v['neigh_pos']}/{v['neigh_total']}",
                  per_coin=v["per_coin"], hours=v["hours"]) for k, v in summary.items()}
    Path(__file__).with_suffix(".json").write_text(json.dumps(js, default=str, indent=1))
    print("\nSUMMARY:", json.dumps(js, default=str, indent=1))


if __name__ == "__main__":
    main()
