"""H: perp_spot_basis -- fade extreme perp-vs-spot premium (trailing-7d z-score).

Signal sources
  premium : Hyperliquid hourly funding-history `premium` (perp mark vs oracle),
            all 50 cached coins.
  basis   : HL 1h close / yfinance spot 1h close - 1 (BTC, ETH only).
Timing (strict): the observation stamped at hour T (premium averaged over the
hour ending T, or the candle that closes at T) becomes a signal at T; the fill
is at the OPEN of the candle whose open time is T+1h (i.e. next bar open after
the bar that closed at T).  Exit = open of the bar `hold` hours after entry
(time stop, taker).  Funding paid/received at every funding stamp in
(entry, exit] is folded into exit_px so common.evaluate() sees it as gross.
Execution modes
  taker        : market in / market out (0.045% per side)
  maker_entry  : limit at next-bar open improved by 1bp; requires the bar's
                 high/low to trade THROUGH the limit; taker exit
  maker_both   : as above on entry and exit (exit limit at exit-bar open -1bp
                 improvement, must be traded through); else fall back to taker
                 exit at that bar's close? NO -- we keep it simple and honest:
                 unfilled exit limit -> taker exit at the *next* bar open.
"""
from __future__ import annotations
import sys, json, itertools, time as _time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C

NOTIONAL = 1000.0          # USD per trade
LOOKBACK = 168             # trailing 7d, hours
MAKER_IMPROVE = 0.0001     # 1bp inside the open
PERIOD = (pd.Timestamp("2026-01-31", tz="UTC"), pd.Timestamp("2026-08-27 21:00", tz="UTC"))
STRATEGY = "perp_spot_basis"
OUT_MD = Path(__file__).with_suffix(".md")
rng = np.random.default_rng(7)

# ---------------------------------------------------------------- data prep
def load_coin(coin: str, source: str):
    """Return dict of aligned hourly arrays for one coin, or None."""
    bars = C.hl_candles(coin, "1h")
    bars = bars[~bars.index.duplicated()].sort_index()
    fund = C.hl_funding(coin)
    fund = fund.copy(); fund.index = fund.index.floor("h")
    fund = fund[~fund.index.duplicated(keep="last")].sort_index()
    if source == "premium":
        x = fund["premium"].rename("x")
    elif source == "basis":
        ysym = {"BTC": "BTC-USD", "ETH": "ETH-USD"}.get(coin)
        if ysym is None:
            return None
        y = C.yf_bars(ysym, "1h")["close"]
        y = y[~y.index.duplicated()].sort_index()
        x = (bars["close"] / y.reindex(bars.index) - 1).rename("x")
    else:
        raise ValueError(source)
    # z-score over trailing LOOKBACK hours (includes current obs; known at T)
    m = x.rolling(LOOKBACK, min_periods=LOOKBACK).mean()
    s = x.rolling(LOOKBACK, min_periods=LOOKBACK).std()
    z = ((x - m) / s).rename("z")
    # signal stamped at T -> fill at bar with open time T+1h
    z_at_fill = z.copy(); z_at_fill.index = z_at_fill.index + pd.Timedelta("1h")
    df = bars[["open", "high", "low", "close", "volume"]].join(z_at_fill, how="left")
    df["fr"] = fund["fundingRate"].reindex(df.index).fillna(0.0)
    return dict(coin=coin, df=df)

def gen_trades(cd: dict, z_thr: float, hold: int, mode: str) -> list[dict]:
    """Causal, non-overlapping (per coin) trade list over the full period."""
    df = cd["df"]; coin = cd["coin"]
    idx = df.index; n = len(df)
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    z = df["z"].values; fr = df["fr"].values
    cum_fr = np.concatenate([[0.0], np.cumsum(fr)])  # cum_fr[k] = sum fr[0..k-1]
    hours = ((idx - idx[0]) / pd.Timedelta("1h")).values.astype(np.int64)
    rows = []; i = 0
    while i < n:
        zi = z[i]
        if not np.isfinite(zi) or abs(zi) < z_thr:
            i += 1; continue
        side = -1 if zi > 0 else +1          # fade: short when premium high
        j = i + hold
        if j >= n or hours[j] - hours[i] != hold:   # data gap -> skip
            i += 1; continue
        # ---- entry
        if mode == "taker":
            epx = o[i]; mk_e = False; entry_bar = i
        else:
            lim = o[i] * (1 + MAKER_IMPROVE) if side < 0 else o[i] * (1 - MAKER_IMPROVE)
            filled = (h[i] > lim) if side < 0 else (l[i] < lim)
            if not filled:
                i += 1; continue
            epx = lim; mk_e = True; entry_bar = i
        # ---- exit
        if mode == "maker_both":
            lim = o[j] * (1 - MAKER_IMPROVE) if side < 0 else o[j] * (1 + MAKER_IMPROVE)
            filled = (l[j] < lim) if side < 0 else (h[j] > lim)
            if filled:
                xpx = lim; mk_x = True; exit_bar = j
            else:
                if j + 1 >= n: i += 1; continue
                xpx = o[j + 1]; mk_x = False; exit_bar = j + 1
        else:
            xpx = o[j]; mk_x = False; exit_bar = j
        qty = NOTIONAL / epx
        # funding stamps in (entry, exit]: fr at bars entry_bar+1 .. exit_bar
        f_sum = cum_fr[exit_bar + 1] - cum_fr[entry_bar + 1]
        fund_usd = -side * f_sum * NOTIONAL     # short receives when fr>0
        tr = C.crypto_trade(idx[entry_bar], idx[exit_bar], side, epx, xpx, qty, coin,
                            maker_entry=mk_e, maker_exit=mk_x)
        tr["exit_px_raw"] = xpx
        tr["funding_usd"] = fund_usd
        tr["exit_px"] = xpx + fund_usd / (side * qty)   # fold funding into gross
        tr["z"] = zi; tr["hold"] = hold
        rows.append(tr)
        i = exit_bar + 1   # no overlap per coin
    return rows

# ---------------------------------------------------------------- harness
class Runner:
    def __init__(self, coins, source, mode):
        self.cds = [x for x in (load_coin(c, source) for c in coins) if x is not None]
        self.mode = mode; self.source = source; self.cache = {}
    def all_trades(self, p):
        key = (p["z"], p["hold"])
        if key not in self.cache:
            rows = []
            for cd in self.cds:
                rows += gen_trades(cd, p["z"], p["hold"], self.mode)
            self.cache[key] = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        return self.cache[key]
    def __call__(self, p, start, end):
        t = self.all_trades(p)
        if len(t) == 0: return t
        return t[(t["entry_time"] >= start) & (t["entry_time"] < end)].reset_index(drop=True)

GRID = [dict(z=z, hold=h) for z in (1.5, 2.0, 2.5, 3.0) for h in (4, 8, 12, 24)]
def pname(p): return f"z{p['z']}_h{p['hold']}"

def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:8.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sh={r['sharpe']:.2f} bps={r['net_bps']:.1f} folds={[round(f,1) for f in r['folds']]}")

def shuffle_test(runner, p, oos_trades, n_iter=300):
    """Keep per-coin trade count, side and hold; move entries to random bars
    within the OOS window. Returns (real_net, p_value, null_mean, null_sd)."""
    bounds = C.fold_bounds(PERIOD, 3); s = bounds[1][0]
    real = C.evaluate(oos_trades)["net"]
    by_coin = oos_trades.groupby("instrument")
    cds = {cd["coin"]: cd for cd in runner.cds}
    nulls = []
    for _ in range(n_iter):
        rows = []
        for coin, g in by_coin:
            df = cds[coin]["df"]; idx = df.index
            o = df["open"].values; fr = df["fr"].values
            cum_fr = np.concatenate([[0.0], np.cumsum(fr)])
            lo = idx.searchsorted(s); hi = len(df) - p["hold"] - 2
            if hi <= lo: continue
            picks = rng.integers(lo, hi, size=len(g))
            for k, (side, hold) in enumerate(zip(g["side"].values, g["hold"].values)):
                i = int(picks[k]); j = i + int(hold)
                epx, xpx = o[i], o[j]; qty = NOTIONAL / epx
                f_sum = cum_fr[j + 1] - cum_fr[i + 1]
                fund = -side * f_sum * NOTIONAL
                tr = C.crypto_trade(idx[i], idx[j], side, epx, xpx, qty, coin,
                                    maker_entry=(runner.mode != "taker"),
                                    maker_exit=(runner.mode == "maker_both"))
                tr["exit_px"] = xpx + fund / (side * qty)
                rows.append(tr)
        nulls.append(C.evaluate(pd.DataFrame(rows))["net"] if rows else 0.0)
    nulls = np.array(nulls)
    pval = float((nulls >= real).mean())
    return real, pval, float(nulls.mean()), float(nulls.std())

def main():
    t0 = _time.time()
    coins = C.list_hl_funding_coins()
    coins = [c for c in coins if (C.DATA / f"hl_{c}_1h.parquet").exists()]
    uni = C.hl_universe().set_index("coin")
    illiq = set(uni.index[uni["dayNtlVlm"] < 5e6])
    md = [f"# perp_spot_basis results\n", f"Period {PERIOD[0].date()} -> {PERIOD[1].date()}, "
          f"{len(coins)} coins, notional ${NOTIONAL:.0f}/trade, lookback {LOOKBACK}h, "
          f"funding included in PnL, fold edges = calendar thirds.\n"]
    bounds = C.fold_bounds(PERIOD, 3)
    md.append("Folds: " + ", ".join(f"F{k+1} {a.date()}->{b.date()}" for k, (a, b) in enumerate(bounds)) + "\n")
    summary = {}
    configs = [("premium", "taker", coins), ("premium", "maker_entry", coins),
               ("premium", "maker_both", coins),
               ("basis", "taker", ["BTC", "ETH"]), ("basis", "maker_entry", ["BTC", "ETH"]),
               ("premium_btceth", "taker", ["BTC", "ETH"])]
    for source, mode, cset in configs:
        src = "premium" if source.startswith("premium") else source
        runner = Runner(cset, src, mode)
        tag = f"{source}_{mode}"
        print(f"\n===== {tag} ({len(runner.cds)} coins) =====")
        best, oos, table = C.walk_forward(GRID, runner, PERIOD, n_folds=3, min_trades=10)
        res = C.oos_result(oos, PERIOD, 3)
        # full-period per-cell nets (for neighbor robustness / reviewer), OOS-only nets
        cell_oos = {}
        md.append(f"\n## {tag}\n\nIn-sample grid (fold 1) + OOS (folds 2+3) net for every cell:\n\n")
        md.append("| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |\n|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|\n")
        for _, row in table.iterrows():
            p = json.loads(row["params"])
            full = runner.all_trades(p)
            oo = full[full["entry_time"] >= bounds[1][0]]
            ro = C.oos_result(oo, PERIOD, 3)
            cell_oos[pname(p)] = ro
            md.append(f"| {pname(p)} | {row['is_n']} | {row['is_net']:.1f} | {row['is_pf']:.2f} | {row['is_wr']:.2f} | "
                      f"{ro['n']} | {ro['net']:.1f} | {ro['pf']:.2f} | {ro['folds'][1]:.1f} | {ro['folds'][2]:.1f} | "
                      f"{'*' if row['selected'] else ''} |\n")
            is_res = C.evaluate(runner(p, *bounds[0]), n_folds=1)
            C.record_to_lab(STRATEGY, f"{tag}_{pname(p)}_IS", "HL-basket" if len(cset) > 2 else "+".join(cset),
                            "1h", dict(p, source=source, mode=mode, lookback=LOOKBACK),
                            is_res, period=bounds[0], source=str(Path(__file__)),
                            notes=f"in-sample fold1 cell; {len(runner.cds)} coins")
            print(f"  {pname(p):10s} IS n={row['is_n']:4d} net={row['is_net']:8.2f} pf={row['is_pf']:.2f} | OOS {fmt(ro)}")
        print(f"BEST (fold-1 select) {best} -> OOS {fmt(res)}")
        C.record_to_lab(STRATEGY, f"{tag}_WF_OOS", "HL-basket" if len(cset) > 2 else "+".join(cset), "1h",
                        dict(best, source=source, mode=mode, lookback=LOOKBACK),
                        res, period=PERIOD, source=str(Path(__file__)),
                        notes=f"walk-forward OOS folds2+3, params chosen on fold1; {len(runner.cds)} coins")
        md.append(f"\n**Walk-forward pick {pname(best)} -> OOS** {fmt(res)}  gross={res['gross']:.1f} fees={res['fees']:.1f} "
                  f"maxdd={res['max_dd']:.1f} hold={res['avg_hold_min']/60:.0f}h\n")
        entry = dict(best=best, oos=res, oos_trades=oos, cell_oos=cell_oos, table=table, runner=runner)
        # ---- neighbor robustness (OOS nets of adjacent cells)
        zs, hs = (1.5, 2.0, 2.5, 3.0), (4, 8, 12, 24)
        zi, hi = zs.index(best["z"]), hs.index(best["hold"])
        neigh = [pname(dict(z=zs[a], hold=hs[b])) for a in (zi-1, zi, zi+1) for b in (hi-1, hi, hi+1)
                 if 0 <= a < 4 and 0 <= b < 4 and not (a == zi and b == hi)]
        nn = [(k, cell_oos[k]["net"]) for k in neigh]
        n_pos = sum(1 for _, v in nn if v > 0)
        md.append(f"\nNeighbors OOS net: {', '.join(f'{k}={v:.1f}' for k, v in nn)} -> {n_pos}/{len(nn)} positive\n")
        entry["neigh"] = (n_pos, len(nn), nn)
        # ---- shuffle test
        if len(oos):
            real, pval, nm, nsd = shuffle_test(runner, best, oos, n_iter=200)
            md.append(f"\nShuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): "
                      f"real={real:.1f}, null mean={nm:.1f} sd={nsd:.1f}, p(null>=real)={pval:.3f}\n")
            entry["shuffle"] = (real, pval, nm, nsd)
            print(f"  shuffle: real={real:.1f} null={nm:.1f}+-{nsd:.1f} p={pval:.3f}")
            # ---- per-side, per-coin, liquidity split (OOS)
            oo = C.add_pnl(oos)
            sides = oo.groupby("side")["net_pnl"].agg(["count", "sum"])
            md.append("\nOOS by side: " + "; ".join(f"side {int(s)}: n={int(r['count'])} net={r['sum']:.1f}" for s, r in sides.iterrows()) + "\n")
            fund_tot = oo["funding_usd"].sum() if "funding_usd" in oo else float("nan")
            md.append(f"\nOOS funding component: {fund_tot:.1f} USD of net {res['net']:.1f}\n")
            entry["funding_component"] = fund_tot
            pc = oo.groupby("instrument")["net_pnl"].agg(["count", "sum"]).sort_values("sum")
            pc["illiquid"] = [c in illiq for c in pc.index]
            if len(pc) > 2:
                liq = oo[~oo["instrument"].isin(illiq)]; ill = oo[oo["instrument"].isin(illiq)]
                rl, ri = C.oos_result(liq, PERIOD, 3), C.oos_result(ill, PERIOD, 3)
                md.append(f"\nOOS liquid (>= $5M/24h, {len(set(liq['instrument']))} coins): {fmt(rl)}\n")
                md.append(f"\nOOS illiquid (< $5M/24h, {len(set(ill['instrument']))} coins): {fmt(ri)}\n")
                C.record_to_lab(STRATEGY, f"{tag}_WF_OOS_liquid", "HL-liquid", "1h",
                                dict(best, source=source, mode=mode, lookback=LOOKBACK, filter="dayNtlVlm>=5M"),
                                rl, period=PERIOD, source=str(Path(__file__)), notes="OOS liquid subset")
                C.record_to_lab(STRATEGY, f"{tag}_WF_OOS_illiquid", "HL-illiquid", "1h",
                                dict(best, source=source, mode=mode, lookback=LOOKBACK, filter="dayNtlVlm<5M"),
                                ri, period=PERIOD, source=str(Path(__file__)), notes="OOS illiquid subset")
                entry["liq"] = (rl, ri)
                print(f"  liquid: {fmt(rl)}\n  illiquid: {fmt(ri)}")
            md.append("\nOOS per coin (net USD): " + ", ".join(
                f"{c}{'*' if r['illiquid'] else ''}={r['sum']:.0f}({int(r['count'])})" for c, r in pc.iterrows()) + "  (* = illiquid)\n")
        summary[tag] = entry
    # ---- extra: long-only vs short-only on the headline taker config, OOS-only diagnostic
    md.append("\n## Interpretation\n")
    OUT_MD.write_text("".join(md))
    print(f"\nwrote {OUT_MD}  ({_time.time()-t0:.0f}s)")
    return summary

if __name__ == "__main__":
    S = main()
    # compact machine summary
    for tag, e in S.items():
        r = e["oos"]
        print(f"{tag:28s} best={e['best']} n={r['n']} net={r['net']:.1f} pf={r['pf']:.2f} folds={[round(f,1) for f in r['folds']]} "
              f"neigh={e['neigh'][0]}/{e['neigh'][1]} shuffle_p={e.get('shuffle',(0,float('nan')))[1]:.3f}")
