"""Adversarial execution-realism re-run of h_mean_reversion_zscore (1h, WF-best
K=2 thr=3 H=4 tgt=0.5 vf=1). Does NOT modify the author's script; imports its
bar loader / signal builder and re-simulates with extra frictions:

  * fill only if bar t+1 trades THROUGH the limit by >= m bps (queue priority)
  * entries whose bar t+1 OPEN is already through the limit are taker fills
  * taker exit slippage: per-coin half-spread (live L2 snapshot) or flat bps
  * hourly funding accrued while the position is open (real HL funding history)
  * concurrency / capital and per-trade notional vs 24h volume
Every variant is recorded to quant-lab (project edge-hunt).
"""
from __future__ import annotations
import sys, json, math
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import common as C
import h_mean_reversion_zscore as A

STRAT = "mean_reversion_zscore"
SRC = "research/edge_hunt/tests/verify_mean_reversion_zscore_execution.py"
TF = "1h"
BEST = dict(K=2, thr=3.0, H=4, tgt=0.5, vol_filter=1.0)
NOTIONAL = 1000.0
SPREAD_FILE = Path("/private/tmp/claude-501/-Users-molt-bot/78c80aee-b9a8-40f2-986e-38cb35c978c8/scratchpad/hl_spreads.json")
SPREADS = json.load(open(SPREAD_FILE)) if SPREAD_FILE.exists() else {}

_FUND = {}
def funding(coin):
    if coin not in _FUND:
        try:
            f = C.hl_funding(coin)["fundingRate"].astype(float)
            f.index = f.index.floor("h")
            f = f[~f.index.duplicated()]
        except FileNotFoundError:
            f = pd.Series(dtype=float)
        _FUND[coin] = f
    return _FUND[coin]


def simulate(coin, p, fill_margin_bps=0.0, exit_slip_bps=0.0, gap_taker=False,
             use_funding=False, spread_exit=False):
    b = A.bars(coin, TF)
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    idx = b.index; n = len(b)
    sf = A.signal_frame(b, p["K"], p["thr"], p["vol_filter"])
    sig_idx = np.flatnonzero(sf["side"].values != 0)
    sides = sf["side"].values[sig_idx]; rK = sf["rK"].values
    fr = funding(coin)
    m = fill_margin_bps / 1e4
    half_spread = (SPREADS.get(coin, {}).get("spread_bps", 2.0) / 2) / 1e4 if spread_exit else 0.0
    slip = exit_slip_bps / 1e4 + half_spread
    trades = []; busy_until = -1; H = p["H"]
    for i, s in zip(sig_idx, sides):
        if i <= busy_until or i + 1 + H >= n:
            continue
        lim = c[i]
        if s == -1 and not (h[i + 1] > lim * (1 + m)):
            continue
        if s == 1 and not (l[i + 1] < lim * (1 - m)):
            continue
        # open of t+1 already through the limit -> resting order would cross: taker
        gap = (s == -1 and o[i + 1] > lim) or (s == 1 and o[i + 1] < lim)
        maker_in = not (gap_taker and gap)
        entry_t = idx[i + 1]; entry_px = lim
        exit_j, exit_px, hit = i + 1 + H, o[i + 1 + H], False
        if p["tgt"] is not None and np.isfinite(rK[i]):
            target = lim * math.exp(s * p["tgt"] * abs(rK[i]))
            for j in range(i + 2, i + 1 + H):
                if (s == 1 and h[j] > target) or (s == -1 and l[j] < target):
                    exit_j, exit_px, hit = j, target, True
                    break
        exit_px = exit_px * (1 - s * slip)  # taker exit pays slippage against us
        qty = NOTIONAL / entry_px
        tr = C.crypto_trade(entry_t, idx[exit_j], int(s), float(entry_px), float(exit_px), qty, coin,
                            maker_entry=maker_in, maker_exit=False)
        fund_usd = 0.0
        if use_funding and len(fr):
            t0, t1 = idx[i + 1], idx[exit_j]
            # funding events strictly after the fill bar opens; include exit bar's
            # top-of-hour payment only if we were still in during that bar (target hit)
            ev = fr[(fr.index > t0) & ((fr.index <= t1) if hit else (fr.index < t1))]
            fund_usd = float(-s * ev.sum() * NOTIONAL)  # long pays when rate>0
        tr["funding_usd"] = fund_usd
        tr["fee_usd"] = tr["fee_usd"] - fund_usd  # fold funding into the cost line
        tr["gap"] = bool(gap); tr["hit"] = hit
        tr["through_bps"] = float(((h[i + 1] / lim - 1) if s == -1 else (1 - l[i + 1] / lim)) * 1e4)
        trades.append(tr); busy_until = exit_j - 1
    return trades


def run(coins, **kw):
    rows = []
    for coin in coins:
        rows.extend(simulate(coin, BEST, **kw))
    df = pd.DataFrame(rows)
    return df.sort_values("entry_time").reset_index(drop=True)


def main():
    coins = C.list_hl_coins()
    uni = C.hl_universe().set_index("coin")
    lo = min(A.bars(c, TF).index.min() for c in coins); hi = max(A.bars(c, TF).index.max() for c in coins)
    times = (lo, hi); bounds = C.fold_bounds(times, 3)
    oos_s, oos_e = bounds[1][0], bounds[-1][1]
    def oos(df):
        t = pd.to_datetime(df["entry_time"], utc=True)
        return df[(t >= oos_s) & (t < oos_e)].reset_index(drop=True)
    def rep(name, df, notes, variant):
        r = C.evaluate(df, 3, start=lo, end=hi)
        print(f"{name:52s} " + A.fmt(r))
        C.record_to_lab(STRAT, variant, "HL_basket50", TF, dict(BEST, **{"exec": name}), r,
                        period=times, source=SRC, notes=notes)
        return r

    print(f"fold bounds {[(str(a.date()), str(b.date())) for a, b in bounds]}; OOS = folds 2+3")
    base = oos(run(coins))
    r0 = rep("baseline (author model)", base, "reproduction of author's WF-best OOS", "1h_exec_baseline")

    # --- diagnostics on the baseline fills
    tb = C.add_pnl(base)
    print(f"\nfill diagnostics (OOS n={len(tb)}):")
    print(f"  bar t+1 OPEN already through limit (resting limit would cross => taker): {tb['gap'].mean()*100:.1f}%")
    q = tb["through_bps"].quantile([.1, .25, .5, .75]).round(1).to_dict()
    print(f"  trade-through depth beyond limit (bps) quantiles: {q}")
    for thr in (2, 5, 10):
        sub = tb[tb["through_bps"] <= thr]
        print(f"  trades with <= {thr:2d} bps trade-through: n={len(sub)} net={sub['net_pnl'].sum():.1f}  (rest net={tb[tb['through_bps']>thr]['net_pnl'].sum():.1f})")
    print(f"  target hit share: {tb['hit'].mean()*100:.1f}%; net on target exits={tb[tb['hit']]['net_pnl'].sum():.1f}, on time-stops={tb[~tb['hit']]['net_pnl'].sum():.1f}")
    # concurrency
    ev = pd.concat([pd.Series(1, index=pd.to_datetime(tb["entry_time"], utc=True)),
                    pd.Series(-1, index=pd.to_datetime(tb["exit_time"], utc=True))]).sort_index().cumsum()
    print(f"  concurrent positions: max={int(ev.max())}, p95={int(ev.quantile(.95))}; capital at max = ${int(ev.max())*NOTIONAL:.0f}")
    # notional vs volume
    tb["dayvol"] = tb["instrument"].map(uni["dayNtlVlm"])
    tb["pct_dayvol"] = NOTIONAL / tb["dayvol"] * 100
    print(f"  $1000 as % of 24h volume: max={tb['pct_dayvol'].max():.3f}% (coin {tb.loc[tb['pct_dayvol'].idxmax(),'instrument']}), trades >0.1%: {(tb['pct_dayvol']>0.1).sum()}")
    tb["spread"] = tb["instrument"].map({k: v.get("spread_bps", np.nan) for k, v in SPREADS.items()})
    print(f"  net from coins with live spread > 5 bps: {tb[tb['spread']>5]['net_pnl'].sum():.1f} (n={(tb['spread']>5).sum()}); <=5 bps: {tb[tb['spread']<=5]['net_pnl'].sum():.1f}")

    print("\n--- single frictions ---")
    res = {}
    for m in (1, 2, 5, 10):
        res[f"fill_m{m}"] = rep(f"fill needs trade-through >= {m} bps", oos(run(coins, fill_margin_bps=m)),
                                f"maker fill only if bar t+1 goes >= {m} bps past the limit", f"1h_exec_fillthrough_{m}bps")
    res["gap_taker"] = rep("open-through-limit entries charged taker", oos(run(coins, gap_taker=True)),
                           "entries where bar t+1 open is already past the limit are taker fills", "1h_exec_gap_taker")
    for sl in (1, 2, 4):
        res[f"slip{sl}"] = rep(f"taker exit slippage {sl} bps", oos(run(coins, exit_slip_bps=sl)),
                               f"{sl} bps adverse slippage on the taker exit", f"1h_exec_exitslip_{sl}bps")
    res["spread"] = rep("taker exit pays per-coin half-spread (live L2)", oos(run(coins, spread_exit=True)),
                        "exit slippage = half of live top-of-book spread per coin (quiet snapshot)", "1h_exec_halfspread_exit")
    res["funding"] = rep("+ hourly funding accrual (real HL history)", oos(run(coins, use_funding=True)),
                         "funding paid/received at each hourly mark while open", "1h_exec_funding")

    print("\n--- combined realistic ---")
    comb_kw = dict(fill_margin_bps=2, exit_slip_bps=2, gap_taker=True, use_funding=True, spread_exit=True)
    comb = oos(run(coins, **comb_kw))
    rc = rep("REALISTIC: 2bps through + gap taker + 2bps+half-spread exit + funding", comb,
             "combined: fill needs 2 bps trade-through, open-through=taker, 2bps + half-spread taker exit slippage, real funding",
             "1h_exec_realistic_combined")
    comb5 = oos(run(coins, **dict(comb_kw, fill_margin_bps=5)))
    rc5 = rep("REALISTIC-5: same with 5 bps trade-through", comb5, "combined realistic with 5 bps fill margin", "1h_exec_realistic_combined_5bps")
    # liquid-only under realistic
    liq = comb[comb["instrument"].map(uni["dayNtlVlm"]) >= 5e6].reset_index(drop=True)
    rl = rep("REALISTIC, liquid coins only (24h vol >= $5M)", liq, "combined realistic, dayNtlVlm>=5M", "1h_exec_realistic_liquid")
    tc = C.add_pnl(comb)
    print(f"\nrealistic per-fold n={C.evaluate(comb,3,start=lo,end=hi)['fold_n']}; funding total={tc['funding_usd'].sum():.1f}")
    top = tc.groupby("instrument")["net_pnl"].sum().sort_values(ascending=False)
    print("realistic top/bottom coins:", top.head(5).round(1).to_dict(), top.tail(5).round(1).to_dict())
    print(f"realistic net without top-1 coin: {rc['net'] - top.iloc[0]:.1f}; without top-3: {rc['net'] - top.head(3).sum():.1f}")
    out = dict(baseline=r0["net"], baseline_n=r0["n"], realistic=rc["net"], realistic_n=rc["n"], realistic_folds=rc["folds"],
               realistic_pf=rc["pf"], realistic5=rc5["net"], liquid_realistic=rl["net"],
               singles={k: round(v["net"], 1) for k, v in res.items()})
    print("\nSUMMARY", json.dumps(out, default=float))
    Path(__file__).with_suffix(".json").write_text(json.dumps(out, default=float, indent=1))


if __name__ == "__main__":
    main()
