"""Round 3 / key=funding_xsec_carry

Dollar-neutral cross-sectional funding carry on Hyperliquid (point-in-time
universe, 194 perps with 1h data in the period, incl. later-delisted names).

Signal (strictly causal): at every 00:00 UTC day open, rank the eligible names
by the trailing-W-hour mean of the hourly funding rate using ONLY funding rows
paid at or before 23:00 of the previous day (row at 00:00 is excluded).
  LONG  the bottom-q fraction (most negative funding: shorts pay longs)
  SHORT the top-q fraction    (most positive funding: longs pay shorts)
$1,000 notional per name.  Eligibility at the signal: trailing-24h USD volume
>= $5M (from the 1d candle that closed at the signal), >= 30 daily closes
listed, a bar at the 00:00 open, >= 90% of the W funding rows present.

Book mechanics: hold while the name stays in its decile (re-ranked daily),
hard exit after H days, exit when the coin's trailing-24h mean funding sign
flips against the position, exit (settle at last close, taker) if it drops out
of the panel (delisting).
Execution arms:
  maker : limit at the 00:00 open, entry counted filled ONLY if the 00:00 bar
          trades through the limit by >= 1 tick (low <= open - tick for buys,
          high >= open + tick for sells) - otherwise the entry is skipped that
          day; exits: maker at the open on the same rule, taker fallback at the
          00:00 bar's close.
  taker : fill at the 00:00 open, taker fee both sides.
PnL = hourly funding accrued on mark notional (funding rows paid in
(entry_hour, exit_hour], mark = open of that hour) + price - fees.  Funding is
folded into exit_px so common.evaluate() sees the total; price_pnl and
funding_usd are kept as columns for the decomposition.
Walk-forward: grid (q x W x H = 12 per arm) selected on fold 1 only; headline =
folds 2+3 of the maker arm (the arm the hypothesis specifies).
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import common as C  # noqa: E402
import xsec_pit_data as D  # noqa: E402

OUT_MD = ROOT / "tests" / "h_funding_xsec_carry.md"
OUT_JSON = ROOT / "tests" / "h_funding_xsec_carry_result.json"
STRATEGY = "funding_xsec_carry"
INSTR = "HL_XSEC_PIT"
TF = "1d"
NOTIONAL = 1000.0
LIQ_USD = 5e6
MIN_LISTED_D = 30
MIN_NAMES = 8
SEED = 7
N_SHUFFLE = 200
SRC = str(Path(__file__).relative_to(ROOT.parent.parent))


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def load_panel():
    listed, delisted = D.all_coins()
    coins_all = listed + [c for c in delisted if c not in listed]
    ref = C.hl_candles("BTC", "1h")
    t0, t1 = ref.index[0], ref.index[-1]
    hours = pd.date_range(t0, t1, freq="h", tz="UTC")
    bars, daily = {}, {}
    for c in coins_all:
        p1, pdd = D.path_1h(c), D.path_1d(c)
        if not (p1.exists() and pdd.exists()):
            continue
        h, d = D.read(p1), D.read(pdd)
        if h is None or d is None:
            continue
        h = h[(h.index >= t0) & (h.index <= t1)]
        if len(h) == 0:
            continue
        bars[c], daily[c] = h, d
    coins = sorted(bars)
    n_h, n_c = len(hours), len(coins)
    Oh = np.full((n_h, n_c), np.nan); Hh = Oh.copy(); Lh = Oh.copy(); Ch = Oh.copy()
    Fh = np.full((n_h, n_c), np.nan)
    no_fund = []
    for j, c in enumerate(coins):
        b = bars[c].reindex(hours)
        Oh[:, j], Hh[:, j], Lh[:, j], Ch[:, j] = b["open"], b["high"], b["low"], b["close"]
        p = D.path_fund(c)
        f = D.read(p) if p.exists() else None
        if f is None or len(f) == 0:
            no_fund.append(c)
            continue
        f.index = f.index.floor("h")
        f = f[~f.index.duplicated(keep="last")]
        Fh[:, j] = f["fundingRate"].astype(float).reindex(hours).values
    day_opens = hours[hours.hour == 0]
    hidx = hours.get_indexer(day_opens)
    days = pd.DatetimeIndex(day_opens - pd.Timedelta(days=1))   # 1d candle that closed at the signal
    d_close = pd.DataFrame({c: daily[c]["close"] for c in coins}).sort_index()
    d_vol = pd.DataFrame({c: daily[c]["volume"] * daily[c]["close"] for c in coins}).sort_index()
    full_idx = pd.date_range(min(d_close.index[0], days[0] - pd.Timedelta(days=40)), days[-1], freq="D", tz="UTC")
    d_close, d_vol = d_close.reindex(full_idx), d_vol.reindex(full_idx)
    n_listed = d_close.notna().cumsum().reindex(days).values
    vol24 = d_vol.reindex(days).values
    # mark for funding accrual at hour h = open of bar h (forward-filled over gaps)
    mark = pd.DataFrame(Oh).ffill().values
    G = np.cumsum(np.nan_to_num(Fh) * np.nan_to_num(mark), axis=0)      # cum funding USD per 1 coin, paid by longs
    Fcum = np.cumsum(np.nan_to_num(Fh), axis=0)
    Fcnt = np.cumsum(np.isfinite(Fh).astype(int), axis=0)
    u = pd.read_parquet(C.DATA / "hl_universe_all.parquet")
    szdec = dict(zip(u["coin"], u["szDecimals"].astype(int)))
    sz = np.array([szdec.get(c, -1) for c in coins])
    return dict(coins=coins, hours=hours, day_opens=day_opens, hidx=hidx, Oh=Oh, Hh=Hh, Lh=Lh, Ch=Ch,
                Fh=Fh, G=G, Fcum=Fcum, Fcnt=Fcnt, n_listed=n_listed, vol24=vol24, sz=sz, no_fund=no_fund,
                bars=bars)


def trailing_mean(P, W):
    """(n_days x n_coins) mean hourly funding over the W rows paid in
    [00:00 - W h, 23:00] of the previous day, and the count of rows present."""
    hi = P["hidx"]
    lo = hi - W - 1                              # row hi-1 is 23:00 of D-1 -> sum rows (lo, hi-1]
    ok = lo >= 0
    s = np.full((len(hi), P["Fcum"].shape[1]), np.nan); n = np.zeros_like(s)
    s[ok] = P["Fcum"][hi[ok] - 1] - P["Fcum"][lo[ok]]
    n[ok] = P["Fcnt"][hi[ok] - 1] - P["Fcnt"][lo[ok]]
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(n > 0, s / n, np.nan)
    return m, n


P = load_panel()
COINS = P["coins"]; CIDX = {c: j for j, c in enumerate(COINS)}
DAY_OPENS = P["day_opens"]; HIDX = P["hidx"]; N_D = len(DAY_OPENS)
PERIOD = (P["hours"][0], P["hours"][-1])
BOUNDS = C.fold_bounds(PERIOD, 3)
SCORES = {W: trailing_mean(P, W) for W in (8, 24, 72)}
S24 = SCORES[24][0]
BASE_ELIG = np.isfinite(P["Oh"][HIDX]) & (P["vol24"] >= LIQ_USD) & (P["n_listed"] >= MIN_LISTED_D) & np.isfinite(S24)
SNAP50 = set(C.hl_universe()["coin"])
RNG = np.random.default_rng(SEED)


def tick(px, j):
    """Hyperliquid perp tick: 5 significant figures, at most 6 - szDecimals decimals."""
    t1 = 10.0 ** (math.floor(math.log10(px)) - 4)
    s = P["sz"][j]
    t2 = 10.0 ** (-(6 - s)) if s >= 0 else 0.0
    return max(t1, t2)


def fill(i, j, side, mode):
    """Fill at the 00:00 bar of day i for coin j.  Returns (px, maker, through).
    maker mode: px = open if the bar traded through by >= 1 tick, else None."""
    hi = HIDX[i]
    o = P["Oh"][hi, j]
    if not np.isfinite(o):
        return None, False, False
    if mode == "taker":
        return o, False, True
    tk = tick(o, j)
    through = (P["Lh"][hi, j] <= o - tk) if side > 0 else (P["Hh"][hi, j] >= o + tk)
    if through:
        return o, True, True
    return None, False, False


def funding_usd(j, side, qty, he, hx):
    """Funding cash flow in USD for `side` x qty coins over hours (he, hx]."""
    return -side * qty * (P["G"][hx, j] - P["G"][he, j])


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------
_CACHE: dict = {}


def build_trades(params):
    key = json.dumps(params, sort_keys=True)
    if key in _CACHE:
        return _CACHE[key]
    q, W, H, mode = float(params["q"]), int(params["W"]), int(params["H"]), params["exec"]
    shuffle = int(params.get("_shuffle", 0))
    restrict = params.get("_universe")
    liq = float(params.get("_liq", LIQ_USD))
    score_all, cnt_all = SCORES[W]
    rng = np.random.default_rng(SEED + shuffle) if shuffle else None
    rows = []; pos = {}
    n_elig, n_long, n_short, n_skip, n_try = [], [], [], 0, 0
    for i in range(N_D):
        t = DAY_OPENS[i]; hi = HIDX[i]
        elig = BASE_ELIG[i] & np.isfinite(score_all[i]) & (cnt_all[i] >= 0.9 * W)
        if liq != LIQ_USD:
            elig = np.isfinite(P["Oh"][hi]) & (P["vol24"][i] >= liq) & (P["n_listed"][i] >= MIN_LISTED_D) \
                & np.isfinite(S24[i]) & np.isfinite(score_all[i]) & (cnt_all[i] >= 0.9 * W)
        if restrict is not None:
            elig &= np.isin(np.array(COINS), list(restrict))
        idx = np.where(elig)[0]
        n_elig.append(len(idx))
        sc = score_all[i, idx].copy(); s24 = S24[i, idx].copy()
        if shuffle and len(idx):
            perm = rng.permutation(len(idx)); sc, s24 = sc[perm], s24[perm]
        sign24 = dict(zip(idx, np.sign(s24)))
        if len(idx) < MIN_NAMES:
            longs, shorts = set(), set()
        else:
            k = max(1, int(np.floor(len(idx) * q)))
            order = np.argsort(sc, kind="stable")
            longs, shorts = set(idx[order[:k]]), set(idx[order[-k:]])
        # ---- exits -------------------------------------------------------
        for j in list(pos):
            p = pos[j]
            held = i - p["i"]
            in_bucket = (j in longs) if p["side"] > 0 else (j in shorts)
            flip = (j in sign24) and (sign24[j] * p["side"] > 0)     # long & funding now positive, or short & negative
            if not np.isfinite(P["Oh"][hi, j]):
                reason = "delist"
            elif held >= H:
                reason = "maxhold"
            elif flip:
                reason = "flip"
            elif not in_bucket:
                reason = "bucket"
            else:
                continue
            rows.append(_close(j, pos.pop(j), i, mode, reason))
        # ---- entries -----------------------------------------------------
        for side, tgt in ((+1, longs), (-1, shorts)):
            for j in tgt:
                if j in pos:
                    continue
                n_try += 1
                px, mk, through = fill(i, j, side, mode)
                if px is None:
                    n_skip += 1
                    continue
                pos[j] = dict(side=side, i=i, t=t, px=px, qty=NOTIONAL / px, maker=mk,
                              vol24=P["vol24"][i, j], score=score_all[i, j])
        n_long.append(sum(1 for p in pos.values() if p["side"] > 0))
        n_short.append(sum(1 for p in pos.values() if p["side"] < 0))
    i_end = N_D - 1
    for j, p in list(pos.items()):
        if p["i"] < i_end:
            rows.append(_close(j, p, i_end, mode, "end"))
    trades = pd.DataFrame(rows)
    diag = dict(avg_elig=float(np.mean(n_elig)), avg_long=float(np.mean(n_long)), avg_short=float(np.mean(n_short)),
                entry_skip_rate=(n_skip / n_try if n_try else np.nan), n_try=n_try)
    _CACHE[key] = (trades, diag)
    return trades, diag


def _close(j, p, i, mode, reason):
    coin = COINS[j]; hi = HIDX[i]; he = HIDX[p["i"]]
    t_exit = DAY_OPENS[i]; hx = hi
    if reason == "delist":
        cl = P["Ch"][:, j]
        cand = np.where(np.isfinite(cl[he + 1:hi + 1]))[0]
        if len(cand):
            hx = he + 1 + cand[-1]
        else:
            hx = he
        px, mk = float(P["Ch"][hx, j]) if np.isfinite(P["Ch"][hx, j]) else p["px"], False
        t_exit = P["hours"][hx] + pd.Timedelta(hours=1)
    else:
        px, mk, through = fill(i, j, -p["side"], mode)
        if px is None:                       # maker exit not filled -> taker at the bar close
            px, mk = float(P["Ch"][hi, j]), False
    qty = p["qty"]
    row = C.crypto_trade(p["t"], t_exit, p["side"], p["px"], px, qty, coin,
                         maker_entry=bool(p["maker"]), maker_exit=bool(mk))
    fu = funding_usd(j, p["side"], qty, he, hx)
    price = p["side"] * (px - p["px"]) * qty
    row.update(exit_px_raw=px, exit_px=px + p["side"] * fu / qty, funding_usd=fu, price_pnl=price,
               leg="long" if p["side"] > 0 else "short", maker_entry=bool(p["maker"]), maker_exit=bool(mk),
               vol24_entry=p["vol24"], score_entry=p["score"], hold_days=i - p["i"], exit_reason=reason,
               entry_i=p["i"], exit_i=i, entry_h=he, exit_h=hx, j=j)
    return row


def run_fn(params, start, end):
    tr, _ = build_trades(params)
    if len(tr) == 0:
        return tr
    m = (tr["entry_time"] >= start) & (tr["entry_time"] < end)
    return tr[m].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Daily book series (mark-to-market at the 00:00 opens)
# ---------------------------------------------------------------------------
def daily_book(trades):
    """Daily book PnL (USD), day d = from open d to open d+1: price + funding
    accrued in the day, entry fee on the entry day, exit fee on the last day."""
    pnl = np.zeros(N_D)
    mark = pd.DataFrame(P["Oh"]).ffill().values
    for r in trades.itertuples(index=False):
        j, side, qty = int(r.j), float(r.side), float(r.qty)
        ei, xi = int(r.entry_i), int(r.exit_i)
        fee_in = C.hl_fee(qty * r.entry_px, r.maker_entry)
        fee_out = float(r.fee_usd) - fee_in
        for d in range(ei, max(xi, ei + 1)):
            h0 = HIDX[d] if d > ei else int(r.entry_h)
            last = (d >= xi - 1)
            h1 = int(r.exit_h) if last else HIDX[d + 1]
            p0 = r.entry_px if d == ei else mark[HIDX[d], j]
            p1 = r.exit_px_raw if last else mark[HIDX[d + 1], j]
            v = side * qty * (p1 - p0) + funding_usd(j, side, qty, h0, h1)
            if d == ei:
                v -= fee_in
            if last:
                v -= fee_out
            pnl[d] += v
    return pd.Series(pnl, index=DAY_OPENS)


def ew_basket():
    """Equal-weight daily return of the liquid alt universe (eligible names ex BTC/ETH), open d -> open d+1."""
    O = P["Oh"][HIDX]
    ret = np.full(N_D, np.nan)
    ex = np.isin(np.array(COINS), ["BTC", "ETH"])
    for d in range(N_D - 1):
        m = BASE_ELIG[d] & ~ex & np.isfinite(O[d]) & np.isfinite(O[d + 1])
        if m.sum() >= 3:
            ret[d] = np.mean(O[d + 1, m] / O[d, m] - 1.0)
    return pd.Series(ret, index=DAY_OPENS)


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else 0.0


# ---------------------------------------------------------------------------
# Grid / reporting helpers
# ---------------------------------------------------------------------------
def grid(exec_mode):
    return [dict(q=q, W=W, H=H, exec=exec_mode) for q, W, H in itertools.product([0.1, 0.2], [8, 24, 72], [3, 7])]


def pname(p):
    return f"{p['exec']}_q{p['q']}_W{p['W']}_H{p['H']}"


def fmt(r):
    return (f"n={r['n']} net={r['net']:.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:.2f} "
            f"dd={r['max_dd']:.2f} bps={r['net_bps']:.1f} folds={[round(f, 2) for f in r['folds']]}")


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in r.values) + " |")
    return "\n".join(out)


def decomp(tr):
    if len(tr) == 0:
        return dict(n=0, net=0.0, price=0.0, funding=0.0, fees=0.0)
    t = C.add_pnl(tr)
    return dict(n=int(len(t)), net=float(t["net_pnl"].sum()), price=float(t["price_pnl"].sum()),
                funding=float(t["funding_usd"].sum()), fees=float(t["fee_usd"].sum()))


def oos_of(tr):
    """Folds 2+3 slice of a full-period trade list."""
    if len(tr) == 0:
        return tr
    return tr[tr["entry_time"] >= BOUNDS[1][0]].reset_index(drop=True)


def grid_row(p, best, exec_mode):
    tr, dg = build_trades(p)
    full = C.evaluate(tr, 3, *PERIOD)
    f1 = C.evaluate(run_fn(p, *BOUNDS[0]), 1)
    oo = C.oos_result(oos_of(tr), PERIOD, 3)
    dc = decomp(oos_of(tr))
    name = pname(p)
    C.record_to_lab(STRATEGY, name + "_full", INSTR, TF, p, full, period=PERIOD, source=SRC,
                    notes=f"full period all folds (IS incl.); PIT universe >= ${LIQ_USD/1e6:.0f}M 24h, >= {MIN_LISTED_D}d listed; "
                          f"oos23 price={dc['price']:.1f} funding={dc['funding']:.1f} fees={dc['fees']:.1f}; "
                          f"avg_elig={dg['avg_elig']:.1f} skip={dg['entry_skip_rate']:.2f}")
    C.record_to_lab(STRATEGY, name + "_is_f1", INSTR, TF, p, f1, period=BOUNDS[0], source=SRC,
                    notes="fold-1 in-sample grid cell (selection fold)")
    return dict(name=name, is_n=f1["n"], is_net=round(f1["net"], 2), is_pf=round(f1["pf"], 2), is_wr=round(f1["wr"], 2),
                oos_n=oo["n"], oos_net=round(oo["net"], 2), oos_pf=round(oo["pf"], 2),
                f1=round(full["folds"][0], 2), f2=round(full["folds"][1], 2), f3=round(full["folds"][2], 2),
                full_net=round(full["net"], 2), oos_price=round(dc["price"], 1), oos_fund=round(dc["funding"], 1),
                oos_fees=round(dc["fees"], 1), avg_elig=round(dg["avg_elig"], 1), avg_long=round(dg["avg_long"], 2),
                avg_short=round(dg["avg_short"], 2), skip=round(dg["entry_skip_rate"], 2),
                selected=(best is not None and pname(best) == name))


# ---------------------------------------------------------------------------
def main():
    print(f"panel: {len(COINS)} coins, {N_D} day opens {DAY_OPENS[0]} -> {DAY_OPENS[-1]}; folds {[(str(a.date()), str(b.date())) for a, b in BOUNDS]}")
    print("coins with no funding history:", P["no_fund"])
    ne = BASE_ELIG.sum(axis=1)
    ever = [COINS[j] for j in np.where(BASE_ELIG.any(axis=0))[0]]
    print(f"eligible/day min {ne.min()} mean {ne.mean():.1f} max {ne.max()}; ever eligible {len(ever)} ({len(set(ever) & SNAP50)} in snapshot-50)")
    # funding spread diagnostic
    m24 = S24.copy(); m24[~BASE_ELIG] = np.nan
    okd = np.isfinite(m24).sum(axis=1) >= MIN_NAMES
    srt = np.sort(np.where(np.isfinite(m24[okd]), m24[okd], np.nan), axis=1)
    top = float(np.nanmean([np.nanmean(r[np.isfinite(r)][-3:]) for r in srt]))
    bot = float(np.nanmean([np.nanmean(r[np.isfinite(r)][:3]) for r in srt]))
    print(f"mean 24h funding of top-3 / bottom-3 names (days with >= {MIN_NAMES} eligible): {top*1e4:.2f} / {bot*1e4:.2f} bps/h")

    # ---- walk-forward, maker arm (headline) ----------------------------------
    G_M, G_T = grid("maker"), grid("taker")
    best, oos_tr, table = C.walk_forward(G_M, run_fn, PERIOD, n_folds=3, select_by="net", min_trades=10)
    oos = C.oos_result(oos_tr, PERIOD, 3)
    print("\nMAKER best:", best, "\nOOS:", fmt(oos))
    C.record_to_lab(STRATEGY, "WF_OOS_" + pname(best), INSTR, TF, best, oos, period=(BOUNDS[1][0], BOUNDS[2][1]),
                    source=SRC, notes="HEADLINE walk-forward OOS folds 2+3, params selected on fold 1; maker arm (entry only if bar trades through by >= 1 tick)")
    best_t, oos_tr_t, table_t = C.walk_forward(G_T, run_fn, PERIOD, n_folds=3, select_by="net", min_trades=10)
    oos_t = C.oos_result(oos_tr_t, PERIOD, 3)
    print("TAKER best:", best_t, "\nOOS:", fmt(oos_t))
    C.record_to_lab(STRATEGY, "WF_OOS_TAKER_" + pname(best_t), INSTR, TF, best_t, oos_t, period=(BOUNDS[1][0], BOUNDS[2][1]),
                    source=SRC, notes="walk-forward OOS folds 2+3, taker arm (fill at 00:00 open, taker both sides)")

    rows_m = [grid_row(p, best, "maker") for p in G_M]
    rows_t = [grid_row(p, best_t, "taker") for p in G_T]
    tab_m = pd.DataFrame(rows_m).sort_values("is_net", ascending=False)
    tab_t = pd.DataFrame(rows_t).sort_values("is_net", ascending=False)
    print("\nIN-SAMPLE GRID (maker)\n", tab_m.to_string(index=False))
    print("\nIN-SAMPLE GRID (taker)\n", tab_t.to_string(index=False))

    # ---- decomposition / legs / ex-top-3 (OOS, best maker) ---------------------
    dc = decomp(oos_tr)
    legs = {}
    for leg in ("long", "short"):
        sub = oos_tr[oos_tr["leg"] == leg].reset_index(drop=True)
        r = C.oos_result(sub, PERIOD, 3); legs[leg] = dict(r=r, d=decomp(sub))
        C.record_to_lab(STRATEGY, f"LEG_{leg.upper()}_" + pname(best), INSTR, TF, dict(best, leg=leg), r,
                        period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC, notes=f"{leg} leg only of the headline OOS book")
    print(f"\nOOS decomposition: {dc}")
    for leg in legs:
        print(f"  {leg}: {fmt(legs[leg]['r'])} decomp={legs[leg]['d']}")
    t_oos = C.add_pnl(oos_tr)
    by_coin = t_oos.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), price=("price_pnl", "sum"),
                                              funding=("funding_usd", "sum"), wr=("net_pnl", lambda x: float((x > 0).mean())),
                                              vol24=("vol24_entry", "median")).sort_values("net", ascending=False)
    top3 = by_coin.index[:3].tolist()
    ex3 = C.oos_result(oos_tr[~oos_tr["instrument"].isin(top3)].reset_index(drop=True), PERIOD, 3)
    print(f"ex-top-3 {top3}: {fmt(ex3)}")
    C.record_to_lab(STRATEGY, "EXTOP3_" + pname(best), INSTR, TF, dict(best, ex=top3), ex3,
                    period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC, notes="headline OOS excluding the 3 best-contributing coins")
    by_reason = t_oos.groupby("exit_reason").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), hold=("hold_days", "mean"))
    by_hold = t_oos.groupby("hold_days").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), funding=("funding_usd", "sum"))
    print(by_reason, "\n", by_hold)
    thin = t_oos.groupby(t_oos["vol24_entry"] < 2 * LIQ_USD).agg(n=("net_pnl", "size"), net=("net_pnl", "sum"))
    print("thin (<$10M) split:\n", thin)
    # post-hoc diagnostic (NOT a result): OOS net by |entry score| bucket (bps/h) and by leg
    t_oos["abs_score_bph"] = t_oos["score_entry"].abs() * 1e4
    t_oos["score_bucket"] = pd.cut(t_oos["abs_score_bph"], [0, 0.5, 1, 2, 5, 1e9], labels=["<0.5", "0.5-1", "1-2", "2-5", ">5"])
    by_score = t_oos.groupby(["score_bucket", "leg"], observed=True).agg(n=("net_pnl", "size"), net=("net_pnl", "sum"),
                                                                          price=("price_pnl", "sum"), funding=("funding_usd", "sum"))
    print("OOS by |entry funding| bucket x leg:\n", by_score)
    carry_bph = t_oos["funding_usd"].sum() / (t_oos["hold_days"].sum() * 24) / NOTIONAL * 1e4
    print(f"realised carry per name-hour (OOS): {carry_bph:.2f} bps/h; per name-day {carry_bph*24:.1f} bps vs maker RT fee 3 bps")

    # ---- daily book t-stat + alt-beta regression (OOS days) --------------------
    full_tr, _ = build_trades(best)
    book = daily_book(full_tr)
    bask = ew_basket()
    lab = C.fold_labels(pd.Series(DAY_OPENS), 3, *PERIOD)
    oos_days = lab >= 1
    b_oos = book[oos_days]; x_oos = bask[oos_days]
    t_book = tstat(b_oos.values)
    print(f"\ndaily book (OOS): n_days={len(b_oos)} mean={b_oos.mean():.2f} sd={b_oos.std():.2f} t={t_book:.2f} sum={b_oos.sum():.2f}"
          f"  (check vs trade-list OOS net {oos['net']:.2f}; difference = trades entered in fold 1 that exit in fold 2)")
    import statsmodels.api as sm
    m = np.isfinite(x_oos.values) & np.isfinite(b_oos.values)
    X = sm.add_constant(x_oos.values[m] * 100)     # basket return in %
    ols = sm.OLS(b_oos.values[m], X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    alpha, beta = ols.params; t_alpha, t_beta = ols.tvalues
    print(f"alt-beta regression: alpha={alpha:.2f} USD/day (t={t_alpha:.2f}), beta={beta:.2f} USD per 1% basket move (t={t_beta:.2f}), R2={ols.rsquared:.3f}")
    fold_t = {k: tstat(book[lab == k].values) for k in range(3)}
    print("daily book t-stat by fold:", {k: round(v, 2) for k, v in fold_t.items()})

    # ---- shuffle -------------------------------------------------------------
    nulls = []
    for s in range(1, N_SHUFFLE + 1):
        tr, _ = build_trades(dict(best, _shuffle=s))
        nulls.append(C.evaluate(oos_of(tr), 1)["net"])
    nulls = np.array(nulls)
    p_sh = float((nulls >= oos["net"]).mean())
    print(f"\nSHUFFLE ({N_SHUFFLE} reps, signals permuted across eligible coins each day): null mean={nulls.mean():.2f} "
          f"sd={nulls.std():.2f} p95={np.percentile(nulls, 95):.2f} actual={oos['net']:.2f} p={p_sh:.3f}")
    C.record_to_lab(STRATEGY, "SHUFFLE_" + pname(best), INSTR, TF, dict(best, shuffle_reps=N_SHUFFLE),
                    dict(C.empty_result(), n=int(oos["n"]), net=float(nulls.mean()), wr=p_sh, folds=[0.0, 0.0, 0.0]),
                    period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC,
                    notes=f"shuffle null: mean OOS net of {N_SHUFFLE} random-decile books; wr field = p(null >= actual); actual={oos['net']:.2f} sd={nulls.std():.2f}")

    # ---- neighbours ----------------------------------------------------------
    def neighbours(b):
        out = []
        for k, vals in (("q", [0.1, 0.2]), ("W", [8, 24, 72]), ("H", [3, 7])):
            for v in vals:
                if v != b[k]:
                    out.append(dict(b, **{k: v}))
        return out
    nb = []
    for p in neighbours(best):
        tr, _ = build_trades(p)
        r = C.oos_result(oos_of(tr), PERIOD, 3)
        nb.append(dict(name=pname(p), oos_n=r["n"], oos_net=round(r["net"], 2), oos_pf=round(r["pf"], 2),
                       f2=round(r["folds"][1], 2), f3=round(r["folds"][2], 2)))
    nb = pd.DataFrame(nb)
    n_nb_pos = int((nb["oos_net"] > 0).sum())
    print("\nNEIGHBOURS\n", nb.to_string(index=False))

    # ---- universe controls ---------------------------------------------------
    ctrl = {}
    for tag, extra in (("snap50", dict(_universe=sorted(SNAP50))), ("liq2m", dict(_liq=2e6)), ("liq20m", dict(_liq=2e7))):
        tr, dg = build_trades(dict(best, **extra))
        r = C.oos_result(oos_of(tr), PERIOD, 3); d = decomp(oos_of(tr))
        ctrl[tag] = dict(r=r, d=d, avg_elig=dg["avg_elig"])
        print(f"UNIVERSE {tag}: {fmt(r)} decomp={d} avg_elig={dg['avg_elig']:.1f}")
        C.record_to_lab(STRATEGY, f"UNIV_{tag.upper()}_" + pname(best), INSTR, TF, dict(best, universe=tag), r,
                        period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC,
                        notes=f"universe control {tag}; oos price={d['price']:.1f} funding={d['funding']:.1f} fees={d['fees']:.1f}")

    # ---- verdict -------------------------------------------------------------
    crit = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=oos["n"] >= 60,
                folds=all(f > 0 for f in oos["folds"][1:]), shuffle=p_sh <= 0.05,
                neighbors=n_nb_pos >= math.ceil(len(nb) / 2))
    if all(crit.values()):
        verdict = "edge"
    elif oos["net"] > 0:
        verdict = "weak"
    else:
        verdict = "none"
    print("\nVERDICT:", verdict, crit)

    # ---- markdown --------------------------------------------------------------
    md = [f"# funding_xsec_carry - dollar-neutral cross-sectional funding carry, point-in-time HL universe\n",
          f"Data: {len(COINS)} HL perps with 1h data in {PERIOD[0].date()} -> {PERIOD[1].date()} (listed + delisted), hourly funding "
          f"for all but {P['no_fund']}. Folds: {[(str(a.date()), str(b.date())) for a, b in BOUNDS]} (~69d each).\n",
          f"Universe at each 00:00 signal: trailing-24h USD vol >= ${LIQ_USD/1e6:.0f}M, >= {MIN_LISTED_D} daily closes, funding history present. "
          f"Eligible/day min {ne.min()} mean {ne.mean():.1f} max {ne.max()}; {len(ever)} coins ever eligible ({len(set(ever) & SNAP50)} in the snapshot-50). "
          f"Mean trailing-24h funding of the top-3 / bottom-3 names: {top*1e4:.2f} / {bot*1e4:.2f} bps/h.\n",
          "Signal: trailing-W-hour mean hourly funding using rows paid <= 23:00 of D-1; LONG bottom-q, SHORT top-q, $1,000/name, "
          "hold while in decile, hard exit at H days, exit on 24h funding sign flip, settle at last close on delisting. "
          "Maker arm: limit at the 00:00 open filled only if the bar trades through by >= 1 tick (else entry skipped / exit taker at bar close). "
          "Taker arm: fill at the open, taker both sides. Funding accrued hourly on mark notional, folded into exit_px.\n",
          "## Headline (walk-forward OOS, folds 2+3, maker arm)\n",
          f"Selected on fold 1: `{best}`\n",
          "| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 | price | funding | fees |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|",
          f"| {oos['n']} | {oos['net']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | {oos['sharpe']:.2f} | {oos['max_dd']:.1f} | {oos['net_bps']:.1f} | "
          f"{oos['folds'][1]:.2f} | {oos['folds'][2]:.2f} | {dc['price']:.1f} | {dc['funding']:.1f} | {dc['fees']:.1f} |\n",
          f"Taker arm (own walk-forward): selected `{best_t}` -> {fmt(oos_t)}\n",
          "### Legs (OOS)\n",
          "| leg | n | net | pf | wr | fold2 | fold3 | price | funding | fees |", "|---|---|---|---|---|---|---|---|---|---|"]
    for leg in legs:
        r, d = legs[leg]["r"], legs[leg]["d"]
        md.append(f"| {leg} | {r['n']} | {r['net']:.2f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['folds'][1]:.2f} | {r['folds'][2]:.2f} | "
                  f"{d['price']:.1f} | {d['funding']:.1f} | {d['fees']:.1f} |")
    md += ["", f"Ex-top-3 names ({top3}): {fmt(ex3)}\n",
           f"Daily book (mark-to-market at 00:00 opens), OOS days: n={len(b_oos)} mean={b_oos.mean():.2f} USD/day sd={b_oos.std():.2f} "
           f"t={t_book:.2f}; t by fold {dict((k, round(v, 2)) for k, v in fold_t.items())}.\n",
           f"Alt-beta regression of daily book PnL on the EW liquid-alt basket (OOS, HAC): alpha={alpha:.2f} USD/day (t={t_alpha:.2f}), "
           f"beta={beta:.2f} USD per 1% basket move (t={t_beta:.2f}), R2={ols.rsquared:.3f}.\n",
           "Exit reasons (OOS):\n", md_table(by_reason.reset_index()), "\nHold days (OOS):\n", md_table(by_hold.reset_index()),
           "\n## In-sample grid (fold 1) with fold 2/3 nets - maker arm\n", md_table(tab_m),
           "\n## In-sample grid (fold 1) with fold 2/3 nets - taker arm\n", md_table(tab_t),
           "\n## Sanity checks\n",
           f"- (a) Shuffle ({N_SHUFFLE} reps; each day the funding signals are permuted across the eligible coins, same book mechanics): "
           f"null mean {nulls.mean():.2f}, sd {nulls.std():.2f}, p95 {np.percentile(nulls, 95):.2f}; actual {oos['net']:.2f}; P(null >= actual) = {p_sh:.3f}.",
           f"- (b) OOS folds: fold2 {oos['folds'][1]:.2f}, fold3 {oos['folds'][2]:.2f} (n {oos['fold_n'][1]}/{oos['fold_n'][2]}).",
           f"- (c) Neighbours (one parameter changed): {n_nb_pos}/{len(nb)} positive OOS net.\n", md_table(nb),
           "\n- (d) Per-coin OOS (best maker):\n", md_table(by_coin.reset_index().round(2)),
           f"\nThin split (24h vol < $10M at entry; all >= $5M by construction): {thin.to_dict()}\n",
           f"Realised carry per name-hour (OOS): {carry_bph:.2f} bps/h = {carry_bph*24:.1f} bps per name-day vs 3 bps maker round trip.\n",
           "Post-hoc diagnostic (not a result): OOS net by |entry funding| bucket (bps/h) x leg:\n", md_table(by_score.reset_index().round(1)),
           "Universe controls (best params, OOS folds 2+3):\n",
           "| universe | avg elig | n | net | pf | fold2 | fold3 | price | funding | fees |", "|---|---|---|---|---|---|---|---|---|---|"]
    for tag, v in ctrl.items():
        r, d = v["r"], v["d"]
        md.append(f"| {tag} | {v['avg_elig']:.1f} | {r['n']} | {r['net']:.2f} | {r['pf']:.2f} | {r['folds'][1]:.2f} | {r['folds'][2]:.2f} | "
                  f"{d['price']:.1f} | {d['funding']:.1f} | {d['fees']:.1f} |")
    md += ["", f"## Verdict: **{verdict}**\n", f"criteria: `{crit}`\n"]
    OUT_MD.write_text("\n".join(md))

    res = dict(key="funding_xsec_carry", carry_bph=carry_bph, top3_bph=top*1e4, bot3_bph=bot*1e4, best_params=best, oos=oos, oos_taker=oos_t, best_taker=best_t, decomp=dc,
               legs={k: dict(r=v["r"], d=v["d"]) for k, v in legs.items()}, ex_top3=dict(names=top3, r=ex3),
               book_t=t_book, book_t_by_fold=fold_t, alpha=alpha, t_alpha=t_alpha, beta=beta, t_beta=t_beta,
               shuffle=dict(mean=float(nulls.mean()), sd=float(nulls.std()), p=p_sh), neighbours=nb.to_dict("records"),
               n_nb_pos=n_nb_pos, controls={k: dict(r=v["r"], d=v["d"]) for k, v in ctrl.items()},
               grid_maker=rows_m, grid_taker=rows_t, verdict=verdict, criteria=crit,
               period=[str(PERIOD[0]), str(PERIOD[1])], folds=[[str(a), str(b)] for a, b in BOUNDS])
    OUT_JSON.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print("wrote", OUT_MD, OUT_JSON)


if __name__ == "__main__":
    main()
