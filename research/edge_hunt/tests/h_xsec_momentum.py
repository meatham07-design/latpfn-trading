"""Round 1 / key=xsec_momentum

Cross-sectional momentum vs reversal across the Hyperliquid perp universe.

Signal (computed at the close of the last 1h bar before the rebalance time,
00:00 UTC): trailing L-day return of each coin's daily close (close of the
23:00 bar).  Rank; long the top q-quantile, short the bottom q-quantile,
equal-dollar per name ($1,000 notional per position -> market neutral).
Fill at the OPEN of the next 1h bar (00:00 bar open) -> strictly causal.
Hold until the next rebalance (every R days) where the book is re-formed at
the next 00:00 bar open.  If a coin stays in the same bucket across a
rebalance the position is kept (no churn) - turnover is reported.

Fees: Hyperliquid TAKER both sides (0.045%/side).  Funding: hourly funding
history summed over the hold; longs pay positive funding, shorts receive.
Funding is folded into the trade's exit price (exit_px_adj) so that
common.evaluate() gross includes it; exit_px_raw / funding_usd columns are
kept for audit.

Walk-forward: parameters selected on fold 1 (calendar first third) only,
OOS reported on folds 2+3.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

OUT_MD = ROOT / "tests" / "h_xsec_momentum.md"
STRATEGY = "xsec_momentum"
NOTIONAL_PER_NAME = 1000.0      # USD per position (equal-dollar)
ILLIQ_USD = 5e6                 # 24h notional volume threshold for "illiquid"
RNG = np.random.default_rng(7)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_panel():
    coins = C.list_hl_coins()
    opens, closes, vols = {}, {}, {}
    fund = {}
    for c in coins:
        b = C.hl_candles(c, "1h")
        b = b[~b.index.duplicated(keep="last")]
        opens[c] = b["open"]
        closes[c] = b["close"]
        vols[c] = b["volume"] * b["close"]
        try:
            f = C.hl_funding(c)
            f.index = f.index.floor("h")
            f = f[~f.index.duplicated(keep="last")]["fundingRate"].astype(float)
            fund[c] = f
        except FileNotFoundError:
            fund[c] = pd.Series(dtype=float)
    O = pd.DataFrame(opens).sort_index()
    Cl = pd.DataFrame(closes).sort_index()
    V = pd.DataFrame(vols).sort_index()
    F = pd.DataFrame(fund).sort_index().reindex(O.index).fillna(0.0)
    return O, Cl, V, F


O, CL, VOLUSD, FUND = load_panel()
COINS = list(O.columns)
HOURS = O.index
# daily decision points: 00:00 UTC bar opens (fill bar). Signal uses the close
# of the previous bar (23:00 bar) which is the last information available.
DAY_OPENS = HOURS[(HOURS.hour == 0)]
# daily close series aligned to the decision (fill) bar: close of the bar
# immediately before each 00:00 open.
_pos = HOURS.get_indexer(DAY_OPENS) - 1
DAILY_CLOSE = pd.DataFrame(CL.values[_pos], index=DAY_OPENS, columns=COINS)
DAILY_CLOSE[_pos < 0] = np.nan
FUND_CUM = FUND.cumsum()   # cumulative hourly funding, for fast interval sums

UNIV = C.hl_universe().set_index("coin")
DAY_VLM = UNIV["dayNtlVlm"].reindex(COINS)
ILLIQ = set(DAY_VLM[DAY_VLM < ILLIQ_USD].index)

PERIOD = (HOURS[0], HOURS[-1])


def funding_usd(coin, side, notional, t_entry, t_exit):
    """Funding PnL in USD for a position open over (t_entry, t_exit].
    Positive fundingRate => longs pay.  side=+1 long."""
    cum = FUND_CUM[coin]
    a = cum.asof(t_entry) if t_entry >= cum.index[0] else 0.0
    b = cum.asof(t_exit) if t_exit >= cum.index[0] else 0.0
    a = 0.0 if pd.isna(a) else a
    b = 0.0 if pd.isna(b) else b
    return -side * notional * (b - a)


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[pd.DataFrame, dict]] = {}


def build_trades(params: dict) -> tuple[pd.DataFrame, dict]:
    """Full-period trade list for one parameter set + diagnostics."""
    key = json.dumps(params, sort_keys=True)
    if key in _CACHE:
        return _CACHE[key]
    L = int(params["lookback_d"])
    R = int(params["rebal_d"])
    q = float(params["quantile"])
    direction = 1 if params["mode"] == "mom" else -1
    shuffle = params.get("_shuffle", 0)
    min_names = params.get("min_names", 20)

    ret = DAILY_CLOSE / DAILY_CLOSE.shift(L) - 1.0        # trailing L-day return
    rebal_days = DAY_OPENS[::R]
    # positions currently open: coin -> dict(side, entry_time, entry_px)
    open_pos: dict[str, dict] = {}
    rows = []
    n_rebal = 0
    turn_num = 0
    turn_den = 0
    for i, t in enumerate(rebal_days):
        if t not in ret.index:
            continue
        r = ret.loc[t].dropna()
        # only coins with a valid next-bar open (fill price) at t
        r = r[O.loc[t, r.index].notna()]
        if len(r) < min_names:
            target = {}
        else:
            k = max(1, int(np.floor(len(r) * q)))
            if shuffle:
                vals = r.values.copy()
                RNG.shuffle(vals)
                r = pd.Series(vals, index=r.index)
            srt = r.sort_values()
            losers, winners = list(srt.index[:k]), list(srt.index[-k:])
            target = {c: direction for c in winners}
            target.update({c: -direction for c in losers})
        n_rebal += 1
        # close positions no longer wanted (or flipped)
        for c in list(open_pos):
            if target.get(c) != open_pos[c]["side"]:
                p = open_pos.pop(c)
                rows.append(_close(c, p, t))
        # open new
        changed = 0
        for c, s in target.items():
            if c in open_pos:
                continue
            changed += 1
            px = float(O.loc[t, c])
            open_pos[c] = dict(side=s, entry_time=t, entry_px=px,
                               qty=NOTIONAL_PER_NAME / px)
        turn_num += changed
        turn_den += max(len(target), 1)
    # close everything at the last available 00:00 open
    t_end = DAY_OPENS[-1]
    for c, p in list(open_pos.items()):
        if p["entry_time"] < t_end:
            rows.append(_close(c, p, t_end))
    trades = pd.DataFrame(rows)
    diag = dict(n_rebal=n_rebal, turnover=(turn_num / turn_den if turn_den else np.nan))
    _CACHE[key] = (trades, diag)
    return trades, diag


def _close(coin, p, t_exit):
    exit_px = float(O.loc[t_exit, coin])
    row = C.crypto_trade(p["entry_time"], t_exit, p["side"], p["entry_px"], exit_px,
                         p["qty"], coin, maker_entry=False, maker_exit=False)
    fu = funding_usd(coin, p["side"], NOTIONAL_PER_NAME, p["entry_time"], t_exit)
    row["exit_px_raw"] = exit_px
    row["funding_usd"] = fu
    # fold funding into exit price so evaluate() gross includes it
    row["exit_px"] = exit_px + p["side"] * fu / p["qty"]
    return row


def run_fn(params, start, end):
    tr, _ = build_trades(params)
    if len(tr) == 0:
        return tr
    m = (tr["entry_time"] >= start) & (tr["entry_time"] < end)
    return tr[m].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
GRID = [dict(lookback_d=L, rebal_d=R, quantile=q, mode=m)
        for L, R, q, m in itertools.product([1, 7, 30], [1, 7], [0.1, 0.2], ["mom", "rev"])]
assert len(GRID) <= 24


def pname(p):
    return f"L{p['lookback_d']}_R{p['rebal_d']}_q{p['quantile']}_{p['mode']}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} "
            f"folds={[round(f, 1) for f in r['folds']]}")



def md_table(df: pd.DataFrame, index: bool = False) -> str:
    """Minimal markdown table (no tabulate dependency)."""
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)

def main():
    bounds = C.fold_bounds(PERIOD, 3)
    print("period", PERIOD, "folds", [(s.date(), e.date()) for s, e in bounds])
    print(f"universe {len(COINS)} coins; illiquid(<$5M/24h): {sorted(ILLIQ)}")

    # --- walk-forward -------------------------------------------------------
    best, oos_tr, table = C.walk_forward(GRID, run_fn, PERIOD, n_folds=3, min_trades=10)
    oos = C.oos_result(oos_tr, PERIOD, 3)
    print("\nBEST (fold-1 selected):", best)
    print("OOS (folds 2+3):", fmt(oos))

    # --- full grid: fold-1 IS plus fold 2/3 nets for sensitivity ------------
    lines = []
    grid_rows = []
    for i, p in enumerate(GRID):
        tr, diag = build_trades(p)
        full = C.evaluate(tr, 3, *PERIOD)
        is_ = C.evaluate(run_fn(p, *bounds[0]), 1)
        o = C.oos_result(pd.concat([run_fn(p, *bounds[1]), run_fn(p, *bounds[2])]), PERIOD, 3)
        per_rebal = full["net"] / max(diag["n_rebal"], 1)
        row = dict(idx=i, name=pname(p), is_n=is_["n"], is_net=is_["net"], is_pf=is_["pf"],
                   oos_n=o["n"], oos_net=o["net"], oos_pf=o["pf"], f1=full["folds"][0],
                   f2=full["folds"][1], f3=full["folds"][3 - 1], full_net=full["net"],
                   turnover=diag["turnover"], n_rebal=diag["n_rebal"],
                   net_per_rebal=per_rebal, fees=full["fees"],
                   funding=float(tr["funding_usd"].sum()) if len(tr) else 0.0,
                   selected=(p == best))
        grid_rows.append(row)
        C.record_to_lab(STRATEGY, pname(p) + "_full", "HL_XSEC", f"{p['rebal_d']}d", p, full,
                        period=PERIOD, source=str(Path(__file__).name),
                        notes=f"full-period all folds (IS incl.), taker+funding; turnover={diag['turnover']:.2f} n_rebal={diag['n_rebal']}")
        C.record_to_lab(STRATEGY, pname(p) + "_is_f1", "HL_XSEC", f"{p['rebal_d']}d", p,
                        C.evaluate(run_fn(p, *bounds[0]), 3, *PERIOD),
                        period=bounds[0], source=str(Path(__file__).name),
                        notes="fold-1 in-sample grid cell")
    grid = pd.DataFrame(grid_rows)
    pd.set_option("display.width", 250)
    print("\nIN-SAMPLE (fold 1) GRID + fold-2/3 sensitivity:")
    print(grid.round(2).to_string(index=False))

    # --- record headline OOS ---------------------------------------------------
    C.record_to_lab(STRATEGY, "WF_OOS_" + pname(best), "HL_XSEC", f"{best['rebal_d']}d", best, oos,
                    period=(bounds[1][0], bounds[2][1]), source=str(Path(__file__).name),
                    notes="HEADLINE walk-forward OOS folds 2+3, params selected on fold 1; taker both sides + funding")

    # --- sanity (a): shuffle -----------------------------------------------------
    sh_nets = []
    for s in range(1, 41):
        ps = dict(best, _shuffle=s)
        tr = pd.concat([run_fn(ps, *bounds[1]), run_fn(ps, *bounds[2])])
        sh_nets.append(C.evaluate(tr, 1)["net"])
    sh_nets = np.array(sh_nets)
    sh_pct = float((sh_nets >= oos["net"]).mean())
    print(f"\nSHUFFLE (random bucket assignment, 40 trials, OOS): mean={sh_nets.mean():.1f} "
          f"sd={sh_nets.std():.1f} p(shuffle>=real)={sh_pct:.2f}  real={oos['net']:.1f}")
    C.record_to_lab(STRATEGY, "SHUFFLE_" + pname(best), "HL_XSEC", f"{best['rebal_d']}d",
                    dict(best, shuffle="mean_of_40"),
                    dict(C.empty_result(), n=int(oos["n"]), net=float(sh_nets.mean())),
                    period=(bounds[1][0], bounds[2][1]), source=str(Path(__file__).name),
                    notes=f"shuffle control: sd={sh_nets.std():.1f} p(shuffle>=real)={sh_pct:.2f}")

    # --- sanity (c): neighbors ---------------------------------------------------
    def neigh(p, q):
        return (p["mode"] == q["mode"] and sum(p[k] != q[k] for k in ("lookback_d", "rebal_d", "quantile")) == 1)
    nb = grid[[neigh(GRID[i], best) for i in grid["idx"]]]
    print("\nNEIGHBORS of best (one param changed), OOS nets:")
    print(nb[["name", "oos_n", "oos_net", "oos_pf", "f2", "f3"]].round(2).to_string(index=False))
    nb_pos = int((nb["oos_net"] > 0).sum())

    # --- sanity (d): per coin / liquidity -----------------------------------------
    t = C.add_pnl(oos_tr) if len(oos_tr) else pd.DataFrame()
    per_coin = pd.DataFrame()
    liq_split = {}
    side_split = {}
    if len(t):
        t["illiq"] = t["instrument"].isin(ILLIQ)
        per_coin = t.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"),
                                               funding=("funding_usd", "sum")).sort_values("net")
        per_coin["illiq"] = per_coin.index.isin(ILLIQ)
        liq_split = t.groupby("illiq")["net_pnl"].agg(["size", "sum"]).to_dict("index")
        side_split = t.groupby("side")["net_pnl"].agg(["size", "sum"]).to_dict("index")
        print("\nPER-COIN OOS (worst 8 / best 8):")
        print(per_coin.head(8).round(1).to_string())
        print(per_coin.tail(8).round(1).to_string())
        print("liquidity split:", liq_split)
        print("side split (+1 long / -1 short):", side_split)
        print(f"OOS funding total={t['funding_usd'].sum():.1f}  fees={t['fee_usd'].sum():.1f} "
              f"gross_ex_funding={(t['gross_pnl'] - t['funding_usd']).sum():.1f}")

    # --- verdict ----------------------------------------------------------------
    oos_folds = oos["folds"][1:]
    crit = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=oos["n"] >= 60,
                folds=all(f > 0 for f in oos_folds), shuffle=sh_pct < 0.05,
                neighbors=(nb_pos >= max(1, len(nb) // 2)))
    if all(crit.values()):
        verdict = "edge"
    elif oos["net"] > 0:
        verdict = "weak"
    else:
        verdict = "none"
    print("\nCRITERIA:", crit, "VERDICT:", verdict)

    # --- markdown ---------------------------------------------------------------
    md = []
    md.append("# h_xsec_momentum - cross-sectional momentum / reversal, Hyperliquid universe\n")
    md.append(f"Data: {len(COINS)} HL perps, 1h candles {PERIOD[0].date()} -> {PERIOD[1].date()} (universe = "
              f"current top-50 by volume snapshot -> **survivorship-biased toward today's winners**). "
              f"Folds: {[(str(s.date()), str(e.date())) for s, e in bounds]}.\n")
    md.append("Execution: signal = trailing L-day return of the 23:00-bar close; fill at next (00:00) bar OPEN; "
              f"equal ${NOTIONAL_PER_NAME:.0f}/name; long top q / short bottom q; hold to next rebalance; "
              "positions kept when bucket unchanged. Fees: HL taker 4.5 bps/side both legs. Funding: hourly history, "
              "longs pay positive funding, folded into exit price.\n")
    md.append(f"## Headline (walk-forward OOS, folds 2+3)\n\nSelected on fold 1: `{best}`\n\n"
              f"| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |\n|---|---|---|---|---|---|---|---|---|\n"
              f"| {oos['n']} | {oos['net']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | {oos['sharpe']:.2f} | "
              f"{oos['max_dd']:.1f} | {oos['net_bps']:.1f} | {oos_folds[0]:.2f} | {oos_folds[1]:.2f} |\n")
    if len(t):
        bk = grid[grid["selected"]].iloc[0]
        md.append(f"Turnover per rebalance (fraction of book changed): {bk['turnover']:.2f}; rebalances: {int(bk['n_rebal'])}; "
                  f"full-period net per rebalance: {bk['net_per_rebal']:.2f} USD on a "
                  f"~${2 * NOTIONAL_PER_NAME * max(1, int(np.floor(len(COINS) * best['quantile']))):.0f} gross book.\n")
    md.append("## In-sample grid (fold 1) with fold 2/3 nets for sensitivity\n")
    md.append(md_table(grid.drop(columns=["idx"]).round(2)) + "\n")
    md.append("## Sanity checks\n")
    md.append(f"- (a) Shuffle (random long/short bucket assignment, 40 trials, OOS period): mean {sh_nets.mean():.1f}, "
              f"sd {sh_nets.std():.1f}, P(shuffle >= real) = {sh_pct:.2f}; real = {oos['net']:.1f}.\n"
              f"- (b) OOS folds: fold2 {oos_folds[0]:.2f}, fold3 {oos_folds[1]:.2f}.\n"
              f"- (c) Neighbors of best (one param changed): {nb_pos}/{len(nb)} positive OOS net.\n\n"
              + md_table(nb[["name", "oos_n", "oos_net", "oos_pf", "f2", "f3"]].round(2)) + "\n")
    if len(t):
        md.append(f"- (d) Liquidity split (illiquid = 24h vol < $5M): {liq_split}\n- Side split: {side_split}\n\n"
                  "Per-coin OOS:\n\n" + md_table(per_coin.round(1), index=True) + "\n")
    md.append(f"## Criteria\n\n`{crit}`\n\n## Verdict: **{verdict}**\n")
    OUT_MD.write_text("\n".join(md))
    print("wrote", OUT_MD)

    result = dict(best=best, oos=oos, oos_folds=oos_folds, sh_pct=sh_pct, sh_mean=float(sh_nets.mean()),
                  nb_pos=nb_pos, nb_n=len(nb), verdict=verdict, crit=crit,
                  is_best_net=float(grid[grid["selected"]]["is_net"].iloc[0]),
                  liq_split=liq_split, side_split=side_split)
    (ROOT / "tests" / "h_xsec_momentum_result.json").write_text(json.dumps(result, default=str, indent=1))
    return result


if __name__ == "__main__":
    main()
