"""Round 3 / key=xsec_wide_book_altshedge

Sharpened version of round-2 xsec_mom30_rev1_hedged.
  score(t) = z(30d ret) - z(k-day ret) [+ z(-funding_24h) in the 'fund' arm],
  z = cross-sectional z-score at the 23:00 UTC close (daily candle of day
  D-1); fills at the 00:00 UTC 1h bar of day D (strictly causal).
Universe (point-in-time, incl. later-delisted perps): >= 31 daily closes,
  trailing-24h USD volume >= $1M, top-80 by trailing-30d USD volume.
Book: long top-q, $1,000 per name, hold until the name drops out of the
  bucket at a rebalance (base), or -25% per-name stop (hourly close, exit at
  next 1h open) / 14-day max hold with a one-rebalance cooldown (arms).
Hedge (headline): short a beta-scaled, equal-notional, EQUAL-WEIGHT liquid-
  alt basket (top-20 by trailing-30d volume, ex-book, ex-BTC/PAXG), resized
  at every rebalance; hedge funding accrued on the mark notional; fees on the
  per-name adjustments only.  BTC-hedge and unhedged arms = controls.
Accounting: HEADLINE = realized-only (positions still open at sample end are
  EXCLUDED; the mark-to-market version is shown separately).
Walk-forward: 18-cell pre-registered grid selected on fold 1 only; headline =
  folds 2+3.  Rolling walk-forward (select on fold 2, test on fold 3) also
  reported.  Execution headline = taker (4.5 bps/side); maker touch-through
  arm reported.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import common as C  # noqa: E402
import xsec_pit_data as D  # noqa: E402

OUT_MD = ROOT / "tests" / "h_xsec_wide_book_altshedge.md"
OUT_JSON = ROOT / "tests" / "h_xsec_wide_book_altshedge_result.json"
STRATEGY = "xsec_wide_book_altshedge"
NOTIONAL = 1000.0
LIQ_USD = 1e6          # trailing-24h USD volume gate at signal time
TOP_N = 80             # by trailing-30d USD volume
MIN_NAMES = 15
L_MOM = 30
BASKET_N = 20
BASKET_EXCL = {"BTC", "PAXG"}
BETA_CLIP = (0.3, 2.0)
STOP_PCT = 0.25
MAX_HOLD_D = 14
SEED = 11
N_SHUFFLE = 1000

# ---------------------------------------------------------------------------
# Data / panel
# ---------------------------------------------------------------------------
def load_panel():
    listed, delisted = D.all_coins()
    coins_all = listed + [c for c in delisted if c not in listed]
    D.ensure_candles(coins_all, verbose=False)
    ref = C.hl_candles("BTC", "1h")
    t0, t1 = ref.index[0], ref.index[-1]
    hours = None
    bars, daily = {}, {}
    for c in coins_all:
        h = D.read(D.path_1h(c)); d = D.read(D.path_1d(c))
        if h is None or d is None:
            continue
        h = h[(h.index >= t0) & (h.index <= t1)]
        if len(h) == 0:
            continue
        bars[c] = h; daily[c] = d
        hours = h.index if hours is None else hours.union(h.index)
    hours = hours[(hours >= t0) & (hours <= t1)]
    coins = sorted(bars)
    day_opens = hours[hours.hour == 0]
    n_d, n_c, n_h = len(day_opens), len(coins), len(hours)
    O = np.full((n_d, n_c), np.nan); H = O.copy(); Lo = O.copy(); Cl = O.copy()
    HO = np.full((n_h, n_c), np.nan); HC = HO.copy()
    for j, c in enumerate(coins):
        b = bars[c].reindex(day_opens)
        O[:, j], H[:, j], Lo[:, j], Cl[:, j] = b["open"], b["high"], b["low"], b["close"]
        hb = bars[c].reindex(hours)
        HO[:, j], HC[:, j] = hb["open"], hb["close"]
    days = pd.DatetimeIndex(day_opens - pd.Timedelta(days=1))    # daily candle that CLOSED at day_opens[i]
    d_close = pd.DataFrame({c: daily[c]["close"] for c in coins}).sort_index()
    d_vol = pd.DataFrame({c: daily[c]["volume"] * daily[c]["close"] for c in coins}).sort_index()
    full_idx = pd.date_range(min(d_close.index[0], days[0] - pd.Timedelta(days=40)), days[-1], freq="D", tz="UTC")
    d_close = d_close.reindex(full_idx); d_vol = d_vol.reindex(full_idx)
    ret_mom = (d_close / d_close.shift(L_MOM) - 1.0).reindex(days).values
    ret_k = {k: (d_close / d_close.shift(k) - 1.0).reindex(days).values for k in (1, 2, 3)}
    d_ret1 = (d_close / d_close.shift(1) - 1.0)                       # daily returns, full history
    vol30 = d_vol.rolling(30, min_periods=20).sum().reindex(days).values
    vol24 = d_vol.reindex(days).values
    return dict(coins=coins, day_opens=day_opens, hours=hours, O=O, H=H, Lo=Lo, Cl=Cl, HO=HO, HC=HC,
                ret_mom=ret_mom, ret_k=ret_k, vol30=vol30, vol24=vol24, bars=bars,
                d_close=d_close, d_ret1=d_ret1, days=days)


def universe_mask(P):
    ok = np.isfinite(P["ret_mom"]) & np.isfinite(P["ret_k"][3]) & np.isfinite(P["O"]) \
        & np.isfinite(P["vol30"]) & (P["vol24"] >= LIQ_USD)
    v = np.where(ok, P["vol30"], -np.inf)
    mask = np.zeros_like(ok)
    for i in range(ok.shape[0]):
        n_ok = int(ok[i].sum())
        if n_ok == 0:
            continue
        mask[i, np.argsort(-v[i])[:min(TOP_N, n_ok)]] = True
    return mask


def basket_mask(P):
    """Liquid-alt basket candidates per day: top-20 by 30d vol among names with
    30d history and 24h vol >= $1M, ex BTC/PAXG."""
    ok = np.isfinite(P["ret_mom"]) & np.isfinite(P["O"]) & np.isfinite(P["vol30"]) & (P["vol24"] >= LIQ_USD)
    excl = np.array([c in BASKET_EXCL for c in P["coins"]])
    ok &= ~excl
    v = np.where(ok, P["vol30"], -np.inf)
    return ok, v


def build_funding(P, mask):
    coins = P["coins"]
    ever = [coins[j] for j in np.where(mask.any(axis=0))[0]]
    ever = sorted(set(ever) | {"BTC"})
    need = [c for c in ever if not D.path_fund(c).exists()]
    if need:
        print("fetching funding for", len(need), "coins", flush=True)
        D.ensure_funding(need, verbose=False)
    hours = P["hours"]
    FC = np.zeros((len(hours), len(coins)))          # cumulative hourly funding aligned to `hours`
    F24 = np.full((len(P["day_opens"]), len(coins)), np.nan)
    have = []
    for j, c in enumerate(coins):
        p = D.path_fund(c)
        if not p.exists():
            continue
        f = D.read(p)
        if f is None:
            continue
        f.index = f.index.floor("h")
        f = f[~f.index.duplicated(keep="last")]["fundingRate"].astype(float).sort_index()
        cum = f.cumsum().reindex(hours, method="ffill").fillna(0.0).values
        FC[:, j] = cum
        have.append(c)
        # trailing-24h funding sum known at the 23:00 close of D-1 (events with time <= 23:00 D-1)
        f24 = f.rolling(24, min_periods=1).sum()
        F24[:, j] = f24.reindex(P["day_opens"] - pd.Timedelta(hours=1), method="ffill").values
    P["FC"] = FC; P["F24"] = F24; P["fund_coins"] = set(have)
    return P


t_load = time.time()
P = load_panel()
MASK = universe_mask(P)
BOK, BV = basket_mask(P)
P = build_funding(P, MASK | BOK)
COINS = P["coins"]; CIDX = {c: j for j, c in enumerate(COINS)}
DAY_OPENS = P["day_opens"]; HOURS = P["hours"]
HPOS = {t: i for i, t in enumerate(HOURS)}
DAY_HPOS = np.array([HPOS[t] for t in DAY_OPENS])
PERIOD = (HOURS[0], HOURS[-1])
BTC = CIDX["BTC"]
RNG = np.random.default_rng(SEED)
print(f"panel loaded in {time.time()-t_load:.0f}s: {len(COINS)} coins, {len(DAY_OPENS)} days", flush=True)


def hpos(t):
    """Index of the last hour <= t in HOURS."""
    return int(np.searchsorted(HOURS.values, np.datetime64(t.tz_convert("UTC").tz_localize(None)), side="right") - 1)


def funding_usd(j, side, notional, t_entry, t_exit):
    """USD funding PnL of a `side` position of `notional` USD over (t_entry, t_exit]."""
    a, b = hpos(t_entry), hpos(t_exit)
    return -side * notional * (P["FC"][b, j] - P["FC"][a, j])


def zs(x):
    x = np.asarray(x, float)
    m, s = np.nanmean(x), np.nanstd(x)
    if not np.isfinite(s) or s == 0:
        return np.zeros_like(x)
    z = (x - m) / s
    return np.where(np.isfinite(z), z, 0.0)


def fill(i, j, side, mode):
    o = P["O"][i, j]
    if mode == "taker":
        return o, False
    through = (P["Lo"][i, j] < o) if side > 0 else (P["H"][i, j] > o)
    if through:
        return o, True
    return P["Cl"][i, j], False


def book_beta(i, book_idx, basket_idx):
    """Trailing-30d beta of the equal-weight book to the equal-weight basket,
    from daily returns up to and including the candle that closed at DAY_OPENS[i]."""
    d_end = P["days"][i]
    r = P["d_ret1"].loc[:d_end].iloc[-30:]
    rb = r.iloc[:, list(book_idx)].mean(axis=1)
    rk = r.iloc[:, list(basket_idx)].mean(axis=1)
    m = rb.notna() & rk.notna()
    if m.sum() < 15 or rk[m].var() == 0:
        return 1.0
    beta = float(np.cov(rb[m], rk[m])[0, 1] / rk[m].var())
    return float(np.clip(beta, *BETA_CLIP))


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------
_CACHE: dict = {}


def build_trades(params):
    key = json.dumps(params, sort_keys=True)
    if key in _CACHE:
        return _CACHE[key]
    R = int(params["rebal_d"]); k = int(params["k"]); q = float(params["quantile"])
    hedge = params.get("hedge", "alt"); mode = params.get("exec", "taker"); sig = params.get("signal", "combo")
    exit_rule = params.get("exit", "rank")
    shuffle = int(params.get("_shuffle", 0)); phase = int(params.get("_phase", 0)) % R
    rows = []; open_pos = {}; cooldown = set()
    n_univ = []; n_long = []; betas = []
    hedge_pos = {}       # coin j -> dict(notional, px_entry, mk)
    hedge_t = None; hedge_H = 0.0; hedge_fee_pending = 0.0
    rebal_idx = list(range(phase, len(DAY_OPENS), R))
    i_end = len(DAY_OPENS) - 1
    for i in rebal_idx:
        t = DAY_OPENS[i]
        # ---- intra-period exits (stop) since the previous rebalance ----------
        if exit_rule == "stop" and open_pos:
            for j in list(open_pos):
                p = open_pos[j]
                h0 = hpos(p["entry_time"]) + 1; h1 = DAY_HPOS[i]
                cl = P["HC"][h0:h1, j]
                hit = np.where(cl <= p["entry_px"] * (1 - STOP_PCT))[0]
                if len(hit):
                    hx = h0 + hit[0] + 1
                    if hx < h1 and np.isfinite(P["HO"][hx, j]):
                        rows.append(_close_long_at(j, open_pos.pop(j), HOURS[hx], float(P["HO"][hx, j]), False, reason="stop"))
        m = MASK[i]
        idx = np.where(m)[0]
        n_univ.append(len(idx))
        if len(idx) < MIN_NAMES:
            target = set()
        else:
            sc = zs(P["ret_mom"][i, idx]) - zs(P["ret_k"][k][i, idx])
            if sig == "fund":
                sc = sc + zs(-P["F24"][i, idx])
            elif sig == "mom":
                sc = zs(P["ret_mom"][i, idx])
            elif sig == "rev":
                sc = -zs(P["ret_k"][k][i, idx])
            if shuffle:
                sc = RNG.permutation(sc)
            kk = max(1, int(np.floor(len(idx) * q)))
            target = set(idx[np.argsort(-sc)[:kk]])
        # ---- max-hold forced realisation (cooldown one rebalance) -----------
        if exit_rule == "maxhold":
            for j in list(open_pos):
                if (t - open_pos[j]["entry_time"]) >= pd.Timedelta(days=MAX_HOLD_D):
                    rows.append(_close_long(j, open_pos.pop(j), i, mode, reason="maxhold"))
                    cooldown.add(j)
            target -= cooldown
        # ---- rank-drop exits --------------------------------------------------
        for j in list(open_pos):
            if j not in target:
                rows.append(_close_long(j, open_pos.pop(j), i, mode, reason="rank"))
        # ---- new entries -----------------------------------------------------
        for j in target:
            if j in open_pos:
                continue
            px, mk = fill(i, j, +1, mode)
            if not np.isfinite(px):
                continue
            open_pos[j] = dict(entry_time=t, entry_px=px, qty=NOTIONAL / px, maker=mk, vol24=P["vol24"][i, j])
        cooldown = set()
        n_long.append(len(open_pos))
        # ---- hedge ------------------------------------------------------------
        if hedge != "none":
            book = list(open_pos)
            if hedge == "alt":
                cand = np.where(BOK[i] & ~np.isin(np.arange(len(COINS)), book))[0]
                cand = cand[np.argsort(-BV[i][cand])][:BASKET_N]
                basket = [int(j) for j in cand if np.isfinite(P["O"][i, j])]
            else:
                basket = [BTC]
            beta = book_beta(i, book, basket) if (book and basket) else 1.0
            betas.append(beta)
            H_new = beta * NOTIONAL * len(book) if basket else 0.0
            # close the running hedge interval at this rebalance
            if hedge_t is not None:
                rows.append(_close_hedge_interval(hedge_pos, hedge_t, i, mode, hedge_fee_pending, final=False))
            # resize: per-name target notionals
            tgt = {j: H_new / len(basket) for j in basket} if H_new > 0 else {}
            new_pos = {}; fee = 0.0
            for j in set(hedge_pos) | set(tgt):
                old = hedge_pos.get(j, {}).get("notional", 0.0); new = tgt.get(j, 0.0)
                delta = new - old
                if abs(delta) > 1e-9:
                    px, mk = fill(i, j, -1 if delta > 0 else +1, mode)
                    if not np.isfinite(px):
                        px, mk = P["Cl"][i, j], False
                    fee += C.hl_fee(abs(delta), mk)
                else:
                    px, mk = P["O"][i, j], True
                if new > 0:
                    new_pos[j] = dict(notional=new, px=px)
            if not new_pos and fee > 0 and rows and rows[-1]["leg"] == "hedge":
                rows[-1]["fee_usd"] += fee          # full buy-back when the book empties
                fee = 0.0
            hedge_pos = new_pos; hedge_fee_pending = fee; hedge_H = H_new
            hedge_t = t if hedge_pos else None
    # ---- end of sample: mark open positions (flagged, excluded from realized) --
    for j, p in list(open_pos.items()):
        if p["entry_time"] < DAY_OPENS[i_end]:
            rows.append(_close_long(j, p, i_end, mode, reason="end"))
    if hedge_t is not None and hedge_t < DAY_OPENS[i_end]:
        rows.append(_close_hedge_interval(hedge_pos, hedge_t, i_end, mode, hedge_fee_pending, final=True))
    trades = pd.DataFrame(rows)
    if len(trades):
        trades["final_mark"] = trades["reason"] == "end"
    diag = dict(n_rebal=len(rebal_idx), avg_univ=float(np.mean(n_univ)) if n_univ else 0.0,
                avg_long=float(np.mean(n_long)) if n_long else 0.0,
                avg_beta=float(np.mean(betas)) if betas else np.nan,
                maker_fill_rate=(float(trades.loc[trades["leg"] == "long", "maker_entry"].mean()) if len(trades) else np.nan))
    _CACHE[key] = (trades, diag)
    return trades, diag


def _close_long_at(j, p, t_exit, px, mk, reason):
    coin = COINS[j]
    row = C.crypto_trade(p["entry_time"], t_exit, +1, p["entry_px"], px, p["qty"], coin,
                         maker_entry=p["maker"], maker_exit=mk)
    fu = funding_usd(j, +1, NOTIONAL, p["entry_time"], t_exit)
    row.update(exit_px_raw=px, funding_usd=fu, exit_px=px + fu / p["qty"], leg="long", reason=reason,
               maker_entry=bool(p["maker"]), maker_exit=bool(mk), vol24_entry=p["vol24"], delist=False)
    return row


def _close_long(j, p, i, mode, reason):
    coin = COINS[j]
    t_exit = DAY_OPENS[i]
    px, mk = fill(i, j, -1, mode)
    delist = False
    if not np.isfinite(px):
        b = P["bars"][coin]
        b = b[(b.index > p["entry_time"]) & (b.index <= t_exit)]
        if len(b) == 0:
            b = P["bars"][coin][P["bars"][coin].index <= t_exit]
        t_exit = b.index[-1] + pd.Timedelta(hours=1)
        px, mk, delist = float(b["close"].iloc[-1]), False, True
    row = _close_long_at(j, p, t_exit, px, mk, reason)
    row["delist"] = delist
    return row


def _close_hedge_interval(hedge_pos, t_entry, i, mode, fee_entry, final):
    """One synthetic row for the short basket over [t_entry, DAY_OPENS[i]]:
    entry_px=1, exit_px=1+basket_ret-funding/H, side=-1, qty=H (USD)."""
    t_exit = DAY_OPENS[i]
    H = sum(p["notional"] for p in hedge_pos.values())
    pnl_px = 0.0; fu = 0.0; fee_exit = 0.0
    for j, p in hedge_pos.items():
        px, mk = fill(i, j, +1, mode)
        if not np.isfinite(px):
            px, mk = P["Cl"][i, j], False
            if not np.isfinite(px):
                b = P["bars"][COINS[j]]; b = b[b.index <= t_exit]
                px = float(b["close"].iloc[-1])
        pnl_px += p["notional"] * (px / p["px"] - 1.0)
        fu += funding_usd(j, -1, p["notional"], t_entry, t_exit)
        if final:
            fee_exit += C.hl_fee(p["notional"], mk)
    r_b = pnl_px / H
    exit_px = 1.0 + r_b - fu / H
    return dict(entry_time=t_entry, exit_time=t_exit, side=-1, entry_px=1.0, exit_px=exit_px, qty=H,
                notional_usd=H, fee_usd=fee_entry + fee_exit, instrument="ALTBASKET" if len(hedge_pos) > 1 else "BTC",
                multiplier=1.0, exit_px_raw=1.0 + r_b, funding_usd=fu, leg="hedge",
                reason="end" if final else "roll", maker_entry=False, maker_exit=False, vol24_entry=np.nan, delist=False)


def realized(tr):
    return tr[~tr["final_mark"]].reset_index(drop=True) if len(tr) else tr


def run_fn(params, start, end, mtm=False):
    tr, _ = build_trades(params)
    if len(tr) == 0:
        return tr
    if not mtm:
        tr = realized(tr)
    m = (tr["entry_time"] >= start) & (tr["entry_time"] < end)
    return tr[m].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Grid / helpers
# ---------------------------------------------------------------------------
GRID = [dict(rebal_d=R, k=k, quantile=q, hedge="alt", exec="taker", signal="combo", exit="rank")
        for R, k, q in itertools.product([3, 5, 7], [1, 2, 3], [0.2, 0.3])]
assert len(GRID) <= 24


def pname(p):
    return (f"{p.get('signal','combo')}_R{p['rebal_d']}_k{p['k']}_q{p['quantile']}_h{p.get('hedge','alt')}"
            f"_{p.get('exec','taker')}_x{p.get('exit','rank')}")


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:.2f} "
            f"dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} folds={[round(f, 1) for f in r['folds']]}")


def md_table(df, index=False):
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)


def ev_split(tr, bounds):
    """Book / long-leg / hedge-leg evaluate dicts for a trade frame."""
    book = C.evaluate(tr, 3, *PERIOD) if len(tr) else C.empty_result()
    lg = tr[tr["leg"] == "long"] if len(tr) else tr
    hd = tr[tr["leg"] == "hedge"] if len(tr) else tr
    return book, (C.evaluate(lg, 3, *PERIOD) if len(lg) else C.empty_result()), \
        (C.evaluate(hd, 3, *PERIOD) if len(hd) else C.empty_result())


def oos_frame(p, bounds, mtm=False):
    return pd.concat([run_fn(p, *bounds[1], mtm=mtm), run_fn(p, *bounds[2], mtm=mtm)], ignore_index=True)


def decision_stats(tr):
    """Per-rebalance-decision book PnL (long trades + hedge interval opened at that decision)."""
    if len(tr) == 0:
        return 0, 0.0, 0.0, 0.0, 0
    t = C.add_pnl(tr)
    wk = t.groupby("entry_time")["net_pnl"].sum()
    n = len(wk); mu = wk.mean(); sd = wk.std(ddof=1) if n > 1 else np.nan
    tstat = mu / sd * np.sqrt(n) if (n > 1 and sd > 0) else 0.0
    return n, float(mu), float(sd), float(tstat), int((wk > 0).sum())


def concentration(tr):
    lg = C.add_pnl(tr[tr["leg"] == "long"]) if len(tr) else tr
    if len(lg) == 0:
        return dict(n_long=0, long_net=0.0, ex_top1=0.0, ex_top3=0.0, median=0.0, top3=[])
    s = lg.sort_values("net_pnl", ascending=False)
    v = s["net_pnl"].values
    return dict(n_long=len(v), long_net=float(v.sum()), ex_top1=float(v[1:].sum()), ex_top3=float(v[3:].sum()),
                median=float(np.median(v)), top3=[(r.instrument, round(r.net_pnl, 1)) for r in s.head(3).itertuples()])


def grid_row(i, p, best, bounds, src, tag=""):
    tr, diag = build_trades(p)
    rz = realized(tr)
    full_book, full_long, full_hedge = ev_split(rz, bounds)
    mtm_book = C.evaluate(tr, 3, *PERIOD) if len(tr) else C.empty_result()
    is_ = C.evaluate(run_fn(p, *bounds[0]), 1)
    o_tr = oos_frame(p, bounds)
    o = C.oos_result(o_tr, PERIOD, 3)
    ol = o_tr[o_tr["leg"] == "long"]
    n_dec, mu, sd, tst, npos = decision_stats(o_tr)
    conc = concentration(o_tr)
    row = dict(idx=i, name=pname(p), is_n=is_["n"], is_net=is_["net"], is_pf=is_["pf"],
               oos_n_long=int(len(ol)), oos_net=o["net"], oos_pf=o["pf"], f2=o["folds"][1], f3=o["folds"][2],
               oos_mtm_net=C.oos_result(oos_frame(p, bounds, mtm=True), PERIOD, 3)["net"],
               oos_t=tst, oos_ndec=n_dec, oos_ex_top3=conc["ex_top3"],
               full_net=full_book["net"], f1=full_book["folds"][0], long_net=full_long["net"],
               hedge_net=full_hedge["net"], mtm_net=mtm_book["net"], fees=full_book["fees"],
               funding=float(rz["funding_usd"].sum()) if len(rz) else 0.0,
               n_rebal=diag["n_rebal"], avg_univ=diag["avg_univ"], avg_long=diag["avg_long"],
               avg_beta=diag["avg_beta"], maker_fill=diag["maker_fill_rate"], selected=(p == best))
    C.record_to_lab(STRATEGY, tag + pname(p) + "_full", "HL_XSEC_PIT", f"{p['rebal_d']}d", p, full_book,
                    period=PERIOD, source=src,
                    notes=f"full-period REALIZED book (long+hedge), PIT universe top{TOP_N}/30d vol >=${LIQ_USD/1e6:.0f}M; "
                          f"n_long_oos={len(ol)} long_net={row['long_net']:.1f} hedge_net={row['hedge_net']:.1f} "
                          f"mtm_net={row['mtm_net']:.1f} avg_univ={diag['avg_univ']:.1f} avg_long={diag['avg_long']:.1f} "
                          f"avg_beta={diag['avg_beta']:.2f} maker_fill={diag['maker_fill_rate']:.2f}")
    C.record_to_lab(STRATEGY, tag + pname(p) + "_is_f1", "HL_XSEC_PIT", f"{p['rebal_d']}d", p,
                    C.evaluate(run_fn(p, *bounds[0]), 3, *PERIOD), period=bounds[0], source=src,
                    notes="fold-1 in-sample grid cell (realized)")
    C.record_to_lab(STRATEGY, tag + pname(p) + "_oos_f23", "HL_XSEC_PIT", f"{p['rebal_d']}d", p, o,
                    period=(bounds[1][0], bounds[2][1]), source=src,
                    notes=f"folds 2+3 realized (grid transparency, NOT selected unless flagged); selected={p == best}; "
                          f"t={tst:.2f} n_dec={n_dec} ex_top3={conc['ex_top3']:.1f}")
    return row


def select_on(grid, bounds_sel, min_trades=10):
    rows = []
    for i, p in enumerate(grid):
        r = C.evaluate(run_fn(p, *bounds_sel), 1)
        rows.append(dict(idx=i, n=r["n"], net=r["net"], pf=r["pf"]))
    t = pd.DataFrame(rows)
    elig = t[t["n"] >= min_trades]
    pick = (elig if len(elig) else t).sort_values("net", ascending=False).iloc[0]
    return grid[int(pick["idx"])], t


# ---------------------------------------------------------------------------
def main():
    src = Path(__file__).name
    bounds = C.fold_bounds(PERIOD, 3)
    n_univ = MASK.sum(axis=1)
    print("period", PERIOD, "folds", [(s.date(), e.date()) for s, e in bounds])
    print(f"panel: {len(COINS)} coins; PIT universe/day min={n_univ.min()} mean={n_univ.mean():.1f} max={n_univ.max()}")
    ever = [COINS[j] for j in np.where(MASK.any(axis=0))[0]]
    no_fund = [c for c in ever if c not in P["fund_coins"]]
    print(f"coins ever eligible: {len(ever)}; without funding history: {no_fund}")
    fl_days = C.fold_labels(pd.Series(DAY_OPENS), 3, *PERIOD)
    univ_by_fold = [float(n_univ[fl_days == kf].mean()) for kf in range(3)]
    print("universe size by fold:", np.round(univ_by_fold, 1))

    # --- walk-forward (select on fold 1) --------------------------------------
    t0 = time.time()
    best, oos_tr, table = C.walk_forward(GRID, run_fn, PERIOD, n_folds=3, min_trades=10)
    oos = C.oos_result(oos_tr, PERIOD, 3)
    oos_long = C.oos_result(oos_tr[oos_tr["leg"] == "long"], PERIOD, 3)
    oos_hedge = C.oos_result(oos_tr[oos_tr["leg"] == "hedge"], PERIOD, 3)
    oos_mtm = C.oos_result(oos_frame(best, bounds, mtm=True), PERIOD, 3)
    print(f"\nBEST (fold-1 selected): {best}  [{time.time()-t0:.0f}s]")
    print("OOS realized book  :", fmt(oos))
    print("OOS realized longs :", fmt(oos_long))
    print("OOS realized hedge :", fmt(oos_hedge))
    print("OOS MTM book       :", fmt(oos_mtm))

    grid = pd.DataFrame([grid_row(i, p, best, bounds, src) for i, p in enumerate(GRID)])
    pd.set_option("display.width", 320)
    print("\nIN-SAMPLE (fold 1) GRID + folds 2/3 (combo, alt-hedged, taker, rank exit):")
    print(grid.drop(columns=["idx"]).round(2).to_string(index=False))
    C.record_to_lab(STRATEGY, "WF_OOS_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d", best, oos,
                    period=(bounds[1][0], bounds[2][1]), source=src,
                    notes=f"HEADLINE walk-forward OOS folds 2+3 REALIZED-only, selected on fold 1; long n={oos_long['n']} "
                          f"long_net={oos_long['net']:.1f} hedge_net={oos_hedge['net']:.1f} mtm_net={oos_mtm['net']:.1f}")
    C.record_to_lab(STRATEGY, "WF_OOS_MTM_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d", best, oos_mtm,
                    period=(bounds[1][0], bounds[2][1]), source=src, notes="walk-forward OOS incl. end-of-sample marks")

    # --- rolling walk-forward: select on fold 2, test fold 3 --------------------
    best2, sel2 = select_on(GRID, bounds[1])
    roll_tr = run_fn(best2, *bounds[2])
    roll = C.oos_result(roll_tr, PERIOD, 3)
    roll_long = roll_tr[roll_tr["leg"] == "long"]
    print(f"\nROLLING WF: selected on fold 2 -> {best2}; fold-3 realized: {fmt(roll)} (long n={len(roll_long)})")
    C.record_to_lab(STRATEGY, "ROLL_WF_f2sel_f3_" + pname(best2), "HL_XSEC_PIT", f"{best2['rebal_d']}d", best2, roll,
                    period=bounds[2], source=src, notes="rolling walk-forward: selected on fold 2, tested on fold 3 (realized)")

    # --- arms at the selected structure ----------------------------------------
    arm_defs = {
        "hedge_btc": dict(best, hedge="btc"), "hedge_none": dict(best, hedge="none"),
        "exec_maker": dict(best, exec="maker_fb"), "exit_stop25": dict(best, exit="stop"),
        "exit_maxhold14": dict(best, exit="maxhold"), "signal_fund": dict(best, signal="fund"),
        "signal_mom": dict(best, signal="mom"), "signal_rev": dict(best, signal="rev"),
    }
    arms = []
    for nm, p in arm_defs.items():
        r = grid_row(100 + len(arms), p, best, bounds, src, tag="ARM_")
        r["arm"] = nm
        arms.append(r)
    arms = pd.DataFrame(arms)
    print("\nARMS at selected structure (OOS realized):")
    print(arms[["arm", "name", "is_n", "is_net", "oos_n_long", "oos_net", "oos_pf", "f2", "f3", "oos_mtm_net", "oos_t",
                "oos_ex_top3", "hedge_net", "avg_beta", "maker_fill"]].round(2).to_string(index=False))

    # --- funding arm: its own walk-forward over the 18-cell grid ---------------
    fgrid = [dict(p, signal="fund") for p in GRID]
    fbest, f_oos_tr, _ = C.walk_forward(fgrid, run_fn, PERIOD, n_folds=3, min_trades=10)
    f_oos = C.oos_result(f_oos_tr, PERIOD, 3)
    print(f"\nFUNDING ARM own WF: best={fbest}; OOS realized: {fmt(f_oos)} long n={int((f_oos_tr['leg']=='long').sum())}")
    C.record_to_lab(STRATEGY, "WF_OOS_FUNDARM_" + pname(fbest), "HL_XSEC_PIT", f"{fbest['rebal_d']}d", fbest, f_oos,
                    period=(bounds[1][0], bounds[2][1]), source=src, notes="funding-term arm, own fold-1 selection, realized")

    # --- (a) shuffle: random bucket, N reps ------------------------------------
    t0 = time.time()
    sh = []
    for rep in range(N_SHUFFLE):
        p = dict(best, _shuffle=1, _rep=rep)
        tr, _ = build_trades(p)
        _CACHE.pop(json.dumps(p, sort_keys=True), None)
        rz = realized(tr)
        m = (rz["entry_time"] >= bounds[1][0]) & (rz["entry_time"] < bounds[2][1])
        sh.append(C.evaluate(rz[m], 1)["net"] if m.any() else 0.0)
    sh = np.array(sh)
    sh_p = float((sh >= oos["net"]).mean())
    print(f"\nSHUFFLE ({N_SHUFFLE} reps, {time.time()-t0:.0f}s): mean {sh.mean():.1f} sd {sh.std():.1f} "
          f"p95 {np.percentile(sh, 95):.1f} P(shuffle>=real)={sh_p:.3f}; real {oos['net']:.1f}")
    C.record_to_lab(STRATEGY, "SHUFFLE_" + pname(best), "HL_XSEC_PIT", f"{best['rebal_d']}d", dict(best, _shuffle=1),
                    dict(C.empty_result(), n=N_SHUFFLE, net=float(sh.mean()), folds=[0.0, 0.0, 0.0]),
                    period=(bounds[1][0], bounds[2][1]), source=src,
                    notes=f"random-bucket shuffle {N_SHUFFLE} reps OOS realized: mean={sh.mean():.1f} sd={sh.std():.1f} "
                          f"p={sh_p:.3f} real={oos['net']:.1f}")

    # --- (c) neighbours --------------------------------------------------------
    nb = []
    for p in GRID:
        diff = sum(p[kk] != best[kk] for kk in ("rebal_d", "k", "quantile"))
        if diff == 1:
            nb.append(grid[grid["name"] == pname(p)].iloc[0])
    nb = pd.DataFrame(nb)
    nb_pos = int((nb["oos_net"] > 0).sum())
    print(f"\nNEIGHBOURS: {nb_pos}/{len(nb)} positive OOS")
    print(nb[["name", "is_net", "oos_n_long", "oos_net", "oos_pf", "f2", "f3", "oos_t"]].round(2).to_string(index=False))

    # --- (d) per-coin / liquidity split / concentration / decisions -----------
    t = C.add_pnl(oos_tr)
    lg = t[t["leg"] == "long"]
    per_coin = lg.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"),
                                            funding=("funding_usd", "sum"), vol24=("vol24_entry", "median")).sort_values("net")
    liq10 = lg.groupby(lg["vol24_entry"] < 1e7)["net_pnl"].agg(["size", "sum"])
    liq5 = lg.groupby(lg["vol24_entry"] < 5e6)["net_pnl"].agg(["size", "sum"])
    liq_split10 = {("thin<10M" if kk else "liquid>=10M"): dict(n=int(v["size"]), net=round(float(v["sum"]), 1)) for kk, v in liq10.iterrows()}
    liq_split5 = {("thin<5M" if kk else "liquid>=5M"): dict(n=int(v["size"]), net=round(float(v["sum"]), 1)) for kk, v in liq5.iterrows()}
    reason_split = lg.groupby("reason")["net_pnl"].agg(["size", "sum"]).round(1).to_dict("index")
    conc = concentration(oos_tr)
    n_dec, mu, sd, tst, npos = decision_stats(oos_tr)
    n_dec_l, mu_l, sd_l, tst_l, npos_l = decision_stats(lg)
    # per-fold decision stats
    dec_f = {}
    for kf in (1, 2):
        m = (t["entry_time"] >= bounds[kf][0]) & (t["entry_time"] < bounds[kf][1])
        dec_f[f"fold{kf+1}"] = decision_stats(t[m])
    print(f"\nCONCENTRATION: {conc}")
    print(f"DECISIONS (book): n={n_dec} mean={mu:.1f} sd={sd:.1f} t={tst:.2f} pos={npos}; longs-only t={tst_l:.2f}; by fold {dec_f}")
    print(f"LIQ split: {liq_split10} | {liq_split5}\nexit reasons: {reason_split}")
    print(f"OOS funding long {lg['funding_usd'].sum():.1f}, hedge {t[t['leg']=='hedge']['funding_usd'].sum():.1f}; "
          f"fees {t['fee_usd'].sum():.1f}; delisting exits {int(lg['delist'].sum())}")
    print(per_coin.round(1).to_string())

    # open positions at sample end (what MTM adds)
    full_tr, _ = build_trades(best)
    marks = C.add_pnl(full_tr[full_tr["final_mark"]])
    marks = marks[marks["entry_time"] >= bounds[1][0]]
    print("\nEND-OF-SAMPLE MARKS (excluded from headline):")
    print(marks[["instrument", "entry_time", "entry_px", "exit_px", "net_pnl"]].round(2).to_string(index=False))

    # --- (e) anchor phases ------------------------------------------------------
    phase_rows = []
    for R in sorted({best["rebal_d"], 7}):
        for ph in range(R):
            p = dict(best, rebal_d=R, _phase=ph)
            o_tr = oos_frame(p, bounds)
            o = C.oos_result(o_tr, PERIOD, 3)
            _, _, _, tp, _ = decision_stats(o_tr)
            cp = concentration(o_tr)
            phase_rows.append(dict(R=R, phase=ph, oos_n_long=int((o_tr["leg"] == "long").sum()), oos_net=o["net"],
                                   oos_pf=o["pf"], f2=o["folds"][1], f3=o["folds"][2], t=tp, ex_top3=cp["ex_top3"]))
            C.record_to_lab(STRATEGY, f"PHASE_R{R}_p{ph}_" + pname(best), "HL_XSEC_PIT", f"{R}d", p, o,
                            period=(bounds[1][0], bounds[2][1]), source=src, notes=f"anchor phase {ph} of {R}; realized OOS")
    phase_df = pd.DataFrame(phase_rows)
    print("\nANCHOR PHASES (OOS realized):")
    print(phase_df.round(2).to_string(index=False))
    ph_sel = phase_df[phase_df["R"] == best["rebal_d"]]
    ph7 = phase_df[phase_df["R"] == 7]

    # --- criteria / verdict ------------------------------------------------------
    n_long_oos = int(oos_long["n"])
    crit = dict(
        net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=n_long_oos >= 60,
        folds=all(f > 0 for f in oos["folds"][1:]), shuffle=sh_p < 0.05,
        neighbors=nb_pos >= max(1, int(np.ceil(0.75 * len(nb)))),
        ex_top3=conc["ex_top3"] > 0, t_dec=tst >= 2.0,
        phases=bool((ph_sel["oos_net"] > 0).all()),
        rolling=roll["net"] > 0,
    )
    core = ["net_pos", "pf", "n", "folds", "shuffle", "neighbors", "ex_top3", "t_dec"]
    if all(crit[c] for c in core):
        verdict = "edge"
    elif crit["net_pos"]:
        verdict = "weak"
    else:
        verdict = "none"
    print("\nCRITERIA:", crit, "\nVERDICT:", verdict)

    # --- markdown ------------------------------------------------------------------
    md = [f"# {STRATEGY} - wide-book z(30d)-z(kd) long book, beta-scaled liquid-alt basket hedge (round 3)\n",
          f"Data: {len(COINS)} HL perps (PIT incl. delisted) 1h+1d, {PERIOD[0].date()} -> {PERIOD[1].date()}. "
          f"Folds: {[(str(s.date()), str(e.date())) for s, e in bounds]}.\n",
          f"Universe (PIT at each 23:00 signal): 24h USD vol >= ${LIQ_USD/1e6:.0f}M, top-{TOP_N} by 30d USD vol, >= 31 daily closes. "
          f"Size/day min {n_univ.min()}, mean {n_univ.mean():.1f}, max {n_univ.max()}; by fold {np.round(univ_by_fold,1).tolist()}; "
          f"{len(ever)} coins ever eligible; no-funding coins: {no_fund}.\n",
          "Execution: score at the 23:00 close (daily candle D-1); long top-q, $1000/name, fill at the 00:00 1h bar open, taker "
          "4.5 bps/side (headline). Hedge: short beta-scaled (30d, clipped 0.3-2.0) equal-weight basket of the top-20 liquid alts "
          "(ex-book, ex-BTC/PAXG), resized each rebalance, fees on adjustments only, funding accrued on notional, aggregated into one "
          "row per interval (instrument ALTBASKET). Hourly funding folded into exit_px. HEADLINE = REALIZED-only: positions still "
          "open at sample end are excluded (MTM shown separately). n = long-leg trades (hedge rows excluded from n).\n",
          f"## Headline (walk-forward OOS, folds 2+3, realized only)\n\nSelected on fold 1: `{best}`\n\n"
          f"| leg | n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |\n|---|---|---|---|---|---|---|---|---|---|\n"
          f"| book (long+hedge) | {oos['n']} | {oos['net']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | {oos['sharpe']:.2f} | {oos['max_dd']:.1f} | {oos['net_bps']:.1f} | {oos['folds'][1]:.2f} | {oos['folds'][2]:.2f} |\n"
          f"| long leg | {oos_long['n']} | {oos_long['net']:.2f} | {oos_long['pf']:.2f} | {oos_long['wr']:.2f} | {oos_long['sharpe']:.2f} | {oos_long['max_dd']:.1f} | {oos_long['net_bps']:.1f} | {oos_long['folds'][1]:.2f} | {oos_long['folds'][2]:.2f} |\n"
          f"| hedge leg | {oos_hedge['n']} | {oos_hedge['net']:.2f} | {oos_hedge['pf']:.2f} | {oos_hedge['wr']:.2f} | {oos_hedge['sharpe']:.2f} | {oos_hedge['max_dd']:.1f} | {oos_hedge['net_bps']:.1f} | {oos_hedge['folds'][1]:.2f} | {oos_hedge['folds'][2]:.2f} |\n"
          f"| book MTM (incl. end marks) | {oos_mtm['n']} | {oos_mtm['net']:.2f} | {oos_mtm['pf']:.2f} | {oos_mtm['wr']:.2f} | {oos_mtm['sharpe']:.2f} | {oos_mtm['max_dd']:.1f} | {oos_mtm['net_bps']:.1f} | {oos_mtm['folds'][1]:.2f} | {oos_mtm['folds'][2]:.2f} |\n",
          f"Rolling walk-forward (select on fold 2 -> test fold 3): selected `{best2}`; fold-3 realized n_long={len(roll_long)} "
          f"net={roll['net']:.2f} pf={roll['pf']:.2f}.\n",
          f"Fold-3 alt-basket-hedged net (headline params): {oos['folds'][2]:.2f} (long {oos_long['folds'][2]:.2f}, hedge {oos_hedge['folds'][2]:.2f}).\n",
          "## In-sample grid (fold 1) with OOS folds 2/3 (all cells alt-hedged, taker, rank exit)\n",
          md_table(grid.drop(columns=["idx"]).round(2)) + "\n",
          "## Arms at the selected structure\n",
          md_table(arms[["arm", "name", "is_n", "is_net", "oos_n_long", "oos_net", "oos_pf", "f2", "f3", "oos_mtm_net", "oos_t",
                         "oos_ex_top3", "long_net", "hedge_net", "avg_beta", "maker_fill"]].round(2)) + "\n",
          f"Funding arm with its own fold-1 selection: `{fbest}` -> OOS realized n={f_oos['n']} net={f_oos['net']:.2f} "
          f"pf={f_oos['pf']:.2f} folds={np.round(f_oos['folds'],1).tolist()}.\n",
          "## Sanity checks\n",
          f"- (a) Shuffle (random long bucket, {N_SHUFFLE} reps, OOS realized, same hedge): mean {sh.mean():.1f}, sd {sh.std():.1f}, "
          f"p95 {np.percentile(sh,95):.1f}, P(shuffle >= real) = {sh_p:.3f}; real = {oos['net']:.1f}.\n"
          f"- (b) OOS folds: fold2 {oos['folds'][1]:.2f}, fold3 {oos['folds'][2]:.2f}; MTM fold2 {oos_mtm['folds'][1]:.2f}, fold3 {oos_mtm['folds'][2]:.2f}.\n"
          f"- (c) Neighbours of best (one param changed): {nb_pos}/{len(nb)} positive OOS net.\n\n"
          + md_table(nb[["name", "is_net", "oos_n_long", "oos_net", "oos_pf", "f2", "f3", "oos_t", "oos_ex_top3"]].round(2)) + "\n",
          f"- (d) Liquidity split (long leg, 24h USD vol at entry): {liq_split10}; {liq_split5}\n"
          f"- Exit reasons: {reason_split}\n"
          f"- Concentration: {conc}\n"
          f"- Per-decision book PnL: n={n_dec} decisions, mean {mu:.1f}, sd {sd:.1f}, t={tst:.2f}, positive {npos}/{n_dec}; "
          f"long-leg only t={tst_l:.2f}; by fold (n, mean, sd, t, pos): {dec_f}\n"
          f"- OOS funding long {lg['funding_usd'].sum():.1f} / hedge {t[t['leg']=='hedge']['funding_usd'].sum():.1f}; fees {t['fee_usd'].sum():.1f}; "
          f"delisting exits {int(lg['delist'].sum())}\n\n"
          "Per-coin OOS (long leg):\n\n" + md_table(per_coin.round(1), index=True) + "\n",
          "End-of-sample marks excluded from the headline:\n\n" + md_table(marks[["instrument", "entry_time", "entry_px", "exit_px", "net_pnl"]].round(2)) + "\n",
          f"- (e) Anchor phases (OOS realized), selected R={best['rebal_d']} and R=7:\n\n" + md_table(phase_df.round(2)) + "\n",
          f"## Criteria\n\n`{crit}`\n\n## Verdict: **{verdict}**\n"]
    OUT_MD.write_text("\n".join(md))
    print("wrote", OUT_MD)

    result = dict(best=best, oos=oos, oos_long=oos_long, oos_hedge=oos_hedge, oos_mtm=oos_mtm, best2=best2, roll=roll,
                  roll_n_long=int(len(roll_long)), sh_p=sh_p, sh_mean=float(sh.mean()), sh_sd=float(sh.std()),
                  nb_pos=nb_pos, nb_n=len(nb), verdict=verdict, crit={k: bool(v) for k, v in crit.items()},
                  is_best_net=float(grid[grid["selected"]]["is_net"].iloc[0]), conc=conc,
                  decisions=dict(n=n_dec, mean=mu, sd=sd, t=tst, pos=npos, t_long=tst_l, by_fold=dec_f),
                  liq_split10=liq_split10, liq_split5=liq_split5, reason_split=reason_split,
                  grid=grid.to_dict("records"), arms=arms.to_dict("records"), phases=phase_df.to_dict("records"),
                  fund_arm=dict(best=fbest, oos=f_oos), univ_by_fold=univ_by_fold,
                  marks=marks[["instrument", "entry_time", "net_pnl"]].to_dict("records"))
    OUT_JSON.write_text(json.dumps(result, default=str, indent=1))
    return result


if __name__ == "__main__":
    main()
