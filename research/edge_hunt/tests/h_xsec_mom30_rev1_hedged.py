"""Round 2 / key=xsec_mom30_rev1_hedged

Long-only cross-sectional book on a POINT-IN-TIME Hyperliquid universe:
  score(t) = z(30d return) - z(1d return), z = cross-sectional z-score at the
  23:00 UTC close (daily candle close of day D-1); fills at the 00:00 UTC bar
  of day D (next bar -> strictly causal).
Universe at each signal: all perps (incl. later-delisted ones) with >= 31
daily closes, trailing-24h USD volume >= $5M, top-50 by trailing-30d USD
volume.  Long top-q fraction, $1,000 per name, hold to next rebalance; names
that stay in the bucket are kept.  Optional equal-notional BTC-perp short
hedge, resized at each rebalance (fees on the adjustment only).
Execution arms: 'taker' (fill at 00:00 open, taker fee) and 'maker_fb'
(limit at the 00:00 open; filled at the open with maker fee only if the
00:00 bar trades THROUGH the limit - low<open for buys, high>open for sells;
otherwise taker fallback at that bar's close).  Hourly funding included
(longs pay positive funding, the BTC short receives), folded into exit_px.
Walk-forward: grid selected on fold 1 only; headline = folds 2+3.
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
sys.path.insert(0, str(ROOT / "tests"))
import common as C  # noqa: E402
import xsec_pit_data as D  # noqa: E402

OUT_MD = ROOT / "tests" / "h_xsec_mom30_rev1_hedged.md"
OUT_JSON = ROOT / "tests" / "h_xsec_mom30_rev1_hedged_result.json"
STRATEGY = "xsec_mom30_rev1_hedged"
NOTIONAL = 1000.0
LIQ_USD = 5e6          # trailing-24h USD volume gate at signal time
TOP_N = 50             # by trailing-30d USD volume
MIN_NAMES = 10
L_MOM, L_REV = 30, 1
SEED = 11

# ---------------------------------------------------------------------------
# Data / panel
# ---------------------------------------------------------------------------
def load_panel():
    listed, delisted = D.all_coins()
    coins_all = listed + [c for c in delisted if c not in listed]
    D.ensure_candles(coins_all, verbose=False)

    # reference clock = the original 50-coin cache (same folds as round 1)
    ref = C.hl_candles("BTC", "1h")
    t0, t1 = ref.index[0], ref.index[-1]
    hours = None
    bars = {}
    daily = {}
    for c in coins_all:
        h = D.read(D.path_1h(c))
        d = D.read(D.path_1d(c))
        if h is None or d is None:
            continue
        h = h[(h.index >= t0) & (h.index <= t1)]
        if len(h) == 0:
            continue
        bars[c] = h
        daily[c] = d
        hours = h.index if hours is None else hours.union(h.index)
    hours = hours[(hours >= t0) & (hours <= t1)]
    coins = sorted(bars)
    day_opens = hours[hours.hour == 0]
    n_d, n_c = len(day_opens), len(coins)
    # fill-bar arrays (the 00:00 bar of each decision day)
    O = np.full((n_d, n_c), np.nan); H = O.copy(); Lo = O.copy(); Cl = O.copy()
    for j, c in enumerate(coins):
        b = bars[c].reindex(day_opens)
        O[:, j], H[:, j], Lo[:, j], Cl[:, j] = b["open"], b["high"], b["low"], b["close"]
    # daily closes / USD volumes from 1d candles, aligned so that row i holds the
    # values of the candle that CLOSED at day_opens[i] (i.e. day D-1)
    days = pd.DatetimeIndex(day_opens - pd.Timedelta(days=1))
    d_close = pd.DataFrame({c: daily[c]["close"] for c in coins}).sort_index()
    d_vol = pd.DataFrame({c: daily[c]["volume"] * daily[c]["close"] for c in coins}).sort_index()
    # full daily history (before the period) for the lookbacks
    full_idx = pd.date_range(min(d_close.index[0], days[0] - pd.Timedelta(days=40)), days[-1], freq="D", tz="UTC")
    d_close = d_close.reindex(full_idx); d_vol = d_vol.reindex(full_idx)
    ret_mom = (d_close / d_close.shift(L_MOM) - 1.0).reindex(days).values
    ret_rev = (d_close / d_close.shift(L_REV) - 1.0).reindex(days).values
    vol30 = d_vol.rolling(30, min_periods=20).sum().reindex(days).values
    vol24 = d_vol.reindex(days).values
    # hourly funding
    fund_cum = {}
    for c in coins:
        p = D.path_fund(c)
        if p.exists():
            f = D.read(p)
            if f is not None:
                f.index = f.index.floor("h")
                f = f[~f.index.duplicated(keep="last")]["fundingRate"].astype(float).sort_index()
                fund_cum[c] = f.cumsum()
    return dict(coins=coins, day_opens=day_opens, hours=hours, O=O, H=H, Lo=Lo, Cl=Cl,
                ret_mom=ret_mom, ret_rev=ret_rev, vol30=vol30, vol24=vol24,
                bars=bars, fund_cum=fund_cum, d_close=d_close, days=days)


def universe_mask(P):
    """Point-in-time eligibility matrix (n_days x n_coins)."""
    ok = np.isfinite(P["ret_mom"]) & np.isfinite(P["ret_rev"]) & np.isfinite(P["O"]) \
        & np.isfinite(P["vol30"]) & (P["vol24"] >= LIQ_USD)
    v = np.where(ok, P["vol30"], -np.inf)
    mask = np.zeros_like(ok)
    for i in range(ok.shape[0]):
        n_ok = int(ok[i].sum())
        if n_ok == 0:
            continue
        top = np.argsort(-v[i])[:min(TOP_N, n_ok)]
        mask[i, top] = True
    return mask


def ensure_funding_for(P, mask):
    ever = [P["coins"][j] for j in np.where(mask.any(axis=0))[0]] + ["BTC"]
    need = [c for c in ever if c not in P["fund_cum"]]
    if need:
        print("fetching funding for", len(need), "coins")
        D.ensure_funding(need, verbose=False)
        for c in need:
            f = D.read(D.path_fund(c))
            if f is not None:
                f.index = f.index.floor("h")
                f = f[~f.index.duplicated(keep="last")]["fundingRate"].astype(float).sort_index()
                P["fund_cum"][c] = f.cumsum()
    return P


P = load_panel()
MASK = universe_mask(P)
P = ensure_funding_for(P, MASK)
COINS = P["coins"]; CIDX = {c: j for j, c in enumerate(COINS)}
DAY_OPENS = P["day_opens"]
PERIOD = (P["hours"][0], P["hours"][-1])
BTC = CIDX["BTC"]
RNG = np.random.default_rng(SEED)
SNAP50 = set(C.hl_universe()["coin"])           # round-1 hindsight universe


def funding_usd(coin, side, notional, t_entry, t_exit):
    cum = P["fund_cum"].get(coin)
    if cum is None or len(cum) == 0:
        return 0.0
    a = cum.asof(t_entry) if t_entry >= cum.index[0] else 0.0
    b = cum.asof(t_exit) if t_exit >= cum.index[0] else 0.0
    a = 0.0 if pd.isna(a) else a
    b = 0.0 if pd.isna(b) else b
    return -side * notional * (b - a)


def zs(x):
    m, s = np.nanmean(x), np.nanstd(x)
    return (x - m) / s if s > 0 else np.zeros_like(x)


def fill(i, j, side, mode):
    """Fill price + maker flag for a `side` (+1 buy / -1 sell) order at the
    00:00 bar of day i for coin j.  Returns (px, maker_bool)."""
    o = P["O"][i, j]
    if mode == "taker":
        return o, False
    if side > 0:
        through = P["Lo"][i, j] < o
    else:
        through = P["H"][i, j] > o
    if through:
        return o, True
    return P["Cl"][i, j], False


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------
_CACHE: dict = {}


def build_trades(params):
    key = json.dumps(params, sort_keys=True)
    if key in _CACHE:
        return _CACHE[key]
    R = int(params["rebal_d"]); q = float(params["quantile"]); hedge = int(params["hedge"])
    mode = params["exec"]; sig = params.get("signal", "combo")
    shuffle = int(params.get("_shuffle", 0)); restrict = params.get("_universe")
    rows = []; open_pos = {}
    n_rebal = 0; turn_num = 0; turn_den = 0; n_univ = []; n_long = []
    hedge_H = 0.0; hedge_row = None
    delist_exits = 0
    phase = int(params.get("_phase", 0)) % R
    rebal_idx = list(range(phase, len(DAY_OPENS), R))
    for i in rebal_idx:
        t = DAY_OPENS[i]
        m = MASK[i].copy()
        if restrict is not None:
            m &= np.isin(np.array(COINS), list(restrict))
        idx = np.where(m)[0]
        n_univ.append(len(idx))
        if len(idx) < MIN_NAMES:
            target = set()
        else:
            if sig == "combo":
                sc = zs(P["ret_mom"][i, idx]) - zs(P["ret_rev"][i, idx])
            elif sig == "mom":
                sc = zs(P["ret_mom"][i, idx])
            elif sig == "rev":
                sc = -zs(P["ret_rev"][i, idx])
            else:
                raise ValueError(sig)
            if shuffle:
                sc = RNG.permutation(sc)
            k = max(1, int(np.floor(len(idx) * q)))
            target = set(idx[np.argsort(-sc)[:k]])
        n_rebal += 1
        # close longs that left the bucket
        for j in list(open_pos):
            if j not in target:
                rows.append(_close_long(j, open_pos.pop(j), i, mode, delist=False))
        # open new longs
        changed = 0
        for j in target:
            if j in open_pos:
                continue
            px, mk = fill(i, j, +1, mode)
            if not np.isfinite(px):
                continue
            changed += 1
            open_pos[j] = dict(entry_time=t, entry_px=px, qty=NOTIONAL / px, maker=mk,
                               vol24=P["vol24"][i, j])
        turn_num += changed; turn_den += max(len(target), 1)
        n_long.append(len(open_pos))
        # hedge: resize to equal notional of the long book
        if hedge:
            H_new = NOTIONAL * len(open_pos)
            if hedge_row is not None:
                hedge_row = _roll_hedge(hedge_row, i, H_new, mode)
                rows.append(hedge_row["row"])
            if H_new > 0:
                hedge_row = _open_hedge(i, hedge_H, H_new, mode, prev=hedge_row)
            else:
                hedge_row = None
            hedge_H = H_new
    # final close at the last 00:00 open
    i_end = len(DAY_OPENS) - 1
    for j, p in list(open_pos.items()):
        if p["entry_time"] < DAY_OPENS[i_end]:
            rows.append(_close_long(j, p, i_end, mode, delist=False))
    if hedge and hedge_row is not None and hedge_row["i"] < i_end:
        hedge_row = _roll_hedge(hedge_row, i_end, 0.0, mode, final=True)
        rows.append(hedge_row["row"])
    trades = pd.DataFrame(rows)
    delist_exits = int(trades["delist"].sum()) if len(trades) else 0
    diag = dict(n_rebal=n_rebal, turnover=(turn_num / turn_den if turn_den else np.nan),
                avg_univ=float(np.mean(n_univ)) if n_univ else 0.0,
                avg_long=float(np.mean(n_long)) if n_long else 0.0, delist_exits=delist_exits,
                maker_fill_rate=(float(trades["maker_entry"].mean()) if len(trades) else np.nan))
    _CACHE[key] = (trades, diag)
    return trades, diag


def _close_long(j, p, i, mode, delist):
    coin = COINS[j]
    t_exit = DAY_OPENS[i]
    px, mk = fill(i, j, -1, mode)
    if not np.isfinite(px):
        # coin has no bar at this rebalance (delisted / gap): settle at its last
        # available 1h close before t_exit, taker fee
        b = P["bars"][coin]
        b = b[(b.index > p["entry_time"]) & (b.index <= t_exit)]
        if len(b) == 0:
            b = P["bars"][coin][P["bars"][coin].index <= t_exit]
        t_exit = b.index[-1] + pd.Timedelta(hours=1)
        px, mk, delist = float(b["close"].iloc[-1]), False, True
    row = C.crypto_trade(p["entry_time"], t_exit, +1, p["entry_px"], px, p["qty"], coin,
                         maker_entry=p["maker"], maker_exit=mk)
    fu = funding_usd(coin, +1, NOTIONAL, p["entry_time"], t_exit)
    row.update(exit_px_raw=px, funding_usd=fu, exit_px=px + fu / p["qty"], leg="long",
               maker_entry=bool(p["maker"]), maker_exit=bool(mk), vol24_entry=p["vol24"], delist=delist)
    return row


def _open_hedge(i, H_old, H_new, mode, prev=None):
    """Open a hedge interval row at day i.  Price/fee come from the adjustment
    trade |H_new - H_old| (sell if increasing the short, buy if decreasing)."""
    if prev is not None:
        px, mk = prev["px_next"], prev["mk_next"]
    else:
        px, mk = fill(i, BTC, -1, mode)
    return dict(i=i, t=DAY_OPENS[i], px=px, mk=mk, H=H_new, qty=H_new / px, fee_adj=C.hl_fee(abs(H_new - H_old), mk),
                row=None, px_next=None, mk_next=None)


def _roll_hedge(hr, i, H_new, mode, final=False):
    """Close the open hedge interval at day i (the boundary price is the fill
    of the adjustment trade at day i)."""
    delta = H_new - hr["H"]
    final = final or H_new <= 0
    if final or delta < 0:
        px, mk = fill(i, BTC, +1, mode)      # buying back
    elif delta > 0:
        px, mk = fill(i, BTC, -1, mode)      # adding to the short
    else:
        px, mk = P["O"][i, BTC], True        # no trade at the boundary
    t_exit = DAY_OPENS[i]
    row = C.crypto_trade(hr["t"], t_exit, -1, hr["px"], px, hr["qty"], "BTC",
                         maker_entry=hr["mk"], maker_exit=mk)
    # fee: entry adjustment only (the exit adjustment is charged by the next
    # interval's entry), except the final full close
    row["fee_usd"] = hr["fee_adj"] + (C.hl_fee(hr["H"], mk) if final else 0.0)
    fu = funding_usd("BTC", -1, hr["H"], hr["t"], t_exit)
    row.update(exit_px_raw=px, funding_usd=fu, exit_px=px - fu / hr["qty"], leg="hedge",
               maker_entry=bool(hr["mk"]), maker_exit=bool(mk), vol24_entry=np.nan, delist=False)
    hr = dict(hr); hr.update(row=row, px_next=px, mk_next=mk)
    return hr


def run_fn(params, start, end):
    tr, _ = build_trades(params)
    if len(tr) == 0:
        return tr
    m = (tr["entry_time"] >= start) & (tr["entry_time"] < end)
    return tr[m].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
GRID = [dict(rebal_d=R, quantile=q, hedge=h, exec=e, signal="combo")
        for R, q, h, e in itertools.product([1, 7], [0.1, 0.2], [0, 1], ["taker", "maker_fb"])]
assert len(GRID) <= 24


def pname(p):
    return f"{p.get('signal','combo')}_R{p['rebal_d']}_q{p['quantile']}_h{p['hedge']}_{p['exec']}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} "
            f"folds={[round(f, 1) for f in r['folds']]}")


def md_table(df, index=False):
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)


def grid_row(i, p, best, bounds, src):
    tr, diag = build_trades(p)
    full = C.evaluate(tr, 3, *PERIOD)
    is_ = C.evaluate(run_fn(p, *bounds[0]), 1)
    o = C.oos_result(pd.concat([run_fn(p, *bounds[1]), run_fn(p, *bounds[2])]), PERIOD, 3)
    longs = tr[tr["leg"] == "long"] if len(tr) else tr
    hed = tr[tr["leg"] == "hedge"] if len(tr) else tr
    row = dict(idx=i, name=pname(p), is_n=is_["n"], is_net=is_["net"], is_pf=is_["pf"],
               oos_n=o["n"], oos_net=o["net"], oos_pf=o["pf"], f1=full["folds"][0],
               f2=full["folds"][1], f3=full["folds"][2], full_net=full["net"],
               long_net=C.evaluate(longs, 1)["net"] if len(longs) else 0.0,
               hedge_net=C.evaluate(hed, 1)["net"] if len(hed) else 0.0,
               fees=full["fees"], funding=float(tr["funding_usd"].sum()) if len(tr) else 0.0,
               turnover=diag["turnover"], n_rebal=diag["n_rebal"], avg_univ=diag["avg_univ"],
               avg_long=diag["avg_long"], maker_fill=diag["maker_fill_rate"], selected=(p == best))
    C.record_to_lab(STRATEGY, pname(p) + "_full", "HL_XSEC_PIT", f"{p['rebal_d']}d", p, full,
                    period=PERIOD, source=src,
                    notes=f"full-period all folds (IS incl.); PIT universe top{TOP_N}/30d vol, >=${LIQ_USD/1e6:.0f}M 24h; "
                          f"turnover={diag['turnover']:.2f} n_rebal={diag['n_rebal']} avg_univ={diag['avg_univ']:.1f} "
                          f"maker_fill={diag['maker_fill_rate']:.2f} long_net={row['long_net']:.1f} hedge_net={row['hedge_net']:.1f}")
    C.record_to_lab(STRATEGY, pname(p) + "_is_f1", "HL_XSEC_PIT", f"{p['rebal_d']}d", p,
                    C.evaluate(run_fn(p, *bounds[0]), 3, *PERIOD), period=bounds[0], source=src,
                    notes="fold-1 in-sample grid cell")
    return row


def main():
    src = Path(__file__).name
    bounds = C.fold_bounds(PERIOD, 3)
    n_univ = MASK.sum(axis=1)
    print("period", PERIOD, "folds", [(s.date(), e.date()) for s, e in bounds])
    print(f"panel: {len(COINS)} coins with 1h data in period; PIT universe size per day: "
          f"min={n_univ.min()} mean={n_univ.mean():.1f} max={n_univ.max()}")
    ever = [COINS[j] for j in np.where(MASK.any(axis=0))[0]]
    print(f"coins ever in PIT universe: {len(ever)}; of which in round-1 snapshot-50: {len(set(ever) & SNAP50)}")
    no_fund = [c for c in ever if c not in P["fund_cum"]]
    print("coins in universe without funding history:", no_fund)
    # overlap of PIT universe with the hindsight snapshot, by fold
    snap_j = np.array([c in SNAP50 for c in COINS])
    overlap = (MASK & snap_j).sum(axis=1) / np.maximum(MASK.sum(axis=1), 1)
    fl = C.fold_labels(pd.Series(DAY_OPENS), 3, *PERIOD)
    overlap_by_fold = [float(overlap[fl == k].mean()) for k in range(3)]
    print("fraction of PIT universe that is in the snapshot-50, by fold:", np.round(overlap_by_fold, 2))

    # --- walk-forward ---------------------------------------------------------
    best, oos_tr, table = C.walk_forward(GRID, run_fn, PERIOD, n_folds=3, min_trades=10)
    oos = C.oos_result(oos_tr, PERIOD, 3)
    print("\nBEST (fold-1 selected):", best)
    print("OOS (folds 2+3):", fmt(oos))

    grid = pd.DataFrame([grid_row(i, p, best, bounds, src) for i, p in enumerate(GRID)])
    pd.set_option("display.width", 300)
    print("\nIN-SAMPLE (fold 1) GRID + fold-2/3 sensitivity (combo signal):")
    print(grid.round(2).to_string(index=False))

    C.record_to_lab(STRATEGY, "WF_OOS_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d", best, oos,
                    period=(bounds[1][0], bounds[2][1]), source=src,
                    notes="HEADLINE walk-forward OOS folds 2+3, params selected on fold 1; PIT universe; funding incl.")

    # --- arms: momentum-only / reversal-only (same structure grid) ------------
    arms = []
    for sig in ("mom", "rev"):
        for R, q, h in itertools.product([1, 7], [0.1, 0.2], [0, 1]):
            p = dict(best, rebal_d=R, quantile=q, hedge=h, signal=sig)
            arms.append(grid_row(100 + len(arms), p, None, bounds, src))
    arms = pd.DataFrame(arms)
    print("\nARMS momentum-only / reversal-only (exec = selected exec), full-period folds:")
    print(arms.round(2).to_string(index=False))

    # --- sanity (a): random-bucket shuffle on the OOS period --------------------
    sh = []
    for s in range(1, 41):
        ps = dict(best, _shuffle=s)
        tr = pd.concat([run_fn(ps, *bounds[1]), run_fn(ps, *bounds[2])])
        sh.append(C.evaluate(tr, 1)["net"])
    sh = np.array(sh)
    sh_p = float((sh >= oos["net"]).mean())
    print(f"\nSHUFFLE (random bucket, 40 reps, OOS): mean={sh.mean():.1f} sd={sh.std():.1f} "
          f"p(shuffle>=real)={sh_p:.2f} real={oos['net']:.1f}")
    C.record_to_lab(STRATEGY, "SHUFFLE_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d",
                    dict(best, shuffle="mean_of_40"), dict(C.empty_result(), n=int(oos["n"]), net=float(sh.mean())),
                    period=(bounds[1][0], bounds[2][1]), source=src,
                    notes=f"shuffle control: sd={sh.std():.1f} p(shuffle>=real)={sh_p:.2f}")

    # --- sanity (c): neighbours ---------------------------------------------------
    def neigh(p, b):
        return sum(p[k] != b[k] for k in ("rebal_d", "quantile", "hedge", "exec")) == 1
    nb = grid[[neigh(GRID[i], best) for i in grid["idx"]]]
    nb_pos = int((nb["oos_net"] > 0).sum())
    print("\nNEIGHBOURS of best (one param changed), OOS nets:")
    print(nb[["name", "oos_n", "oos_net", "oos_pf", "f2", "f3"]].round(2).to_string(index=False))

    # --- survivorship: same params on the hindsight snapshot-50 universe ---------
    ps = dict(best, _universe=sorted(SNAP50))
    surv_tr = pd.concat([run_fn(ps, *bounds[1]), run_fn(ps, *bounds[2])])
    surv = C.oos_result(surv_tr, PERIOD, 3)
    surv_full = C.evaluate(build_trades(ps)[0], 3, *PERIOD)
    print(f"\nSURVIVORSHIP: OOS on snapshot-50 (hindsight) universe: {fmt(surv)}\n"
          f"              full-period folds hindsight: {np.round(surv_full['folds'],1)}  vs PIT: "
          f"{np.round(C.evaluate(build_trades(best)[0], 3, *PERIOD)['folds'],1)}")
    C.record_to_lab(STRATEGY, "SURV_SNAP50_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d",
                    dict(best, universe="snapshot50"), surv, period=(bounds[1][0], bounds[2][1]), source=src,
                    notes="survivorship check: hindsight snapshot-50 universe, OOS folds 2+3")

    # --- hedged arm of the selected structure must be positive in both OOS folds --
    hb = dict(best, hedge=1)
    hedged_oos = C.oos_result(pd.concat([run_fn(hb, *bounds[1]), run_fn(hb, *bounds[2])]), PERIOD, 3)
    print(f"\nHEDGED arm ({pname(hb)}) OOS: {fmt(hedged_oos)}")
    btc_o = pd.Series(P["O"][:, BTC], index=DAY_OPENS)
    btc_ret = [float(btc_o[(btc_o.index >= s) & (btc_o.index < e)].iloc[-1] /
                     btc_o[(btc_o.index >= s) & (btc_o.index < e)].iloc[0] - 1) for s, e in bounds]
    print("BTC return by fold:", np.round(btc_ret, 3))

    # --- sanity (d): per coin / liquidity / legs --------------------------------
    t = C.add_pnl(oos_tr) if len(oos_tr) else pd.DataFrame()
    per_coin = pd.DataFrame(); liq_split = {}; leg_split = {}; fill_split = {}
    if len(t):
        per_coin = t.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"),
                                               funding=("funding_usd", "sum"),
                                               vol24=("vol24_entry", "median")).sort_values("net")
        lg = t[t["leg"] == "long"].copy()
        lg["thin"] = lg["vol24_entry"] < 2 * LIQ_USD
        liq_split = lg.groupby("thin")["net_pnl"].agg(["size", "sum"]).to_dict("index")
        leg_split = t.groupby("leg")["net_pnl"].agg(["size", "sum"]).to_dict("index")
        fill_split = t.groupby("maker_entry")["net_pnl"].agg(["size", "sum"]).to_dict("index")
        print("\nPER-COIN OOS (worst 8 / best 8):")
        print(per_coin.head(8).round(1).to_string()); print(per_coin.tail(8).round(1).to_string())
        print("liquidity split of long legs (thin = 24h vol < $10M at entry):", liq_split)
        print("leg split:", leg_split, " maker-entry split:", fill_split)
        print(f"OOS funding={t['funding_usd'].sum():.1f} fees={t['fee_usd'].sum():.1f} "
              f"gross_ex_funding={(t['gross_pnl'] - t['funding_usd']).sum():.1f} delist_exits={int(t['delist'].sum())}")

    # --- (e) weekly-anchor phase robustness + concentration + per-rebalance t-stat --
    phase_nets = []
    for ph in range(int(best["rebal_d"])):
        pp = dict(best, _phase=ph)
        tr_ph = pd.concat([run_fn(pp, *bounds[1]), run_fn(pp, *bounds[2])])
        r_ph = C.oos_result(tr_ph, PERIOD, 3)
        phase_nets.append(dict(phase=ph, oos_n=r_ph["n"], oos_net=r_ph["net"], oos_pf=r_ph["pf"],
                               f2=r_ph["folds"][1], f3=r_ph["folds"][2]))
        if ph:
            C.record_to_lab(STRATEGY, f"PHASE{ph}_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d", pp, r_ph,
                            period=(bounds[1][0], bounds[2][1]), source=src,
                            notes=f"weekly rebalance anchor shifted by {ph} days; OOS folds 2+3")
    phase_df = pd.DataFrame(phase_nets)
    phase_pos = int((phase_df["oos_net"] > 0).sum())
    print("\nWEEKLY ANCHOR PHASE (OOS):"); print(phase_df.round(2).to_string(index=False))
    n_long = int((t["leg"] == "long").sum()) if len(t) else 0
    lg_sorted = np.sort(t[t["leg"] == "long"]["net_pnl"].values) if len(t) else np.array([])
    ex_top1 = float(lg_sorted[:-1].sum()) if len(lg_sorted) > 1 else 0.0
    ex_top3 = float(lg_sorted[:-3].sum()) if len(lg_sorted) > 3 else 0.0
    med_long = float(np.median(lg_sorted)) if len(lg_sorted) else 0.0
    wk = t.groupby(t["entry_time"].dt.floor("D"))["net_pnl"].sum() if len(t) else pd.Series(dtype=float)
    t_stat = float(wk.mean() / wk.std() * np.sqrt(len(wk))) if len(wk) > 1 and wk.std() > 0 else 0.0
    print(f"\nCONCENTRATION: long trades n={n_long} net={float(lg_sorted.sum()):.1f} ex-top1={ex_top1:.1f} "
          f"ex-top3={ex_top3:.1f} median={med_long:.1f}; per-rebalance book PnL n={len(wk)} "
          f"mean={wk.mean() if len(wk) else 0:.1f} sd={wk.std() if len(wk) else 0:.1f} t={t_stat:.2f} "
          f"pos={int((wk > 0).sum())}/{len(wk)}")

    # --- verdict --------------------------------------------------------------------
    oos_folds = oos["folds"][1:]
    crit = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=n_long >= 60,
                folds=all(f > 0 for f in oos_folds), shuffle=sh_p < 0.05,
                neighbors=(nb_pos >= max(1, len(nb) // 2)),
                hedged_both_folds=all(f > 0 for f in hedged_oos["folds"][1:]),
                phase=(phase_pos >= max(1, int(np.ceil(0.75 * len(phase_df))))),
                not_tail_driven=(ex_top3 > 0 and t_stat >= 2.0))
    verdict = "edge" if all(crit.values()) else ("weak" if oos["net"] > 0 else "none")
    print("\nCRITERIA:", crit, "VERDICT:", verdict)

    # --- markdown -------------------------------------------------------------------
    md = [f"# h_xsec_mom30_rev1_hedged - long-only z(30d) - z(1d) book, point-in-time HL universe\n",
          f"Data: {len(COINS)} HL perps with 1h data in {PERIOD[0].date()} -> {PERIOD[1].date()} (176 listed + "
          f"delisted perps; 1d candles for the lookbacks, 1h 00:00 bar for fills). "
          f"Folds: {[(str(s.date()), str(e.date())) for s, e in bounds]}.\n",
          f"Universe (point-in-time, at each 23:00 signal): trailing-24h USD vol >= ${LIQ_USD/1e6:.0f}M, top-{TOP_N} by "
          f"trailing-30d USD vol, >= 31 daily closes. Size/day: min {n_univ.min()}, mean {n_univ.mean():.1f}, "
          f"max {n_univ.max()}; {len(ever)} coins ever eligible ({len(set(ever) & SNAP50)} of them in the round-1 "
          f"snapshot-50). Fraction of the PIT universe that is in the snapshot-50 by fold: {np.round(overlap_by_fold, 2).tolist()}.\n",
          "Execution: score = z(30d ret) - z(1d ret) at the 23:00 close; long top-q, $1000/name, fill at the 00:00 bar "
          "(taker at open, or maker limit at open filled only if the bar trades through, else taker at that bar's close); "
          "keep names that stay in the bucket; optional equal-notional BTC short hedge resized at each rebalance "
          "(fee on the adjustment only). Hourly funding folded into exit_px.\n",
          f"## Headline (walk-forward OOS, folds 2+3)\n\nSelected on fold 1: `{best}`\n\n"
          f"| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |\n|---|---|---|---|---|---|---|---|---|\n"
          f"| {oos['n']} | {oos['net']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | {oos['sharpe']:.2f} | "
          f"{oos['max_dd']:.1f} | {oos['net_bps']:.1f} | {oos_folds[0]:.2f} | {oos_folds[1]:.2f} |\n",
          f"Hedged arm of the selected structure ({pname(hb)}) OOS: n={hedged_oos['n']} net={hedged_oos['net']:.2f} "
          f"pf={hedged_oos['pf']:.2f} fold2={hedged_oos['folds'][1]:.2f} fold3={hedged_oos['folds'][2]:.2f}. "
          f"BTC return by fold: {np.round(btc_ret, 3).tolist()}.\n",
          "## In-sample grid (fold 1) with fold 2/3 nets (combo signal)\n", md_table(grid.drop(columns=["idx"]).round(2)) + "\n",
          "## Momentum-only / reversal-only arms (selected exec mode), full-period folds\n",
          md_table(arms.drop(columns=["idx", "selected"]).round(2)) + "\n",
          "## Sanity checks\n",
          f"- (a) Shuffle (random long bucket, 40 reps, OOS): mean {sh.mean():.1f}, sd {sh.std():.1f}, "
          f"P(shuffle >= real) = {sh_p:.2f}; real = {oos['net']:.1f}.\n"
          f"- (b) OOS folds: fold2 {oos_folds[0]:.2f}, fold3 {oos_folds[1]:.2f}.\n"
          f"- (c) Neighbours of best (one param changed): {nb_pos}/{len(nb)} positive OOS net.\n\n"
          + md_table(nb[["name", "oos_n", "oos_net", "oos_pf", "f2", "f3"]].round(2)) + "\n",
          f"- Survivorship: same params on the hindsight snapshot-50 universe, OOS: n={surv['n']} net={surv['net']:.2f} "
          f"pf={surv['pf']:.2f} folds={np.round(surv['folds'],1).tolist()}; full-period folds hindsight "
          f"{np.round(surv_full['folds'],1).tolist()} vs PIT {np.round(C.evaluate(build_trades(best)[0], 3, *PERIOD)['folds'],1).tolist()}.\n"]
    if len(t):
        md.append(f"- (d) Long-leg liquidity split (thin = 24h vol < $10M at entry; all names >= $5M by construction): {liq_split}\n"
                  f"- Leg split: {leg_split}\n- Maker-entry split: {fill_split}\n"
                  f"- OOS funding {t['funding_usd'].sum():.1f}, fees {t['fee_usd'].sum():.1f}, delisting exits {int(t['delist'].sum())}\n\n"
                  "Per-coin OOS:\n\n" + md_table(per_coin.round(1), index=True) + "\n")
    md.append("- (e) Weekly-anchor phase robustness (rebalance day shifted by 0..R-1 days), OOS:\n\n"
              + md_table(phase_df.round(2)) + "\n\n"
              f"- Concentration: long trades n={n_long}, net {float(lg_sorted.sum()):.1f}, ex-top-1 {ex_top1:.1f}, "
              f"ex-top-3 {ex_top3:.1f}, median long trade {med_long:.1f}; per-rebalance book PnL n={len(wk)}, "
              f"mean {wk.mean() if len(wk) else 0:.1f}, sd {wk.std() if len(wk) else 0:.1f}, t={t_stat:.2f}, "
              f"positive {int((wk > 0).sum())}/{len(wk)}.\n")
    md.append(f"## Criteria\n\n`{crit}` (n = long-leg trades only; hedge rows excluded)\n\n## Verdict: **{verdict}**\n")
    OUT_MD.write_text("\n".join(md))
    print("wrote", OUT_MD)

    result = dict(best=best, oos=oos, oos_folds=oos_folds, sh_p=sh_p, sh_mean=float(sh.mean()), nb_pos=nb_pos,
                  nb_n=len(nb), verdict=verdict, crit=crit, is_best_net=float(grid[grid["selected"]]["is_net"].iloc[0]),
                  hedged_oos=hedged_oos, surv=surv, liq_split=liq_split, leg_split=leg_split, btc_ret=btc_ret,
                  grid=grid.to_dict("records"), arms=arms.to_dict("records"), overlap_by_fold=overlap_by_fold,
                  phase=phase_nets, n_long=n_long, ex_top1=ex_top1, ex_top3=ex_top3, med_long=med_long, t_stat=t_stat)
    OUT_JSON.write_text(json.dumps(result, default=str, indent=1))
    return result


if __name__ == "__main__":
    main()
