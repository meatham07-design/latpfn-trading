"""Hypothesis range_edge_maker_fade (round 2): mean reversion at session
opening-range edges with RESTING MAKER limits (stop-cluster / liquidity-sweep
mechanism).  Execution-corrected version of round 1's ORB finding.

Sessions (UTC): 00:00 -> 08:00 and 13:30 -> 21:00 (15m data, opening range =
first 60 min = 4 bars, 52 days) ; 00:00 -> 08:00 and 13:00 -> 21:00 (1h data,
opening range = first 2 bars, 208 days; 13:30 does not align with 1h bars).

Mechanics (strictly causal):
  * range known at the CLOSE of the last range bar; limits live from the next bar.
  * sell limit at rh + k*width, buy limit at rl - k*width.  A fill is counted
    only if a later bar trades THROUGH the level by >= TT bps (queue priority).
  * one fill per side per session (both sides independent).
  * target = maker limit at range midpoint ('mid') or entry -/+ 0.5*width
    ('half'); also requires trade-through by TT bps.  stop = entry -/+ 1R
    (R = |entry - target|), taker.  time stop at session end open, taker.
  * momentum filter ('abort'): with a resting order you cannot "skip" a fill,
    so if the fill bar's range > 1 x opening range we exit at the NEXT bar's
    open (taker) - the honest equivalent of the hypothesis' "skip".
  * BTC trend filter: long fades only when BTC 1h close >= SMA24 (last
    COMPLETED 1h bar before the fill bar), short fades only when <=.
  * Funding (hourly) charged for every hour boundary inside the hold and added
    to fee_usd.
  * $1,000 notional per trade.  hl_maker on entry + target, hl_taker on stop /
    time / abort exits.

Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_range_edge_maker_fade.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

STRATEGY = "range_edge_maker_fade"
SRC = "tests/h_range_edge_maker_fade.py"
COINS = ["BTC", "ETH", "SOL", "HYPE", "XRP", "ZEC", "PUMP", "ENA", "DOGE", "SUI"]
NOTIONAL = 1_000.0
TT = 5e-4  # trade-through requirement for a maker fill (5 bps)

DATASETS = {
    # tf -> (bar, n_range_bars, sessions{key: (start, end)})
    "15m": dict(bar=pd.Timedelta(minutes=15), n_range=4,
                sessions={"00:00": ("00:00", "08:00"), "13:30": ("13:30", "21:00")}),
    "1h": dict(bar=pd.Timedelta(hours=1), n_range=2,
               sessions={"00:00": ("00:00", "08:00"), "13:00": ("13:00", "21:00")}),
}

# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
BARS = {tf: {c: C.hl_candles(c, tf) for c in COINS} for tf in DATASETS}
FUND = {}
for c in COINS:
    f = C.hl_funding(c)["fundingRate"].astype(float)
    FUND[c] = f
BTC1H = C.hl_candles("BTC", "1h")
_btc_close = BTC1H["close"].astype(float)
_btc_sma = _btc_close.rolling(24).mean()
# trend value indexed by bar CLOSE time (open + 1h) so asof(t) only sees completed bars
BTC_TREND = pd.Series(np.where(_btc_close >= _btc_sma, 1, -1), index=BTC1H.index + pd.Timedelta(hours=1))
BTC_TREND[_btc_sma.isna().values] = 0


def data_span(tf: str):
    b = BARS[tf]
    return max(x.index.min() for x in b.values()), min(x.index.max() for x in b.values())


def funding_cost(coin: str, entry_t, exit_t, side: int, notional: float) -> float:
    """USD funding paid (positive = cost) for hour boundaries in (entry_t, exit_t]."""
    f = FUND[coin]
    seg = f[(f.index > entry_t) & (f.index <= exit_t)]
    if len(seg) == 0:
        return 0.0
    # positive rate: longs pay shorts
    return float(side * seg.sum() * notional)


# ---------------------------------------------------------------------------
# simulation of one session, one side
# ---------------------------------------------------------------------------
def _sim_side(bars, i_live, i_e, side, level, width, p, bar, rng_level=None):
    """Rest a limit at `level` from bar i_live; return trade dict or None.
    side=-1: sell limit (fills when high trades through level upward)
    side=+1: buy limit (fills when low trades through level downward)."""
    hi = bars["high"].values
    lo = bars["low"].values
    op = bars["open"].values
    idx = bars.index
    fill_i = None
    for i in range(i_live, i_e):
        if side < 0 and hi[i] >= level * (1 + TT):
            fill_i = i
            break
        if side > 0 and lo[i] <= level * (1 - TT):
            fill_i = i
            break
    if fill_i is None:
        return None
    # gap through the level at the open -> a resting limit fills at the open price (better than level)
    entry_px = level
    if side < 0 and op[fill_i] > level:
        entry_px = float(op[fill_i])
    if side > 0 and op[fill_i] < level:
        entry_px = float(op[fill_i])
    entry_t = idx[fill_i]
    mid = p["_mid"]
    if p["target"] == "mid":
        target = mid
    else:  # 'half': 0.5*width back from entry
        target = entry_px + side * 0.5 * width
    R = abs(entry_px - target)
    if R <= 0:
        return None
    sm = p.get("stop_mult", 1.0)
    stop = entry_px - side * R * sm if sm is not None else (-1e18 if side > 0 else 1e18)
    # fill bar: stop can trigger (continuous path passed the level first); target not credited
    reason = None
    if (side > 0 and lo[fill_i] <= stop) or (side < 0 and hi[fill_i] >= stop):
        exit_t, exit_px, reason = idx[fill_i] + bar, stop, "stop"
    elif p["mom"] == "abort" and (hi[fill_i] - lo[fill_i]) > width:
        j = fill_i + 1
        if j >= i_e:
            exit_t, exit_px, reason = idx[i_e], float(op[i_e]), "time"
        else:
            exit_t, exit_px, reason = idx[j], float(op[j]), "abort"
    if reason is None:
        for i in range(fill_i + 1, i_e):
            if side > 0:
                if lo[i] <= stop:
                    exit_t, exit_px, reason = idx[i] + bar, stop, "stop"
                    break
                if hi[i] >= target * (1 + TT):
                    exit_t, exit_px, reason = idx[i] + bar, target, "target"
                    break
            else:
                if hi[i] >= stop:
                    exit_t, exit_px, reason = idx[i] + bar, stop, "stop"
                    break
                if lo[i] <= target * (1 - TT):
                    exit_t, exit_px, reason = idx[i] + bar, target, "target"
                    break
        else:
            exit_t, exit_px, reason = idx[i_e], float(op[i_e]), "time"
    qty = NOTIONAL / entry_px
    row = C.crypto_trade(entry_t, exit_t, side, entry_px, exit_px, qty, p["_coin"],
                         maker_entry=True, maker_exit=(reason == "target"))
    fund = funding_cost(p["_coin"], entry_t, exit_t, side, NOTIONAL)
    row["fee_usd"] = row["fee_usd"] + fund
    row.update(reason=reason, funding_usd=fund, session=p["_skey"], tf=p["_tf"],
               range_w_bps=width / entry_px * 1e4, R_bps=R / entry_px * 1e4,
               level_off=(entry_px - mid) / width)
    return row


def run_coin(tf: str, coin: str, p: dict, start, end, rng: np.random.Generator | None = None,
             shuffle_mode: str | None = None) -> list[dict]:
    """p: k, target ('mid'|'half'), mom ('none'|'abort'), trend (0|1).
    shuffle_mode 'level': limits at random distance from mid (u ~ U(0.2,1.0) widths).
    shuffle_mode 'time': random fill bar + random side, level = that bar's open, same target/stop geometry."""
    ds = DATASETS[tf]
    bar, n_range = ds["bar"], ds["n_range"]
    bars = BARS[tf][coin]
    idx = bars.index
    pos_map = {t: i for i, t in enumerate(idx)}
    hi, lo, op = bars["high"].values, bars["low"].values, bars["open"].values
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    days = pd.date_range(idx.min().normalize(), idx.max().normalize(), freq="D")
    pp = dict(p, _coin=coin, _tf=tf)
    for day in days:
        for skey, (s_str, e_str) in ds["sessions"].items():
            s_t = day + pd.Timedelta(hours=int(s_str[:2]), minutes=int(s_str[3:]))
            e_t = day + pd.Timedelta(hours=int(e_str[:2]), minutes=int(e_str[3:]))
            if s_t not in pos_map or e_t not in pos_map:
                continue
            i_s, i_e = pos_map[s_t], pos_map[e_t]
            if (i_e - i_s) != int((e_t - s_t) / bar):
                continue
            rh = hi[i_s:i_s + n_range].max()
            rl = lo[i_s:i_s + n_range].min()
            width = rh - rl
            if width <= 0:
                continue
            mid = 0.5 * (rh + rl)
            pp["_mid"], pp["_skey"] = mid, skey
            i_live = i_s + n_range
            if shuffle_mode == "time":
                i = int(rng.integers(i_live, i_e))
                side = int(rng.choice([-1, 1]))
                entry_px = float(op[i])
                t_px = mid if p["target"] == "mid" else entry_px + side * 0.5 * width
                R = abs(entry_px - t_px)
                if R <= 0 or not (start <= idx[i] < end):
                    continue
                stop = entry_px - side * R
                reason = None
                for j in range(i, i_e):
                    if side > 0:
                        if lo[j] <= stop:
                            exit_t, exit_px, reason = idx[j] + bar, stop, "stop"; break
                        if j > i and hi[j] >= t_px * (1 + TT):
                            exit_t, exit_px, reason = idx[j] + bar, t_px, "target"; break
                    else:
                        if hi[j] >= stop:
                            exit_t, exit_px, reason = idx[j] + bar, stop, "stop"; break
                        if j > i and lo[j] <= t_px * (1 - TT):
                            exit_t, exit_px, reason = idx[j] + bar, t_px, "target"; break
                if reason is None:
                    exit_t, exit_px, reason = idx[i_e], float(op[i_e]), "time"
                row = C.crypto_trade(idx[i], exit_t, side, entry_px, exit_px, NOTIONAL / entry_px, coin,
                                     maker_entry=True, maker_exit=(reason == "target"))
                row["fee_usd"] += funding_cost(coin, idx[i], exit_t, side, NOTIONAL)
                row.update(reason=reason, session=skey, tf=tf, range_w_bps=width / entry_px * 1e4,
                           R_bps=R / entry_px * 1e4, level_off=(entry_px - mid) / width, funding_usd=0.0)
                out.append(row)
                continue
            for side, edge in ((-1, rh), (+1, rl)):
                if shuffle_mode == "level":
                    u = float(rng.uniform(0.2, 1.0))
                    level = mid - side * u * width
                else:
                    level = edge - side * p["k"] * width
                if p.get("trend"):
                    tv = BTC_TREND.asof(idx[i_live])
                    if pd.isna(tv) or tv == 0 or int(tv) != side:
                        continue
                row = _sim_side(bars, i_live, i_e, side, level, width, pp, bar)
                if row is None or not (start <= row["entry_time"] < end):
                    continue
                out.append(row)
    return out


def make_run_fn(tf: str):
    def run_fn(p, start, end):
        rows = []
        for c in COINS:
            rows.extend(run_coin(tf, c, p, start, end))
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return run_fn


def shuffle_run(tf, p, start, end, seed, mode):
    rng = np.random.default_rng(seed)
    rows = []
    for c in COINS:
        rows.extend(run_coin(tf, c, p, start, end, rng=rng, shuffle_mode=mode))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)


# ---------------------------------------------------------------------------
GRID = [dict(k=k, target=tg, mom=m, trend=tr)
        for k in (0.0, 0.1, 0.25) for tg in ("mid", "half") for m in ("none", "abort") for tr in (0, 1)]  # 24


def vname(p):
    return f"k{p['k']}_{p['target']}_{p['mom']}_tr{p['trend']}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:8.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:.2f} "
            f"dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} folds={[round(f, 1) for f in r['folds']]}")


def run_dataset(tf: str, lines: list[str]) -> dict:
    ds = DATASETS[tf]
    bar = ds["bar"]
    d0, d1 = data_span(tf)
    times = (d0, d1)
    bounds = C.fold_bounds(times, 3)
    period = (d0, d1)
    inst = ",".join(COINS)
    run_fn = make_run_fn(tf)
    print(f"\n===== {tf}: {d0} -> {d1}  folds: " + "; ".join(f"{s:%m-%d}->{e:%m-%d}" for s, e in bounds))
    rep = C.full_report(GRID, run_fn, times, n_folds=3, min_trades=10)
    best, oos, oos_tr = rep["best_params"], rep["oos"], rep["oos_trades"]
    print("BEST(fold1):", best, "\nOOS:", fmt(oos))

    full_rows = []
    for i, p in enumerate(GRID):
        tr = run_fn(p, d0, d1 + bar)
        r = C.evaluate(tr, 3, start=bounds[0][0], end=bounds[-1][1])
        tr23 = tr[tr["entry_time"] >= bounds[1][0]] if len(tr) else tr
        r23 = C.evaluate(tr23, 3, start=bounds[0][0], end=bounds[-1][1])
        full_rows.append(dict(idx=i, variant=vname(p), n=r["n"], net=r["net"], pf=r["pf"], wr=r["wr"],
                              f1=r["folds"][0], f2=r["folds"][1], f3=r["folds"][2],
                              oos23_n=r23["n"], oos23_net=r23["net"], oos23_pf=r23["pf"]))
        C.record_to_lab(STRATEGY, f"{tf}_{vname(p)}_full", inst, tf, p, r, period=period, source=SRC,
                        notes="full period (grid cell); maker entry/target, taker stop/time/abort, funding incl; $1k")
        C.record_to_lab(STRATEGY, f"{tf}_{vname(p)}_oos23", inst, tf, p, r23, period=period, source=SRC,
                        notes="folds 2+3 of this cell (only the fold-1-selected cell is the honest OOS)")
    full = pd.DataFrame(full_rows)
    ins = rep["insample"].copy()
    ins["variant"] = [vname(p) for p in GRID]
    table = ins[["idx", "variant", "is_n", "is_net", "is_pf", "is_wr", "selected"]].merge(
        full[["idx", "f2", "f3", "oos23_n", "oos23_net", "oos23_pf"]], on="idx")
    pd.set_option("display.width", 220)
    print(table.to_string(index=False))
    C.record_to_lab(STRATEGY, f"{tf}_WF_selected_oos", inst, tf, best, oos, period=period, source=SRC,
                    notes=f"HEADLINE walk-forward OOS folds 2+3, selected on fold1: {vname(best)}")

    # (a) shuffles
    sh = {}
    for mode, reps in (("level", 200), ("time", 100)):
        nets = []
        for seed in range(reps):
            parts = [shuffle_run(tf, best, s, e, seed * 11 + k, mode) for k, (s, e) in enumerate(bounds[1:])]
            st = pd.concat(parts, ignore_index=True)
            nets.append(C.evaluate(st)["net"] if len(st) else 0.0)
        nets = np.array(nets)
        pct = float((nets < oos["net"]).mean())
        sh[mode] = dict(mean=float(nets.mean()), sd=float(nets.std()), p5=float(np.percentile(nets, 5)),
                        p95=float(np.percentile(nets, 95)), pct=pct, reps=reps)
        print(f"SHUFFLE[{mode}] mean={nets.mean():.1f} sd={nets.std():.1f} p5={np.percentile(nets,5):.1f} "
              f"p95={np.percentile(nets,95):.1f} real={oos['net']:.1f} pct={pct:.2f}")
        C.record_to_lab(STRATEGY, f"{tf}_shuffle_{mode}_mean", inst, tf, best,
                        dict(C.empty_result(), n=int(len(oos_tr)), net=float(nets.mean()), folds=[0, 0, 0]),
                        period=period, source=SRC, trust="synthetic",
                        notes=f"mean of {reps} {mode}-shuffled controls over folds 2+3; real OOS percentile={pct:.2f}")

    # (c) neighbours: same target/mom/trend, other k ; same k, other target
    nb_mask = table["variant"].apply(lambda v: v.endswith(f"_{best['mom']}_tr{best['trend']}"))
    nb = table[nb_mask & ~table["selected"]]
    print("NEIGHBOURS (same mom/trend):\n", nb[["variant", "is_net", "oos23_n", "oos23_net", "oos23_pf"]].to_string(index=False))

    # (d) breakdowns
    by = {}
    if len(oos_tr):
        t = C.add_pnl(oos_tr)
        by["coin"] = t.groupby("instrument")["net_pnl"].agg(["count", "sum"])
        by["session"] = t.groupby("session")["net_pnl"].agg(["count", "sum"])
        by["reason"] = t.groupby("reason")["net_pnl"].agg(["count", "sum"])
        by["side"] = t.groupby("side")["net_pnl"].agg(["count", "sum"])
        for k_, v in by.items():
            print(f"OOS by {k_}:\n{v}")
        print(f"avg range {t.range_w_bps.mean():.0f} bps, avg R {t.R_bps.mean():.0f} bps, "
              f"gross {oos['gross']:.1f} fees+funding {oos['fees']:.1f} funding {t.funding_usd.sum():.1f}")
        for c in COINS:
            rc = C.evaluate(oos_tr[oos_tr["instrument"] == c], 3, start=bounds[0][0], end=bounds[-1][1])
            C.record_to_lab(STRATEGY, f"{tf}_WF_selected_oos_percoin", c, tf, best, rc, period=period,
                            source=SRC, notes="per-coin slice of WF OOS")
        for sk in ds["sessions"]:
            rs = C.evaluate(oos_tr[oos_tr["session"] == sk], 3, start=bounds[0][0], end=bounds[-1][1])
            C.record_to_lab(STRATEGY, f"{tf}_WF_selected_oos_sess{sk}", inst, tf, best, rs, period=period,
                            source=SRC, notes="per-session slice of WF OOS")

    oos_folds = oos["folds"][1:]
    crit = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=oos["n"] >= 60,
                folds=all(f > 0 for f in oos_folds),
                shuffle=(sh["level"]["pct"] >= 0.95 and sh["time"]["pct"] >= 0.95),
                neighbors=bool(len(nb) and (nb["oos23_net"] > 0).mean() >= 0.5))
    verdict = "edge" if all(crit.values()) else ("weak" if oos["net"] > 0 else "none")
    print("CRITERIA:", crit, "->", verdict)

    # ---- markdown
    lines.append(f"\n## Dataset {tf} (range = first {ds['n_range']} bars; sessions {list(ds['sessions'].items())})\n")
    lines.append(f"Data {d0:%Y-%m-%d} -> {d1:%Y-%m-%d} UTC; folds " +
                 "; ".join(f"f{i+1} {s:%m-%d}->{e:%m-%d}" for i, (s, e) in enumerate(bounds)) + "\n")
    lines.append(f"### Walk-forward OOS (selected on fold 1: `{vname(best)}`, fold-1 net "
                 f"{float(ins.loc[ins.selected,'is_net'].iloc[0]):.2f}, n={int(ins.loc[ins.selected,'is_n'].iloc[0])})\n")
    lines.append("| n | net USD | gross | fees+fund | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |\n"
                 "|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    lines.append(f"| {oos['n']} | {oos['net']:.2f} | {oos['gross']:.2f} | {oos['fees']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | "
                 f"{oos['sharpe']:.2f} | {oos['max_dd']:.0f} | {oos['net_bps']:.1f} | {oos_folds[0]:.2f} | {oos_folds[1]:.2f} |\n")
    lines.append("### In-sample grid (fold 1) + each cell's fold-2/fold-3 net\n")
    lines.append("| variant | is_n | is_net | is_pf | is_wr | sel | f2 | f3 | f2+3 n | f2+3 net | f2+3 pf |\n"
                 "|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|--:|")
    for _, r in table.iterrows():
        lines.append(f"| {r.variant} | {r.is_n} | {r.is_net:.1f} | {r.is_pf:.2f} | {r.is_wr:.2f} | {'*' if r.selected else ''} | "
                     f"{r.f2:.1f} | {r.f3:.1f} | {r.oos23_n} | {r.oos23_net:.1f} | {r.oos23_pf:.2f} |")
    lines.append("\n### Sanity checks\n")
    for mode, s in sh.items():
        lines.append(f"- **Shuffle[{mode}]** ({s['reps']} reps): mean {s['mean']:.1f}, sd {s['sd']:.1f}, p5 {s['p5']:.1f}, "
                     f"p95 {s['p95']:.1f}; real OOS {oos['net']:.1f} at percentile {s['pct']:.2f}.")
    lines.append(f"- **Folds**: fold2 {oos_folds[0]:.1f}, fold3 {oos_folds[1]:.1f}.")
    lines.append("- **Neighbours** (same mom/trend, f2+3 net): " +
                 ", ".join(f"{r.variant}={r.oos23_net:.0f} (pf {r.oos23_pf:.2f})" for _, r in nb.iterrows()))
    if len(oos_tr):
        u = C.hl_universe().set_index("coin")
        lines.append("- **Per coin (OOS)**: " + ", ".join(
            f"{c}: n={int(by['coin'].loc[c,'count'])} net={by['coin'].loc[c,'sum']:.0f} (24h vol ${u.loc[c,'dayNtlVlm']/1e6:.0f}M)"
            for c in by["coin"].index) + ". No coin below $5M 24h volume.")
        lines.append("- **Per session (OOS)**: " + ", ".join(
            f"{s}: n={int(by['session'].loc[s,'count'])} net={by['session'].loc[s,'sum']:.0f}" for s in by["session"].index))
        lines.append("- **Per side (OOS)**: " + ", ".join(
            f"{'long' if s>0 else 'short'}: n={int(by['side'].loc[s,'count'])} net={by['side'].loc[s,'sum']:.0f}" for s in by["side"].index))
        lines.append("- **Exit reason (OOS)**: " + ", ".join(
            f"{s}: n={int(by['reason'].loc[s,'count'])} net={by['reason'].loc[s,'sum']:.0f}" for s in by["reason"].index))
        lines.append(f"- Avg range {t.range_w_bps.mean():.0f} bps, avg R {t.R_bps.mean():.0f} bps; gross {oos['gross']:.1f}, "
                     f"fees+funding {oos['fees']:.1f} (funding {t.funding_usd.sum():.1f}).")
    lines.append(f"\n**Verdict ({tf}): {verdict}** - criteria {json.dumps({k: bool(v) for k, v in crit.items()})}\n")
    return dict(tf=tf, best=best, oos=oos, oos_folds=oos_folds, verdict=verdict, crit=crit, shuffle=sh,
                insample_best_net=float(ins.loc[ins.selected, "is_net"].iloc[0]),
                table=table.to_dict("records"),
                by={k: v.reset_index().to_dict("records") for k, v in by.items()})


def main():
    lines = [f"# {STRATEGY} - resting maker fade of opening-range edges, HL perps, 10 coins\n",
             "Execution: sell limit at rh + k*w / buy limit at rl - k*w resting from the bar after the range "
             "completes; fill only if a bar trades THROUGH the level by >= 5 bps; maker fee 1.5 bps on entry and "
             "on the midpoint target (also trade-through 5 bps); taker 4.5 bps on stop (1R, R=|entry-target|), "
             "time stop (session-end open) and momentum-abort (fill bar range > opening range -> exit next open). "
             "Hourly funding charged. $1,000 per trade. One fill per side per session. "
             "HEADLINE = 15m / 60-min range (primary spec); 1h / 2-bar range is the long-sample check.\n"]
    res = {tf: run_dataset(tf, lines) for tf in ("15m", "1h")}
    # ---- POST-HOC DIAGNOSTIC (not part of the grid, not a result): stop width on the selected cell
    lines.append("\n## Post-hoc diagnostic (NOT a result): stop width on the fold-1-selected cell, full period\n")
    lines.append("| tf | stop | n | net | gross | PF | WR | folds | stop/target/time/abort n |\n|---|---|--:|--:|--:|--:|--:|---|---|")
    diag = {}
    for tf in ("15m", "1h"):
        best = res[tf]["best"]
        d0, d1 = data_span(tf)
        bounds = C.fold_bounds((d0, d1), 3)
        run_fn = make_run_fn(tf)
        for sm in (1.0, 2.0, 3.0, None):
            p = dict(best, stop_mult=sm)
            tr = run_fn(p, d0, d1 + DATASETS[tf]["bar"])
            r = C.evaluate(tr, 3, start=bounds[0][0], end=bounds[-1][1])
            rc = tr["reason"].value_counts().to_dict() if len(tr) else {}
            diag[f"{tf}_stop{sm}"] = dict(n=r["n"], net=r["net"], gross=r["gross"], pf=r["pf"], folds=r["folds"], reasons=rc)
            C.record_to_lab(STRATEGY, f"{tf}_diag_stopmult{sm}_{vname(best)}", ",".join(COINS), tf, p, r,
                            period=(d0, d1), source=SRC, notes="POST-HOC diagnostic on selected cell, full period (in-sample)")
            lines.append(f"| {tf} | {sm if sm else 'none'} | {r['n']} | {r['net']:.1f} | {r['gross']:.1f} | {r['pf']:.2f} | {r['wr']:.2f} | "
                         f"{[round(f) for f in r['folds']]} | {rc.get('stop',0)}/{rc.get('target',0)}/{rc.get('time',0)}/{rc.get('abort',0)} |")
            print(tf, sm, fmt(r), rc)
    res["diag_stop"] = diag
    Path(__file__).with_suffix(".md").write_text("\n".join(lines))
    (ROOT / "tests" / "h_range_edge_maker_fade_result.json").write_text(json.dumps(res, default=str, indent=1))
    return res


if __name__ == "__main__":
    main()
