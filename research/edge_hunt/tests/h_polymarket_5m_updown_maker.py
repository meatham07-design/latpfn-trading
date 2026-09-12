"""Hypothesis polymarket_5m_updown_maker: can a MAKER (resting limit bids, fee 0,
'takerOnly' fee schedule verified on Gamma) earn positive net on Polymarket BTC/ETH
5-minute (and BTC 15-minute) Up/Down markets by quoting the side priced below its
hit-rate given the concurrent Binance move-to-date, with fills counted ONLY when a
public print traded strictly through the resting price?

Data (all public, cached)
  data/polymarket/            BTC 5m: meta_* (9,199 windows Feb-12..Aug-27) + trades_* prints
  data/polymarket_eth_updown_5m/  ETH 5m, last 14 d       (fetch_polymarket_multi.py)
  data/polymarket_btc_updown_15m/ BTC 15m, last 21 d      (fetch_polymarket_multi.py)
  data/binance_1s/, data/binance_1s_ETHUSDT/  Binance spot 1s klines

Causality / execution model
  * Print timestamps are Polygon settlement times (found in h_poly_lastminute_1s):
    a print stamped t was matched at t-D, D unknown, typically 1-5 s, fat tail.
  * Quote Q(s) posted at second s uses the Binance kline with open_time s-1 (closed
    at s) and the market state (last taker-implied bid/ask) from prints stamped < s.
  * A print stamped t in window phase rel=t-ts is matched against Q(t-G)
    (the STALEST quote that could have been in force) and only counts if t < T1
    (so the quote provably still existed even if D=0).  Honest cells use G >= 6;
    G in 1..4 is reported as a contamination diagnostic only.
  * Fill (strict traded-through): our bid for token S at price P is filled by a
    taker-SELL S print at price < P, or a taker-BUY of the complement at price
    > 1-P (Polymarket's CLOB matches BUY Up vs BUY Down by minting).  Filled
    at P for min(print size, remaining order size).  Order = N shares per side.
  * Bid capped at (last implied ask - tick) so we never cross (taker) the book.
  * Fee = 0 (maker, takerOnly schedule).  Maker rebate (20% of taker fees)
    ignored.  Payoff 1/0 at resolution.

Model  p_model(s) = Phi( log(close[s-1]/strike) / (sigma[s-1]*sqrt(ts+LEN-s)) )
  strike = price_to_beat de-based by trailing-12-window Chainlink/Binance basis
  (prior windows only); sigma = trailing-2h std of {1,15,60}s returns scaled to
  1 s, chosen on fold 1 by Brier.  'cal' anchor = fold-1 binned recalibration of
  p_model by (phase, p_model) bins.  Market anchor = implied mid from prints < s.

Grid (fold-1 selection by net; OOS = folds 2+3 of the BTC-5m full span
2026-08-07 23:00 -> 2026-08-28 00:00 UTC):
  anchor in {model, cal, market, blend} x mode in {mm (two-sided), tilt (only the
  side the model says is >= X cheap vs market mid)} x X in {0.02,0.04,0.08,0.15} x
  (T0,T1) in {(0,60),(0,120),(60,120),(120,300),(200,300),(250,300)}, G=6.
  T1 = cancel time (quotes live in [T0, T1)); prints must be stamped < T1.
ETH-5m and BTC-15m: pure transfer (BTC-selected params), no fitting.

Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_polymarket_5m_updown_maker.py [--quick]
"""
from __future__ import annotations

import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

STRATEGY = "polymarket_5m_updown_maker"
SRC = "tests/h_polymarket_5m_updown_maker.py"
N_SHARES = 50.0
S0 = 0                       # quote-state grid starts at rel 0 (quotes only from T0)
FULL_START = pd.Timestamp("2026-08-07 23:00", tz="UTC")
FULL_END = pd.Timestamp("2026-08-28 00:00", tz="UTC")
G_HONEST = 6
G_CONTAM = (1, 2, 3, 4)
G_ROBUST = 10
SIGMAS = {"s1": 1, "s15": 15, "s60": 60}
PHASES = [(0, 60), (0, 120), (60, 120), (120, 300), (200, 300), (250, 300)]   # (T0, T1) in 5m-window seconds
GRID = [dict(anchor=a, mode=md, X=x, T0=t0, T1=t1, G=G_HONEST)
        for a in ("model", "cal", "market", "blend") for md in ("mm", "tilt")
        for x in (0.02, 0.04, 0.08, 0.15) for (t0, t1) in PHASES]
QUICK = "--quick" in sys.argv

MARKETS = {
    "POLY_BTC5M": dict(pm_dir="polymarket", b_dir="binance_1s", sym="BTCUSDT", LEN=300),
    "POLY_ETH5M": dict(pm_dir="polymarket_eth_updown_5m", b_dir="binance_1s_ETHUSDT", sym="ETHUSDT", LEN=300),
    "POLY_BTC15M": dict(pm_dir="polymarket_btc_updown_15m", b_dir="binance_1s", sym="BTCUSDT", LEN=900),
}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_meta(pm_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(C.DATA / pm_dir / "meta_*.parquet")))
    if not files:
        return pd.DataFrame()
    m = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    m = m[(m.ok == 1) & (m.trades_ok == 1) & m.up_price_final.isin([0.0, 1.0])].copy()
    m["outcome_up"] = m.up_price_final.astype(int)
    m["dt"] = pd.to_datetime(m.ts, unit="s", utc=True)
    m["tick"] = m.tick.fillna(0.001)
    return m.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def load_prints(pm_dir: str, ts_keep: set, LEN: int) -> pd.DataFrame:
    parts = []
    for p in sorted(glob.glob(str(C.DATA / pm_dir / "trades_*.parquet"))):
        t = pd.read_parquet(p)
        t = t[t.ts.isin(ts_keep)]
        t["rel"] = (t.t - t.ts).astype("int32")
        t = t[(t.rel >= 0) & (t.rel < LEN + 120)]   # keep post-window prints only for diagnostics
        parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    t["price"] = t.price.astype(float)
    t["size"] = t["size"].astype(float)
    t["u"] = np.where(t.up == 1, t.price, 1.0 - t.price)
    t["buy"] = t.buy.astype(bool); t["up"] = t.up.astype(bool)
    return t.sort_values(["ts", "t"], kind="stable").reset_index(drop=True)


def load_binance(b_dir: str, sym: str, days=None) -> pd.DataFrame:
    files = sorted(glob.glob(str(C.DATA / b_dir / f"{sym}-1s-*.parquet")))
    if days is not None:
        files = [f for f in files if f.split("-1s-")[1][:10] in days]
    b = pd.concat([pd.read_parquet(f)[["open", "close"]] for f in files]).sort_index()
    b = b[~b.index.duplicated()]
    lc = np.log(b.close)
    for name, k in SIGMAS.items():
        b[name] = lc.diff(k).rolling(7200, min_periods=1800).std() / np.sqrt(k)
    b["sec"] = (b.index.tz_convert("UTC").as_unit("ns").asi8 // 1_000_000_000).astype("int64")
    return b


def make_lookup(b: pd.DataFrame):
    sec = b.sec.values

    def lookup(times, arr):
        pos = np.clip(np.searchsorted(sec, times), 0, len(sec) - 1)
        ok = sec[pos] == times
        out = np.full(len(times), np.nan); out[ok] = arr[pos[ok]]
        return out
    return lookup


def add_strikes(meta: pd.DataFrame, b: pd.DataFrame, LEN: int) -> pd.DataFrame:
    lk = make_lookup(b)
    m = meta.copy()
    m["b_open"] = lk(m.ts.values, b.open.values)
    m["basis0"] = np.log(m.price_to_beat / m.b_open)
    tb = []; ts_arr = m.ts.values; bs = m.basis0.values
    for i in range(len(m)):
        sel = [bs[j] for j in range(max(0, i - 12), i) if ts_arr[i] - ts_arr[j] <= 12 * LEN and np.isfinite(bs[j])]
        tb.append(np.mean(sel) if len(sel) >= 3 else np.nan)
    m["basis_bar"] = tb
    m["strike"] = np.where(np.isfinite(m.basis_bar) & np.isfinite(m.price_to_beat),
                           m.price_to_beat / np.exp(m.basis_bar), m.b_open)
    return m


# ---------------------------------------------------------------------------
# per-second quote-state grid
# ---------------------------------------------------------------------------
def build_grid(meta: pd.DataFrame, prints: pd.DataFrame, b: pd.DataFrame, LEN: int) -> pd.DataFrame:
    """One row per (window, second s in [S0, LEN)).  Columns: ts, s(rel), pm_<sigma>,
    bid_up, ask_up (implied from prints stamped < s), outcome, tick."""
    n = len(meta); rels = np.arange(S0, LEN)
    ts = np.repeat(meta.ts.values, len(rels)); rel = np.tile(rels, n)
    g = pd.DataFrame(dict(ts=ts, rel=rel))
    g["t"] = g.ts + g.rel
    lk = make_lookup(b)
    tm = g.t.values - 1                       # kline open s-1, closed at s
    close = lk(tm, b.close.values)
    strike = np.repeat(meta.strike.values, len(rels))
    remaining = (g.ts.values + LEN) - g.t.values
    sq = np.sqrt(np.maximum(remaining, 1))
    x = np.log(close / strike)
    for sname in SIGMAS:
        sg = lk(tm, b[sname].values)
        g[f"pm_{sname}"] = norm.cdf(x / (sg * sq)).astype("float32")
    # implied touch from prints stamped strictly before s: shift by using t <= s-1
    p = prints[prints.rel < LEN + 60]
    is_ask = (p.up & p.buy) | (~p.up & ~p.buy)
    ask_u = np.where(is_ask, p.u, np.nan)
    bid_u = np.where(~is_ask, p.u, np.nan)
    st = pd.DataFrame(dict(ts=p.ts.values, t=p.t.values + 1, ask=ask_u, bid=bid_u))  # visible from second t+1
    st = st.groupby(["ts", "t"]).agg(ask=("ask", "last"), bid=("bid", "last")).reset_index()
    g = g.merge(st, on=["ts", "t"], how="left")
    g[["ask", "bid"]] = g.groupby("ts")[["ask", "bid"]].ffill()
    g["mid"] = np.where(g.ask.notna() & g.bid.notna(), (g.ask + g.bid) / 2, g.ask.fillna(g.bid))
    g["outcome_up"] = np.repeat(meta.outcome_up.values, len(rels)).astype(np.int8)
    g["tick"] = np.repeat(meta.tick.values, len(rels)).astype("float32")
    g["key"] = g.ts.values.astype("int64") * 4096 + g.rel.values.astype("int64")
    return g.sort_values("key").reset_index(drop=True)


def brier_select(grid: pd.DataFrame, f1_end: pd.Timestamp, LEN: int) -> str:
    q = grid[(grid.ts < f1_end.timestamp()) & (grid.rel.isin([LEN - 180, LEN - 100, LEN - 50]))]
    out = {}
    for sname in SIGMAS:
        pm = q[f"pm_{sname}"].values.astype(float); ok = np.isfinite(pm)
        out[sname] = float(np.mean((pm[ok] - q.outcome_up.values[ok]) ** 2))
    mk = q.mid.values.astype(float); ok = np.isfinite(mk)
    out["market"] = float(np.mean((mk[ok] - q.outcome_up.values[ok]) ** 2))
    print("[brier fold1]", {k: round(v, 4) for k, v in out.items()})
    return min((k for k in SIGMAS), key=lambda k: out[k]), out


def calib_table(grid: pd.DataFrame, f1_end: pd.Timestamp, pm_col: str, LEN: int):
    """Fold-1 empirical hit rate by (phase bucket, p_model bin).  Returns fn(pm, rel)->p_cal."""
    q = grid[(grid.ts < f1_end.timestamp()) & np.isfinite(grid[pm_col])]
    pb = np.clip((q[pm_col].values * 20).astype(int), 0, 19)
    ph = np.minimum(q.rel.values * 6 // LEN, 5)
    tab = pd.DataFrame(dict(pb=pb, ph=ph, y=q.outcome_up.values)).groupby(["ph", "pb"]).y.agg(["mean", "size"])
    arr = np.full((6, 20), np.nan); cnt = np.zeros((6, 20))
    for (h, k), r in tab.iterrows():
        arr[h, k] = r["mean"]; cnt[h, k] = r["size"]
    # shrink sparse cells toward the bin centre
    centre = (np.arange(20) + 0.5) / 20
    w = cnt / (cnt + 2000.0)
    arr = np.where(np.isfinite(arr), w * np.nan_to_num(arr) + (1 - w) * centre[None, :], centre[None, :])

    def fn(pm, rel):
        pb_ = np.clip((np.nan_to_num(pm, nan=0.5) * 20).astype(int), 0, 19)
        ph_ = np.minimum(rel * 6 // LEN, 5)
        out = arr[ph_, pb_]
        out[~np.isfinite(pm)] = np.nan
        return out
    return fn, arr, cnt


# ---------------------------------------------------------------------------
# strategy
# ---------------------------------------------------------------------------
def quotes(grid: pd.DataFrame, params: dict, pm_col: str, cal_fn):
    """Return (bid_up, bid_dn) arrays aligned to grid rows (NaN = no quote)."""
    pm = grid[pm_col].values.astype(float)
    mid = grid.mid.values.astype(float)
    a = params["anchor"]
    if a == "model":
        anc = pm
    elif a == "cal":
        anc = cal_fn(pm, grid.rel.values)
    elif a == "market":
        anc = mid
    else:
        anc = 0.5 * (pm + mid)
    X = params["X"]
    tick = grid.tick.values.astype(float)
    bid_up = anc - X
    bid_dn = (1.0 - anc) - X
    if params["mode"] == "tilt":
        cheap_up = pm - mid >= X
        cheap_dn = mid - pm >= X
        bid_up = np.where(cheap_up, bid_up, np.nan)
        bid_dn = np.where(cheap_dn, bid_dn, np.nan)
    # never cross the last implied ask; round down to tick; keep inside (0.01, 0.99)
    ask_up = grid.ask.values.astype(float); bid_up_mkt = grid.bid.values.astype(float)
    ask_dn = 1.0 - bid_up_mkt                     # implied ask for Down = 1 - bid_up
    bid_up = np.where(np.isfinite(ask_up), np.minimum(bid_up, ask_up - tick), bid_up)
    bid_dn = np.where(np.isfinite(ask_dn), np.minimum(bid_dn, ask_dn - tick), bid_dn)
    bid_up = np.floor(bid_up / tick + 1e-9) * tick
    bid_dn = np.floor(bid_dn / tick + 1e-9) * tick
    active = grid.rel.values >= params["T0"]
    bid_up = np.where(active & (bid_up >= 0.01) & (bid_up <= 0.99), bid_up, np.nan)
    bid_dn = np.where(active & (bid_dn >= 0.01) & (bid_dn <= 0.99), bid_dn, np.nan)
    return bid_up, bid_dn


def build_trades(grid: pd.DataFrame, prints: pd.DataFrame, meta: pd.DataFrame, params: dict, pm_col: str,
                 cal_fn, LEN: int, instrument: str, G: int | None = None, T1: int | None = None,
                 n_shares: float = N_SHARES) -> pd.DataFrame:
    G = params["G"] if G is None else G
    T1 = int(params.get("T1", LEN)) if T1 is None else T1
    bid_up, bid_dn = quotes(grid, params, pm_col, cal_fn)
    keys = grid.key.values
    p = prints[(prints.rel - G >= params["T0"]) & (prints.rel < T1)]
    pk = p.ts.values.astype("int64") * 4096 + (p.rel.values.astype("int64") - G)
    pos = np.searchsorted(keys, pk); pos = np.clip(pos, 0, len(keys) - 1)
    ok = keys[pos] == pk
    bu = np.where(ok, bid_up[pos], np.nan); bd = np.where(ok, bid_dn[pos], np.nan)
    price = p.price.values; up = p.up.values; buy = p.buy.values
    fill_up = np.isfinite(bu) & (((up) & (~buy) & (price < bu)) | ((~up) & (buy) & (price > 1.0 - bu)))
    fill_dn = np.isfinite(bd) & (((~up) & (~buy) & (price < bd)) | ((up) & (buy) & (price > 1.0 - bd)))
    sel = fill_up | fill_dn
    if not sel.any():
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    f = pd.DataFrame(dict(ts=p.ts.values[sel], t=p.t.values[sel], rel=p.rel.values[sel],
                          size=p["size"].values[sel], side_up=fill_up[sel],
                          px=np.where(fill_up[sel], bu[sel], bd[sel])))
    f = f.sort_values(["ts", "side_up", "t"], kind="stable")
    cum = f.groupby(["ts", "side_up"])["size"].cumsum()
    f["fill"] = np.clip(cum, 0, n_shares) - np.clip(cum - f["size"], 0, n_shares)
    f = f[f.fill > 0]
    f["cost"] = f.fill * f.px
    out = meta.set_index("ts").outcome_up
    f["pay"] = f.fill * np.where(f.side_up == (out.reindex(f.ts).values == 1), 1.0, 0.0)
    agg = f.groupby("ts").agg(cost=("cost", "sum"), pay=("pay", "sum"), shares=("fill", "sum"),
                              first_t=("t", "min"), n_fills=("fill", "size"),
                              up_sh=("fill", lambda x: 0.0))
    su = f[f.side_up].groupby("ts").fill.sum(); sd = f[~f.side_up].groupby("ts").fill.sum()
    agg["up_sh"] = su.reindex(agg.index).fillna(0.0); agg["dn_sh"] = sd.reindex(agg.index).fillna(0.0)
    agg = agg.reset_index()
    tr = pd.DataFrame(dict(entry_time=pd.to_datetime(agg.first_t, unit="s", utc=True),
                           exit_time=pd.to_datetime(agg.ts + LEN, unit="s", utc=True),
                           side=1.0, entry_px=agg.cost, exit_px=agg.pay, qty=1.0, notional_usd=agg.cost,
                           fee_usd=0.0, instrument=instrument, multiplier=1.0, ts=agg.ts,
                           shares=agg.shares, up_sh=agg.up_sh, dn_sh=agg.dn_sh, n_fills=agg.n_fills))
    return tr


def make_run_fn(grid, prints, meta, pm_col, cal_fn, LEN, instrument, **kw):
    def run_fn(params, start, end):
        tr = build_trades(grid, prints, meta, params, pm_col, cal_fn, LEN, instrument, **kw)
        if len(tr) == 0:
            return tr
        return tr[(tr.entry_time >= start) & (tr.entry_time < end)].reset_index(drop=True)
    return run_fn


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} gross={r['gross']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.3f} "
            f"sharpe={r['sharpe']:.2f} net_bps={r['net_bps']:.0f} folds={[round(f, 1) for f in r['folds']]} fold_n={r['fold_n']}")


def slim(r):
    return {k: r[k] for k in ("n", "net", "gross", "fees", "pf", "wr", "sharpe", "net_bps", "folds", "fold_n")}


# ---------------------------------------------------------------------------
# calibration curves
# ---------------------------------------------------------------------------
def calibration(grid: pd.DataFrame, pm_col: str, LEN: int, mask=None) -> pd.DataFrame:
    q = grid if mask is None else grid[mask]
    rows = []
    for rel in (LEN - 180, LEN - 100, LEN - 50, LEN - 20):
        s = q[q.rel == rel]
        for name, col in (("market_mid", "mid"), ("model", pm_col)):
            v = s[col].values.astype(float); y = s.outcome_up.values; ok = np.isfinite(v)
            b = np.clip((v[ok] * 10).astype(int), 0, 9)
            for k in range(10):
                mk = b == k
                if mk.sum() >= 20:
                    rows.append(dict(rel=rel, src=name, bin=f"{k/10:.1f}-{(k+1)/10:.1f}", n=int(mk.sum()),
                                     mean_p=float(v[ok][mk].mean()), hit=float(y[ok][mk].mean())))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def prepare(instrument: str, start: pd.Timestamp, end: pd.Timestamp, quick=False):
    cfg = MARKETS[instrument]; LEN = cfg["LEN"]
    meta = load_meta(cfg["pm_dir"])
    if len(meta) == 0:
        return None
    meta = meta[(meta.dt >= start) & (meta.dt < end)]
    if quick:
        meta = meta.iloc[::4]
    days = set(pd.to_datetime(meta.ts, unit="s", utc=True).dt.strftime("%Y-%m-%d")) | \
        set((pd.to_datetime(meta.ts, unit="s", utc=True) - pd.Timedelta(hours=3)).dt.strftime("%Y-%m-%d"))
    b = load_binance(cfg["b_dir"], cfg["sym"], days)
    meta = add_strikes(meta, b, LEN)
    meta = meta[np.isfinite(meta.strike)].reset_index(drop=True)
    prints = load_prints(cfg["pm_dir"], set(meta.ts), LEN)
    t0 = time.time()
    grid = build_grid(meta, prints, b, LEN)
    print(f"[{instrument}] windows={len(meta)} prints={len(prints)} grid={len(grid)} ({time.time()-t0:.0f}s)")
    return dict(meta=meta, prints=prints, b=b, grid=grid, LEN=LEN)


def main():
    t_all = time.time()
    results = {"strategy": STRATEGY, "fee_schedule": "takerOnly rate 0.07 exp 1 rebate 0.2 -> maker fee 0",
               "n_shares_per_side": N_SHARES}
    times = (FULL_START, FULL_END)
    bounds = C.fold_bounds(times, 3)
    f1_end = bounds[0][1]
    inst = "POLY_BTC5M"
    D = prepare(inst, FULL_START, FULL_END, QUICK)
    grid, prints, meta, LEN = D["grid"], D["prints"], D["meta"], D["LEN"]
    # print-side semantics check: taker-BUY prints of a token should sit above taker-SELL prints in the same second
    pp = prints[prints.rel < LEN]
    per = pp.groupby(["ts", "t", "up", "buy"]).price.mean().unstack("buy")
    per = per.dropna()
    spread = (per[True] - per[False])
    print(f"[print semantics] same-second same-token BUY - SELL price: mean={spread.mean():+.4f} "
          f"median={spread.median():+.4f} share>0={(spread > 0).mean():.3f} n={len(spread)}")
    results["print_semantics"] = dict(mean=float(spread.mean()), median=float(spread.median()),
                                      share_pos=float((spread > 0).mean()), n=int(len(spread)))
    sname, briers = brier_select(grid, f1_end, LEN)
    pm_col = f"pm_{sname}"
    results["sigma_selected_fold1"] = sname; results["brier_fold1"] = briers
    cal_fn, cal_arr, cal_cnt = calib_table(grid, f1_end, pm_col, LEN)

    # calibration curves (full span; OOS part reported separately)
    cal_full = calibration(grid, pm_col, LEN)
    cal_oos = calibration(grid, pm_col, LEN, mask=grid.ts >= f1_end.timestamp())
    results["calibration_oos"] = cal_oos.to_dict("records")
    print("\n[calibration OOS (folds 2+3)]")
    print(cal_oos.pivot_table(index=["rel", "bin"], columns="src", values=["n", "mean_p", "hit"]).round(3).to_string())

    run_fn = make_run_fn(grid, prints, meta, pm_col, cal_fn, LEN, inst)
    grid_ = GRID if not QUICK else GRID[::16]
    best, oos, table = C.walk_forward(grid_, run_fn, times, n_folds=3, select_by="net", min_trades=30, verbose=False)
    print("\n[in-sample fold 1 grid]")
    print(table.sort_values("is_net", ascending=False)[["params", "is_n", "is_net", "is_pf", "is_wr"]].to_string(index=False))
    res_oos = C.oos_result(oos, times, 3)
    print("\n[HEADLINE OOS folds 2+3]", best, fmt(res_oos))
    results["best_params"] = best; results["oos"] = slim(res_oos)
    results["insample_table"] = table.to_dict("records")
    period = (bounds[1][0], bounds[2][1])
    for _, row in table.iterrows():
        p = json.loads(row["params"])
        r = C.evaluate(run_fn(p, bounds[0][0], bounds[0][1]), n_folds=1)
        C.record_to_lab(STRATEGY, "is_f1_" + "_".join(f"{k}{v}" for k, v in p.items()), inst, "1s", p, r,
                        period=(bounds[0][0], bounds[0][1]), source=SRC, notes="fold-1 in-sample grid cell (maker, fee 0)")
    C.record_to_lab(STRATEGY, "wf_oos", inst, "1s", best, res_oos, period=period, source=SRC,
                    notes="HEADLINE walk-forward OOS folds 2+3, fold-1 selected params, maker fee 0, strict traded-through fills")

    # OOS of every honest cell (neighbours)
    neigh = []
    for _, row in table.iterrows():
        p = json.loads(row["params"])
        parts = [run_fn(p, s, e) for (s, e) in bounds[1:]]
        tr = pd.concat([x for x in parts if len(x)], ignore_index=True) if any(len(x) for x in parts) else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        r = C.oos_result(tr, times, 3)
        neigh.append(dict(params=row["params"], is_net=row["is_net"], oos_n=r["n"], oos_net=r["net"], oos_pf=r["pf"],
                          oos_wr=r["wr"], f2=r["folds"][1], f3=r["folds"][2]))
        C.record_to_lab(STRATEGY, "oos_" + "_".join(f"{k}{v}" for k, v in p.items()), inst, "1s", p, r,
                        period=period, source=SRC, notes="OOS folds 2+3 of a non-selected grid cell (sensitivity only)")
    neigh = pd.DataFrame(neigh)
    print("\n[OOS of every cell — sensitivity only]")
    print(neigh.sort_values("oos_net", ascending=False).round(2).to_string(index=False))
    results["neighbours_oos"] = neigh.to_dict("records")

    # diagnostics on the selected cell
    oos_tr = oos.copy()
    if len(oos_tr):
        oos_tr = C.add_pnl(oos_tr)
        wk = oos_tr.groupby(oos_tr.entry_time.dt.tz_localize(None).dt.to_period("W")).net_pnl.agg(["sum", "size"])
        print("\n[OOS by ISO week]"); print(wk.round(2).to_string())
        results["oos_by_week"] = {str(k): [float(v["sum"]), int(v["size"])] for k, v in wk.iterrows()}
        dy = oos_tr.groupby(oos_tr.entry_time.dt.date).net_pnl.agg(["sum", "size"])
        results["oos_by_day"] = {str(k): [float(v["sum"]), int(v["size"])] for k, v in dy.iterrows()}
        print("[OOS by day]"); print(dy.round(1).T.to_string())
        top3 = oos_tr.net_pnl.nlargest(3).sum()
        results["oos_top3_removed_net"] = float(res_oos["net"] - top3)
        print(f"[top-3 removal] OOS net {res_oos['net']:.2f} -> {res_oos['net']-top3:.2f}")
        # concentration
        srt = oos_tr.net_pnl.sort_values(ascending=False)
        results["oos_top10pct_share"] = float(srt.head(max(1, len(srt) // 10)).sum() / res_oos["net"]) if res_oos["net"] != 0 else None
        hr = oos_tr.groupby(oos_tr.entry_time.dt.hour).net_pnl.agg(["sum", "size"])
        results["oos_by_hour"] = {int(k): [float(v["sum"]), int(v["size"])] for k, v in hr.iterrows()}
        print("[OOS by UTC hour]"); print(hr.round(1).T.to_string())
        fills = dict(windows_oos=int(len(oos_tr)), avg_shares=float(oos_tr.shares.mean()),
                     both_sides_share=float(((oos_tr.up_sh > 0) & (oos_tr.dn_sh > 0)).mean()),
                     avg_cost=float(oos_tr.notional_usd.mean()))
        n_oos_windows = int(((meta.dt >= bounds[1][0]) & (meta.dt < bounds[2][1])).sum())
        fills["fill_prob_per_window"] = fills["windows_oos"] / max(1, n_oos_windows)
        results["oos_fill_stats"] = fills; print("[fill stats]", fills)

    # G robustness + contamination
    gdiag = {}
    for G in (G_HONEST, G_ROBUST) + G_CONTAM:
        parts = [run_fn(dict(best, G=G), s, e) for (s, e) in bounds[1:]]
        tr = pd.concat([x for x in parts if len(x)], ignore_index=True) if any(len(x) for x in parts) else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        r = C.oos_result(tr, times, 3); gdiag[G] = slim(r)
        print(f"[G={G}] {fmt(r)}")
        C.record_to_lab(STRATEGY, f"oos_selected_G{G}", inst, "1s", dict(best, G=G), r, period=period, source=SRC,
                        trust="measured" if G >= G_HONEST else "suspect",
                        notes="OOS selected params with settlement-delay guard G" + (" (CONTAMINATED, diagnostic only)" if G < G_HONEST else ""))
    results["G_diag"] = {str(k): v for k, v in gdiag.items()}

    # shuffle: model of a random other window at the same rel (3 seeds)
    sh = []
    for seed in (1, 2, 3):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(len(meta))
        g2 = grid.copy()
        pm_mat = grid[pm_col].values.reshape(len(meta), -1)[perm].reshape(-1)
        g2[pm_col] = pm_mat
        rf2 = make_run_fn(g2, prints, meta, pm_col, cal_fn, LEN, inst)
        parts = [rf2(best, s, e) for (s, e) in bounds[1:]]
        tr = pd.concat([x for x in parts if len(x)], ignore_index=True) if any(len(x) for x in parts) else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        r = C.oos_result(tr, times, 3); sh.append(slim(r)); print(f"[shuffle seed {seed}] {fmt(r)}")
        C.record_to_lab(STRATEGY, f"shuffle_seed{seed}", inst, "1s", best, r, period=period, source=SRC,
                        notes="model permuted across windows (same rel), selected params, OOS")
    results["shuffle"] = sh

    # tick/fee stress: charge the taker fee formula even though makers pay 0
    if len(oos):
        rate = 0.07
        stress = oos.copy()
        stress["fee_usd"] = stress.shares * rate * 0.25 * (stress.exit_px > 0)  # upper bound p(1-p)<=0.25 in outcome token
        r = C.oos_result(stress, times, 3); results["oos_if_taker_fee"] = slim(r)
        print(f"[stress: taker fee charged anyway] {fmt(r)}")

    # stratified Feb-Jul sample with selected params
    Dst = prepare(inst, pd.Timestamp("2026-02-01", tz="UTC"), FULL_START, QUICK)
    if Dst is not None and len(Dst["meta"]):
        rf = make_run_fn(Dst["grid"], Dst["prints"], Dst["meta"], pm_col, cal_fn, LEN, inst)
        tr = rf(best, pd.Timestamp("2026-02-01", tz="UTC"), FULL_START)
        r = C.evaluate(tr, n_folds=3)
        print(f"[strat Feb-Jul sample, selected params] {fmt(r)}")
        results["strat_feb_jul"] = slim(r)
        if len(tr):
            trp = C.add_pnl(tr); mo = trp.groupby(trp.entry_time.dt.tz_localize(None).dt.to_period("M")).net_pnl.agg(["sum", "size"])
            results["strat_by_month"] = {str(k): [float(v["sum"]), int(v["size"])] for k, v in mo.iterrows()}
            print(mo.round(1).T.to_string())
        C.record_to_lab(STRATEGY, "strat_feb_jul", inst, "1s", best, r, period=("2026-02-12", FULL_START), source=SRC,
                        notes="stratified Feb-Jul sample (~450 windows/month), selected params, pure OOS")

    # transfer to ETH-5m and BTC-15m (pure OOS, BTC-selected params)
    for inst2 in ("POLY_ETH5M", "POLY_BTC15M"):
        try:
            D2 = prepare(inst2, pd.Timestamp("2026-01-01", tz="UTC"), FULL_END, QUICK)
        except Exception as e:  # noqa
            print(f"[{inst2}] skipped: {e}"); D2 = None
        if D2 is None or len(D2["meta"]) == 0:
            print(f"[{inst2}] no data"); continue
        LEN2 = D2["LEN"]
        p2 = dict(best); 
        if LEN2 != LEN:
            p2["T0"] = int(round(best["T0"] * LEN2 / LEN)); p2["T1"] = int(round(best.get("T1", LEN) * LEN2 / LEN))
        cal2, _, _ = calib_table(D2["grid"], D2["meta"].dt.min() - pd.Timedelta(seconds=1), pm_col, LEN2) if False else (cal_fn, None, None)
        rf = make_run_fn(D2["grid"], D2["prints"], D2["meta"], pm_col, cal2, LEN2, inst2)
        t_lo, t_hi = D2["meta"].dt.min(), D2["meta"].dt.max() + pd.Timedelta(seconds=LEN2)
        tr = rf(p2, t_lo, t_hi)
        r = C.evaluate(tr, n_folds=3, start=t_lo, end=t_hi)
        print(f"[{inst2} transfer, params {p2}] {fmt(r)}")
        results[f"transfer_{inst2}"] = dict(params=p2, **slim(r), windows=int(len(D2["meta"])),
                                            period=[str(t_lo), str(t_hi)])
        C.record_to_lab(STRATEGY, "transfer", inst2, "1s", p2, r, period=(t_lo, t_hi), source=SRC,
                        notes="pure transfer of BTC-5m fold-1-selected params (T0 scaled by window length)")
        cal2df = calibration(D2["grid"], pm_col, LEN2)
        results[f"calibration_{inst2}"] = cal2df.to_dict("records")

    results["runtime_s"] = time.time() - t_all
    out = ROOT / "tests" / "h_polymarket_5m_updown_maker_result.json"
    out.write_text(json.dumps(results, indent=1, default=str))
    print(f"\nwrote {out} ({results['runtime_s']:.0f}s)")


if __name__ == "__main__":
    main()
