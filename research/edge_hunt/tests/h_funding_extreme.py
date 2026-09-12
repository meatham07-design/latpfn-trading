#!/usr/bin/env python
"""Hypothesis funding_extreme (edge-hunt round 1).

Funding-rate dislocation on Hyperliquid perps: when the hourly funding rate (or
its 8h / 24h mean) sits in an extreme percentile of its own trailing 30-day
distribution, take the contrarian side (short when funding is very positive,
long when very negative) at the next candle open, hold N hours, and book the
funding cash flows.  Also a "carry" variant: same trigger, exit when funding
normalises (rank back below the trailing median or sign flip; 168h cap).

Causality
---------
* Funding print f[H] is the rate PAID at H and is fully determined by the
  premium sampled during [H-1h, H) - i.e. by the bar that CLOSES at H.  The
  entry is at the open of the bar that STARTS at H ("next bar open").  The API
  timestamps of funding prints carry a 10-60 ms offset past the hour; those
  are floored to the hour.  A strictly-lagged variant (fill at open[H+1h]) is
  run as a robustness check.
* Funding cash flows are counted only for prints strictly after entry and
  strictly before exit (H+1 .. H+N-1); the print coinciding with exit is not
  credited.  Cash = -side * rate * qty * open[t]  (short receives positive
  funding, long pays it).
* Funding PnL is folded into evaluate() by adjusting exit_px:
  exit_px = exit_px_raw + side * funding_usd / qty.  Fees are computed from the
  RAW prices via common.crypto_trade (taker 4.5 bps / maker 1.5 bps per side).
* Maker mode: limit at open[H]; counted as filled ONLY if the bar traded
  through the limit (buy: low < open, sell: high > open); otherwise no trade.
  Exit is always taker.

Sizing: flat $1,000 notional per trade, one open position per coin at a time,
all 50 cached coins concurrently.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/molt_bot/latpfn-trading/research/edge_hunt")
import common as C  # noqa: E402

OUT_MD = Path("/Users/molt_bot/latpfn-trading/research/edge_hunt/tests/h_funding_extreme.md")
STRATEGY = "funding_extreme"
WINDOW = 720          # trailing hours for the percentile rank (30 days)
MIN_OBS = 240         # min observations before a rank is valid
NOTIONAL = 1000.0     # USD per trade
DEFAULT_RATE = 1.25e-5  # HL default (clamped) hourly funding - must be exceeded
CARRY_MAX_HOLD = 168
ILLIQ_USD = 5e6       # 24h notional volume threshold for "illiquid"
SEED = 7

# Fold period: signals need a 30d warm-up (data starts 2026-01-31) -> pin the
# evaluation window so all variants share fold edges.
PERIOD = (pd.Timestamp("2026-03-02", tz="UTC"), pd.Timestamp("2026-08-27 22:00", tz="UTC"))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_coin(coin: str) -> pd.DataFrame | None:
    c = C.hl_candles(coin, "1h")
    f = C.hl_funding(coin)
    f = f.copy()
    f.index = f.index.floor("h")
    f = f[~f.index.duplicated(keep="last")]
    df = c.join(f[["fundingRate"]], how="left")
    df = df[df["fundingRate"].notna()].copy()
    if len(df) < MIN_OBS + 48:
        return None
    # verify the hourly index is regular where we use positional offsets
    df["hour_pos"] = ((df.index - df.index[0]) / pd.Timedelta(hours=1)).astype(int)
    fr = df["fundingRate"]
    df["m1"] = fr
    df["m8"] = fr.rolling(8, min_periods=8).mean()
    df["m24"] = fr.rolling(24, min_periods=24).mean()
    for m in ("m1", "m8", "m24"):
        df[f"rk_{m}"] = df[m].rolling(WINDOW, min_periods=MIN_OBS).rank(pct=True)
    df["vol_usd_24h"] = (df["volume"] * df["close"]).rolling(24, min_periods=1).sum()
    df["coin"] = coin
    return df


def load_all() -> dict[str, pd.DataFrame]:
    out = {}
    for coin in C.list_hl_coins():
        try:
            d = load_coin(coin)
        except FileNotFoundError:
            continue
        if d is not None:
            out[coin] = d
    return out


# ---------------------------------------------------------------------------
# Signal + trade construction
# ---------------------------------------------------------------------------
def candidate_signals(df: pd.DataFrame, measure: str, pct: float) -> np.ndarray:
    """+1 (long) / -1 (short) / 0 per row.  Contrarian to funding."""
    m = df[measure].values
    rk = df[f"rk_{measure}"].values
    sig = np.zeros(len(df), dtype=int)
    short = (rk >= 1 - pct) & (m > DEFAULT_RATE)
    long_ = (rk <= pct) & (m < -DEFAULT_RATE)
    sig[short] = -1
    sig[long_] = 1
    return sig


def build_trades(data: dict[str, pd.DataFrame], measure: str, pct: float, hold: int | None,
                 mode: str = "taker", lag: int = 0, carry: bool = False) -> pd.DataFrame:
    """hold=None with carry=True -> exit on normalisation."""
    rows = []
    for coin, df in data.items():
        sig = candidate_signals(df, measure, pct)
        idx = np.flatnonzero(sig != 0)
        if len(idx) == 0:
            continue
        o = df["open"].values
        hi = df["high"].values
        lo = df["low"].values
        fr = df["fundingRate"].values
        rk = df[f"rk_{measure}"].values
        mv = df[measure].values
        hp = df["hour_pos"].values
        vol = df["vol_usd_24h"].values
        times = df.index
        n = len(df)
        busy_until = -1
        for i in idx:
            e = i + lag
            if e <= busy_until or e >= n:
                continue
            # require contiguous hourly bars from signal to entry
            if hp[e] - hp[i] != lag:
                continue
            side = int(sig[i])
            if mode == "maker":
                filled = (lo[e] < o[e]) if side > 0 else (hi[e] > o[e])
                if not filled:
                    continue
            # exit index
            if carry:
                x = None
                for t in range(e + 1, min(e + CARRY_MAX_HOLD, n - 1) + 1):
                    if hp[t] - hp[e] != t - e:
                        break
                    normal = (rk[t] < 0.5) if side < 0 else (rk[t] > 0.5)
                    flipped = (mv[t] <= 0) if side < 0 else (mv[t] >= 0)
                    if normal or flipped or (t - e) >= CARRY_MAX_HOLD:
                        x = t
                        break
                if x is None:
                    continue
            else:
                x = e + hold
                if x >= n or hp[x] - hp[e] != hold:
                    continue
            qty = NOTIONAL / o[e]
            # funding prints strictly inside (entry, exit)
            sl = slice(e + 1, x)
            funding_usd = float(-side * np.sum(fr[sl] * qty * o[sl]))
            tr = C.crypto_trade(times[e], times[x], side, float(o[e]), float(o[x]), qty, coin,
                                maker_entry=(mode == "maker"), maker_exit=False)
            tr["exit_px_raw"] = tr["exit_px"]
            tr["funding_usd"] = funding_usd
            tr["exit_px"] = tr["exit_px_raw"] + side * funding_usd / qty
            tr["coin"] = coin
            tr["measure_val"] = float(mv[i])
            tr["rank"] = float(rk[i])
            tr["vol_usd_24h"] = float(vol[i])
            tr["signal_time"] = times[i]
            rows.append(tr)
            busy_until = x
    if not rows:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def slice_trades(tr: pd.DataFrame, start, end) -> pd.DataFrame:
    if len(tr) == 0:
        return tr
    et = pd.to_datetime(tr["entry_time"], utc=True)
    return tr[(et >= start) & (et < end)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def vname(mode: str, p: dict, prefix: str = "") -> str:
    h = p.get("hold")
    return f"{prefix}{mode}_m{p['measure'][1:]}_p{int(p['pct'] * 100)}_" + (f"h{h}" if h else "carry")


def fmt_res(r: dict) -> str:
    return (f"n={r['n']} net={r['net']:.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.2f} bps={r['net_bps']:.1f} "
            f"folds={[round(f, 2) for f in r['folds']]}")


def md_table(df: pd.DataFrame, cols: list[str], floats: int = 2) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                vals.append(f"{v:.{floats}f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def run_walk_forward(cache: dict, grid: list[dict], mode: str, label: str, log: list[str],
                     rec_prefix: str = "") -> dict:
    """walk_forward over `grid` using pre-built trade tables in cache[(mode, key)]."""
    def run_fn(p, start, end):
        return slice_trades(cache[(mode, json.dumps(p, sort_keys=True))], start, end)

    best, oos, table = C.walk_forward(grid, run_fn, PERIOD, n_folds=3, select_by="net", min_trades=10)
    res = C.oos_result(oos, PERIOD, 3)
    # full-period per-cell results (3 folds) for sensitivity + lab recording
    full_rows = []
    for i, p in enumerate(grid):
        tr = cache[(mode, json.dumps(p, sort_keys=True))]
        r = C.evaluate(slice_trades(tr, *PERIOD), 3, *PERIOD)
        full_rows.append(dict(idx=i, variant=vname(mode, p, rec_prefix), n=r["n"], net=r["net"], pf=r["pf"],
                              wr=r["wr"], sharpe=r["sharpe"], bps=r["net_bps"],
                              f1=r["folds"][0], f2=r["folds"][1], f3=r["folds"][2],
                              oos23=r["folds"][1] + r["folds"][2]))
        C.record_to_lab(STRATEGY, vname(mode, p, rec_prefix), "HL_ALL", "1h", dict(p, mode=mode), r,
                        period=PERIOD, source="tests/h_funding_extreme.py",
                        notes=f"grid cell, full period 3 folds, {label}; fold1=in-sample selection fold")
    full = pd.DataFrame(full_rows)
    table = table.merge(full, on="idx")
    C.record_to_lab(STRATEGY, f"{rec_prefix}{mode}_WF_OOS", "HL_ALL", "1h", dict(best or {}, mode=mode), res,
                    period=PERIOD, source="tests/h_funding_extreme.py",
                    notes=f"walk-forward OOS folds 2+3 (fold1 selection), {label}; best={best}")
    log.append(f"\n### {label} ({mode})\nbest (fold-1 selected): `{best}`\n")
    log.append(f"OOS (folds 2+3): {fmt_res(res)}\n")
    log.append(md_table(table.sort_values("is_net", ascending=False),
                        ["variant", "is_n", "is_net", "is_pf", "is_wr", "n", "net", "pf", "f1", "f2", "f3", "oos23", "selected"]))
    print(f"[{label}/{mode}] best={best} OOS {fmt_res(res)}")
    return dict(best=best, oos=res, oos_trades=oos, table=table)


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
def shuffle_test(data: dict, oos_trades: pd.DataFrame, p: dict, n_rep: int = 200) -> dict:
    """Keep the number of OOS trades per coin, their sides and hold, but place
    them at random hours inside the OOS window. Null distribution of net."""
    rng = np.random.default_rng(SEED)
    bounds = C.fold_bounds(PERIOD, 3)
    s, e = bounds[1][0], bounds[2][1]
    hold = p["hold"]
    per_coin = oos_trades.groupby("coin")["side"].apply(list).to_dict()
    nets = []
    for _ in range(n_rep):
        rows = []
        for coin, sides in per_coin.items():
            df = data[coin]
            times = df.index
            ok = np.flatnonzero((times >= s) & (times < e) & (np.arange(len(df)) + hold < len(df)))
            if len(ok) == 0:
                continue
            o = df["open"].values
            fr = df["fundingRate"].values
            hp = df["hour_pos"].values
            picks = rng.choice(ok, size=len(sides), replace=False) if len(ok) >= len(sides) else rng.choice(ok, size=len(sides))
            for side, ei in zip(sides, picks):
                x = ei + hold
                if hp[x] - hp[ei] != hold:
                    continue
                qty = NOTIONAL / o[ei]
                sl = slice(ei + 1, x)
                fund = float(-side * np.sum(fr[sl] * qty * o[sl]))
                tr = C.crypto_trade(times[ei], times[x], side, float(o[ei]), float(o[x]), qty, coin)
                tr["exit_px"] = tr["exit_px"] + side * fund / qty
                rows.append(tr)
        nets.append(C.evaluate(pd.DataFrame(rows))["net"] if rows else 0.0)
    nets = np.array(nets)
    actual = C.evaluate(oos_trades)["net"] if len(oos_trades) else 0.0
    return dict(actual=float(actual), null_mean=float(nets.mean()), null_sd=float(nets.std()),
                null_p95=float(np.quantile(nets, 0.95)), p_value=float((nets >= actual).mean()), n_rep=n_rep)


def neighbor_check(cache: dict, mode: str, best: dict, measures, pcts, holds) -> pd.DataFrame:
    rows = []
    for p in itertools.product(measures, pcts, holds):
        q = dict(measure=p[0], pct=p[1], hold=p[2])
        dist = int(q["measure"] != best["measure"]) + int(q["pct"] != best["pct"]) + int(q["hold"] != best["hold"])
        if dist > 1:
            continue
        tr = cache[(mode, json.dumps(q, sort_keys=True))]
        r = C.evaluate(slice_trades(tr, *PERIOD), 3, *PERIOD)
        rows.append(dict(variant=vname(mode, q), dist=dist, n=r["n"], f1=r["folds"][0], f2=r["folds"][1],
                         f3=r["folds"][2], oos23=r["folds"][1] + r["folds"][2], pf=r["pf"]))
    return pd.DataFrame(rows).sort_values(["dist", "variant"])


def per_coin(oos_trades: pd.DataFrame) -> pd.DataFrame:
    t = C.add_pnl(oos_trades)
    g = t.groupby("coin").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), funding=("funding_usd", "sum"),
                              wr=("net_pnl", lambda x: (x > 0).mean()), vol24=("vol_usd_24h", "median"))
    g["illiquid"] = g["vol24"] < ILLIQ_USD
    return g.sort_values("net", ascending=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    data = load_all()
    print(f"loaded {len(data)} coins in {time.time() - t0:.1f}s")
    measures = ["m1", "m8", "m24"]
    pcts = [0.05, 0.10]
    holds = [4, 8, 24, 48]
    grid = [dict(measure=m, pct=p, hold=h) for m, p, h in itertools.product(measures, pcts, holds)]
    carry_grid = [dict(measure=m, pct=p) for m, p in itertools.product(measures, pcts)]

    cache = {}
    for mode in ("taker", "maker"):
        for p in grid:
            cache[(mode, json.dumps(p, sort_keys=True))] = build_trades(data, p["measure"], p["pct"], p["hold"], mode=mode)
        for p in carry_grid:
            cache[(f"carry_{mode}", json.dumps(p, sort_keys=True))] = build_trades(data, p["measure"], p["pct"], None, mode=mode, carry=True)
    print(f"built {len(cache)} trade tables in {time.time() - t0:.1f}s")

    log = ["# funding_extreme - results", "",
           f"Data: Hyperliquid 1h candles + hourly funding, {len(data)} coins, evaluation window "
           f"{PERIOD[0].date()} -> {PERIOD[1].date()} (3 chronological folds of ~59d). $1,000 notional/trade, "
           f"one position per coin. Trailing rank window {WINDOW}h; signal requires |measure| > default {DEFAULT_RATE:.2e}/h. "
           f"Funding cash flows included (folded into exit_px). Fees: taker 4.5 bps/side; maker 1.5 bps entry (fill only if bar traded through the open) + taker exit.",
           ""]

    # fixed-hold walk-forwards
    wf = {}
    for mode in ("taker", "maker"):
        wf[mode] = run_walk_forward(cache, grid, mode, "fixed-hold", log)
    # carry walk-forwards (cache key uses carry_ prefix)
    wf_c = {}
    for mode in ("taker", "maker"):
        wf_c[mode] = run_walk_forward(cache, carry_grid, f"carry_{mode}", "carry (exit on normalisation)", log)

    # ------------------------------------------------------------------ sanity
    best = wf["taker"]["best"]
    oos_tr = wf["taker"]["oos_trades"]
    log.append("\n## Sanity checks (taker, fixed-hold best params)\n")

    # (a) shuffle
    sh = shuffle_test(data, oos_tr, best) if len(oos_tr) else dict(actual=0, null_mean=0, null_sd=0, null_p95=0, p_value=1.0, n_rep=0)
    log.append(f"(a) Shuffle test ({sh['n_rep']} reps, random entry hours, same coins/sides/hold in OOS window): "
               f"actual OOS net={sh['actual']:.2f}, null mean={sh['null_mean']:.2f}, null sd={sh['null_sd']:.2f}, "
               f"null p95={sh['null_p95']:.2f}, p(null >= actual)={sh['p_value']:.3f}\n")
    print("shuffle:", sh)

    # (b) fold consistency
    r = wf["taker"]["oos"]
    log.append(f"(b) OOS folds 2/3 (taker): {r['folds'][1]:.2f} / {r['folds'][2]:.2f}, n={r['fold_n'][1]}/{r['fold_n'][2]}; "
               f"maker: {wf['maker']['oos']['folds'][1]:.2f} / {wf['maker']['oos']['folds'][2]:.2f}\n")

    # (c) neighbours
    nb = neighbor_check(cache, "taker", best, measures, pcts, holds)
    log.append("(c) Neighbouring parameters (full-period folds; oos23 = folds 2+3):\n")
    log.append(md_table(nb, ["variant", "dist", "n", "f1", "f2", "f3", "oos23", "pf"]))
    print(nb.to_string())

    # (d) per-coin / liquidity
    if len(oos_tr):
        pc = per_coin(oos_tr)
        liq = pc.groupby("illiquid").agg(coins=("n", "size"), n=("n", "sum"), net=("net", "sum"))
        log.append("\n(d) OOS per-coin breakdown (taker best):\n")
        log.append(md_table(pc.reset_index(), ["coin", "n", "net", "funding", "wr", "vol24", "illiquid"]))
        log.append("\nLiquidity split (median 24h notional at signal < $5M = illiquid):\n")
        log.append(md_table(liq.reset_index(), ["illiquid", "coins", "n", "net"]))
        print(pc.to_string())
        print(liq)
        # side split + funding vs price attribution
        t = C.add_pnl(oos_tr)
        side_split = t.groupby("side").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), funding=("funding_usd", "sum"))
        price_only = float((t["side"] * (t["exit_px_raw"] - t["entry_px"]) * t["qty"]).sum())
        log.append(f"\nAttribution (OOS): price-only gross={price_only:.2f}, funding={t['funding_usd'].sum():.2f}, "
                   f"fees={t['fee_usd'].sum():.2f}, net={t['net_pnl'].sum():.2f}\n")
        log.append(md_table(side_split.reset_index(), ["side", "n", "net", "funding"]))
        print(side_split, price_only)
        liquid_only = t[t["vol_usd_24h"] >= ILLIQ_USD]
        rl = C.evaluate(liquid_only, 3, *PERIOD)
        log.append(f"\nLiquid-only OOS (24h vol >= $5M at signal): {fmt_res(rl)}\n")
        C.record_to_lab(STRATEGY, "taker_WF_OOS_liquid_only", "HL_LIQUID", "1h", dict(best, mode="taker", min_vol=ILLIQ_USD),
                        rl, period=PERIOD, source="tests/h_funding_extreme.py", notes="OOS trades restricted to vol24>=5M")

    # (e) strict 1-bar lag on best params
    lag_tr = build_trades(data, best["measure"], best["pct"], best["hold"], mode="taker", lag=1)
    rlag = C.evaluate(slice_trades(lag_tr, *PERIOD), 3, *PERIOD)
    C.record_to_lab(STRATEGY, vname("taker", best, "lag1_"), "HL_ALL", "1h", dict(best, mode="taker", lag=1), rlag,
                    period=PERIOD, source="tests/h_funding_extreme.py", notes="entry delayed one full bar after funding print")
    log.append(f"\n(e) Strict 1-bar-lag entry (fill at open[H+1h]) on best params, full period: {fmt_res(rlag)}\n")
    print("lag1:", fmt_res(rlag))

    # (f) price-only (no funding credited) on best params
    t_all = C.add_pnl(slice_trades(cache[("taker", json.dumps(best, sort_keys=True))], *PERIOD))
    t_po = t_all.copy(); t_po["exit_px"] = t_po["exit_px_raw"]
    rpo = C.evaluate(t_po, 3, *PERIOD)
    log.append(f"(f) Price-only (funding NOT credited), best params, full period: {fmt_res(rpo)}\n")
    C.record_to_lab(STRATEGY, vname("taker", best, "priceonly_"), "HL_ALL", "1h", dict(best, mode="taker", funding=False), rpo,
                    period=PERIOD, source="tests/h_funding_extreme.py", notes="funding cash flows excluded")

    # ---------------------------------------------------------------- verdict
    r = wf["taker"]["oos"]
    crit = dict(net_pos=r["net"] > 0, pf=r["pf"] >= 1.2, n=r["n"] >= 60,
                folds=all(f > 0 for f in r["folds"][1:]), shuffle=sh["p_value"] < 0.05,
                neighbors=bool(len(nb) and (nb["oos23"] > 0).mean() >= 0.6))
    if all(crit.values()):
        verdict = "edge"
    elif crit["net_pos"]:
        verdict = "weak"
    else:
        verdict = "none"
    log.append(f"\n## Verdict: **{verdict}**\n\ncriteria: `{crit}`\n")
    summary = dict(verdict=verdict, criteria=crit, best=best, oos=r, maker_oos=wf["maker"]["oos"],
                   carry_taker_oos=wf_c["taker"]["oos"], carry_maker_oos=wf_c["maker"]["oos"],
                   shuffle=sh, lag1=rlag, price_only=rpo,
                   insample_best=float(wf["taker"]["table"].sort_values("is_net", ascending=False).iloc[0]["is_net"]))
    OUT_MD.write_text("\n".join(log))
    (OUT_MD.with_suffix(".json")).write_text(json.dumps(summary, default=str, indent=1))
    print(f"\nVERDICT={verdict} crit={crit}\nwrote {OUT_MD} ({time.time() - t0:.0f}s)")
    return summary


if __name__ == "__main__":
    main()
