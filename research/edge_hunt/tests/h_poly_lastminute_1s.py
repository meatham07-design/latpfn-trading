"""Hypothesis poly_lastminute_1s (round 3): is the Polymarket BTC 5-minute
Up/Down market price STALE in the last 90 seconds relative to a Binance
1-second model of P(close > open)?

Data
  * data/polymarket/meta_*.parquet  : 9,199 resolved windows (Feb-12 .. Aug-27)
  * data/polymarket/trades_*.parquet: 20.6M prints (ts, t, buy, up, price, size)
  * data/binance_1s/BTCUSDT-1s-<day>.parquet : Binance spot 1s klines (fetched
    by fetch_binance_1s.py, public archive) for every day with a sampled window.

DATA-INTEGRITY FINDING THAT SHAPES THE TEST
  Polymarket data-api print timestamps are Polygon block times (settlement),
  not match times: they sit on a ~1.5 s lattice, and 0.04% of prints (in 44%
  of windows) are stamped 3-84 s AFTER the market's own closedTime.  A print
  stamped t was matched at t - D with D unknown (block + batching, typically a
  few seconds, fat tail).  Regressing the Up-price change on Binance 1s
  returns shows the response concentrated at lags 3-4 s and exhausted by lag
  5.  Therefore a model using Binance klines closer than ~5 s before the print
  timestamp is LOOK-AHEAD relative to the actual match (and the fill it
  assumes is gone).  Honest cells use L >= 6; L in 1..5 are reported only as a
  contamination-decay diagnostic and are excluded from selection.

Model (strictly causal given the above)
  strike   S_ts: 'binance' = Binance 1s OPEN at ts, or 'ptb_adj' =
                 price_to_beat / exp(trailing-12-window mean Chainlink/Binance
                 basis, all from prior windows).  Chosen on fold 1 by Brier.
  at print time t the kline used is open_time tm = t - L (closed at tm+1).
  p_model  = Phi( log(close[tm]/S_ts) / (sigma[tm] * sqrt(ts+300-(tm+1))) )
  sigma    = trailing-2h std of k-second log returns scaled to 1 s, k in
             {1, 15, 60}.  Chosen on fold 1 by Brier (1s returns of BTC are
             positively autocorrelated, so 1s std under-states 90 s vol).

Trade rule (taker, prints-only fills)
  For a print at t with Up-equivalent price u (= price if the print is the Up
  token, else 1-price) in window phase rel = t-ts in [T0, 300):
    buy Up   at u    if an ASK for Up existed at u (taker-BUY Up print or
                     taker-SELL Down print) and u <= p_model - X
    buy Down at 1-u  if an ASK for Down existed (taker-BUY Down / taker-SELL
                     Up print) and (1-u) <= (1-p_model) - X
  First qualifying print fixes the side; later qualifying prints of that side
  add fills (each capped by its own printed size) until $50 cost per window.
  Payoff = 1 (side resolved) or 0 at ts+300.  Fee per the market's own
  feeSchedule: shares * rate * (p(1-p))^exp, taken in the outcome token, so its
  realised USD cost is that many tokens * payoff (0 or 1).

Honest grid (18): X in {0.03,0.05,0.10} x T0 in {210,240,270} x L in {6,8}.
Contamination diagnostic (5): X=0.10, T0=210, L in {1,2,3,4,5}.
Walk-forward: select on fold 1 (first ~6.3 days of the full-coverage span),
report folds 2+3.  Fourth check: same rule on the stratified Feb-Jul sample.

Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_poly_lastminute_1s.py
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

STRATEGY = "poly_lastminute_1s"
SRC = "tests/h_poly_lastminute_1s.py"
INSTR = "POLY_BTC5M"
TF = "1s"
BUDGET = 50.0
PHASE_MIN = 200          # keep prints with rel >= 200 for the trading tests
FULL_START = pd.Timestamp("2026-08-07 23:00", tz="UTC")
FULL_END = pd.Timestamp("2026-08-27 00:00", tz="UTC")   # Aug-27 1s file not yet published
L_HONEST = (6, 8)
L_CONTAM = (1, 2, 3, 4, 5)
ALL_L = tuple(sorted(set(L_HONEST + L_CONTAM)))
GRID = [dict(X=x, T0=t0, L=lag) for lag in L_HONEST for t0 in (210, 240, 270) for x in (0.03, 0.05, 0.10)]
GRID_CONTAM = [dict(X=0.10, T0=210, L=lag) for lag in L_CONTAM]
SIGMAS = {"s1": 1, "s15": 15, "s60": 60}
STRIKES = ("binance", "ptb_adj")


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_meta() -> pd.DataFrame:
    m = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(str(C.DATA / "polymarket/meta_*.parquet")))],
                  ignore_index=True)
    m = m[(m.ok == 1) & (m.trades_ok == 1) & m.up_price_final.isin([0.0, 1.0])].copy()
    m["outcome_up"] = m.up_price_final.astype(int)
    m["dt"] = pd.to_datetime(m.ts, unit="s", utc=True)
    m["closed"] = pd.to_datetime(m.closed_time, utc=True, format="ISO8601").map(lambda x: x.timestamp()).astype("int64")
    return m.sort_values("ts").reset_index(drop=True)


def load_prints(min_rel: int = -1, max_rel: int = 300) -> pd.DataFrame:
    parts = []
    for p in sorted(glob.glob(str(C.DATA / "polymarket/trades_*.parquet"))):
        t = pd.read_parquet(p)
        t["rel"] = (t.t - t.ts).astype("int32")
        t = t[(t.rel >= min_rel) & (t.rel < max_rel)]
        parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    t["price"] = t.price.astype(float)
    t["size"] = t["size"].astype(float)
    t["u"] = np.where(t.up == 1, t.price, 1.0 - t.price)
    return t


def load_binance_1s() -> pd.DataFrame:
    files = sorted(glob.glob(str(C.DATA / "binance_1s/BTCUSDT-1s-*.parquet")))
    if not files:
        raise SystemExit("no Binance 1s data; run fetch_binance_1s.py")
    b = pd.concat([pd.read_parquet(f)[["open", "close"]] for f in files]).sort_index()
    b = b[~b.index.duplicated()]
    lc = np.log(b.close)
    for name, k in SIGMAS.items():
        # trailing 2h of k-second log returns (overlapping), scaled to 1 s; positional window
        rk = lc.diff(k)
        b[name] = rk.rolling(7200, min_periods=1800).std() / np.sqrt(k)
    b["sec"] = (b.index.tz_convert("UTC").as_unit("ns").asi8 // 1_000_000_000).astype("int64")
    return b


def make_lookup(b: pd.DataFrame):
    sec = b.sec.values

    def lookup(times, arr):
        pos = np.searchsorted(sec, times)
        pos = np.clip(pos, 0, len(sec) - 1)
        ok = sec[pos] == times
        out = np.full(len(times), np.nan)
        out[ok] = arr[pos[ok]]
        return out
    return lookup


def add_strikes(meta: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """Two Binance-equivalent strikes per window, both known at ts:
    'binance' = Binance open at ts; 'ptb_adj' = price_to_beat de-based by the
    trailing mean Chainlink/Binance basis of the previous 12 windows (1 h)."""
    lk = make_lookup(b)
    m = meta.copy()
    m["b_open"] = lk(m.ts.values, b.open.values)
    m["basis0"] = np.log(m.price_to_beat / m.b_open)                  # known at ts (ptb published at start)
    # trailing basis from PRIOR windows only, requires them to be consecutive (within 1 h)
    tb = []
    ts_arr = m.ts.values; bs = m.basis0.values
    for i in range(len(m)):
        j0 = max(0, i - 12)
        sel = [bs[j] for j in range(j0, i) if ts_arr[i] - ts_arr[j] <= 3600 and np.isfinite(bs[j])]
        tb.append(np.mean(sel) if len(sel) >= 3 else np.nan)
    m["basis_bar"] = tb
    m["strike_binance"] = m.b_open
    m["strike_ptb_adj"] = np.where(np.isfinite(m.basis_bar) & np.isfinite(m.price_to_beat),
                                   m.price_to_beat / np.exp(m.basis_bar), m.b_open)
    return m


def add_model(prints: pd.DataFrame, meta: pd.DataFrame, b: pd.DataFrame, lags=ALL_L) -> pd.DataFrame:
    lk = make_lookup(b)
    p = prints.merge(meta[["ts", "outcome_up", "fee_rate", "fee_exp", "strike_binance", "strike_ptb_adj"]],
                     on="ts", how="inner")
    p["ask_up"] = ((p.up == 1) & (p.buy == 1)) | ((p.up == 0) & (p.buy == 0))
    p["ask_dn"] = ((p.up == 0) & (p.buy == 1)) | ((p.up == 1) & (p.buy == 0))
    close = b.close.values
    for L in lags:
        tm = p.t.values - L
        s = lk(tm, close)
        remaining = (p.ts.values + 300) - (tm + 1)
        sq = np.sqrt(np.maximum(remaining, 1))
        for sname in SIGMAS:
            sg = lk(tm, b[sname].values)
            for st in STRIKES:
                x = np.log(s / p[f"strike_{st}"].values)
                pm = norm.cdf(x / (sg * sq))
                pm[remaining <= 0] = np.nan
                p[f"pm_{st}_{sname}_L{L}"] = pm.astype("float32")
    return p


def fee_frac(price, rate, exp):
    return rate * (price * (1.0 - price)) ** exp


# ---------------------------------------------------------------------------
# strategy
# ---------------------------------------------------------------------------
def build_trades(p: pd.DataFrame, X: float, T0: int, pm_col: str, budget: float = BUDGET) -> pd.DataFrame:
    pm = p[pm_col].values.astype(float)
    m = (p.rel.values >= T0) & np.isfinite(pm)
    u = p.u.values
    buy_up = m & p.ask_up.values & (u <= pm - X)
    buy_dn = m & p.ask_dn.values & ((1.0 - u) <= (1.0 - pm) - X)
    sel = buy_up | buy_dn
    q = p.loc[sel, ["ts", "t", "rel", "u", "size", "fee_rate", "fee_exp", "outcome_up", pm_col]].copy()
    if len(q) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    q["side_up"] = buy_up[sel]
    q["px"] = np.where(q.side_up, q.u, 1.0 - q.u)                     # price of the token bought
    q = q.sort_values(["ts", "t"], kind="stable")
    rows = []
    for ts, g in q.groupby("ts", sort=False):
        first = g.iloc[0]
        side_up = bool(first.side_up)
        g = g[g.side_up == side_up]
        spent = 0.0; shares = 0.0; fee_tok = 0.0
        for px, sz, fr, fe in zip(g.px.values, g["size"].values, g.fee_rate.values, g.fee_exp.values):
            if spent >= budget:
                break
            take = min(sz, (budget - spent) / px)
            if take <= 0:
                continue
            spent += take * px
            shares += take
            fee_tok += take * fee_frac(px, fr, fe)
        won = int(first.outcome_up) == (1 if side_up else 0)
        rows.append(dict(entry_time=pd.Timestamp(int(first.t), unit="s", tz="UTC"),
                         exit_time=pd.Timestamp(int(ts) + 300, unit="s", tz="UTC"),
                         side=1, entry_px=spent / shares, exit_px=1.0 if won else 0.0,
                         qty=shares, notional_usd=spent, fee_usd=fee_tok * (1.0 if won else 0.0),
                         instrument=INSTR, multiplier=1.0, ts=int(ts), side_up=side_up,
                         first_rel=int(first.rel), pm_first=float(first[pm_col]),
                         fee_rate=float(first.fee_rate), n_fills=len(g)))
    return pd.DataFrame(rows)


def make_run_fn(p: pd.DataFrame, strike: str, sname: str, pm_override: str | None = None):
    def run_fn(params, start, end):
        col = pm_override or f"pm_{strike}_{sname}_L{params['L']}"
        tr = build_trades(p, params["X"], params["T0"], col)
        if len(tr) == 0:
            return tr
        return tr[(tr.entry_time >= start) & (tr.entry_time < end)].reset_index(drop=True)
    return run_fn


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} gross={r['gross']:9.2f} fees={r['fees']:7.2f} "
            f"pf={r['pf']:.2f} wr={r['wr']:.3f} sharpe={r['sharpe']:.2f} folds={[round(f, 2) for f in r['folds']]} "
            f"fold_n={r['fold_n']}")


def slim(r):
    return {k: r[k] for k in ("n", "net", "gross", "fees", "pf", "wr", "sharpe", "folds", "fold_n")}


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------
def timestamp_diagnostics(prints_raw: pd.DataFrame, meta: pd.DataFrame) -> dict:
    t = prints_raw.merge(meta[["ts", "closed"]], on="ts")
    tt = np.sort(t.t.unique()); gaps = pd.Series(np.diff(tt)).value_counts(normalize=True).head(6)
    after = t.t - t.closed
    post = after[after > 0]
    out = dict(gap_dist={int(k): float(v) for k, v in gaps.items()},
               share_after_closedTime=float((after > 0).mean()), n_after_closedTime=int((after > 0).sum()),
               windows_with_after_close=int(t.loc[after > 0, "ts"].nunique()), windows=int(t.ts.nunique()),
               after_close_lag_q={str(q): float(post.quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(post) else {},
               closed_minus_ts_q={str(q): float((meta.closed - meta.ts).quantile(q)) for q in (0.05, 0.5, 0.95)})
    print("\n[timestamps] gaps between distinct print timestamps (s, share):", out["gap_dist"])
    print(f"  closedTime - ts quantiles: {out['closed_minus_ts_q']}")
    print(f"  prints stamped AFTER closedTime: {out['n_after_closedTime']} ({out['share_after_closedTime']:.5f}) in "
          f"{out['windows_with_after_close']} of {out['windows']} windows; lag quantiles {out['after_close_lag_q']}")
    return out


def latency_regression(prints_all: pd.DataFrame, b: pd.DataFrame, rel_lo: int, rel_hi: int, tag: str):
    """Regress the 1s change of the Up last-trade price on Binance 1s log
    returns lagged 0..10 s (lag 0 = kline [t,t+1) = contemporaneous; lag k>=1 =
    kline closed at t-k+1)."""
    import statsmodels.api as sm
    q = prints_all[(prints_all.rel >= rel_lo - 12) & (prints_all.rel < rel_hi)]
    per_sec = q.groupby(["ts", "t"]).u.mean().rename("u").reset_index()
    out = []
    for ts, g in per_sec.groupby("ts"):
        idx = np.arange(ts + rel_lo - 12, ts + rel_hi)
        s = pd.Series(g.u.values, index=g.t.values).reindex(idx).ffill()
        out.append(pd.DataFrame(dict(ts=ts, t=idx, u=s.values)))
    panel = pd.concat(out, ignore_index=True)
    panel["du"] = panel.groupby("ts").u.diff()
    sec = b.sec.values; r = np.log(b.close).diff().values

    def lk(times):
        pos = np.clip(np.searchsorted(sec, times), 0, len(sec) - 1)
        ok = sec[pos] == times
        o = np.full(len(times), np.nan); o[ok] = r[pos[ok]]; return o
    cols = {f"r_l{k}": lk(panel.t.values - k) * 1e4 for k in range(0, 11)}
    dfr = pd.concat([panel[["ts", "t", "u", "du"]], pd.DataFrame(cols)], axis=1)
    dfr = dfr[(dfr.t - dfr.ts >= rel_lo) & dfr.du.notna() & (dfr.u > 0.05) & (dfr.u < 0.95)].dropna()
    Xm = sm.add_constant(dfr[[f"r_l{k}" for k in range(11)]])
    res = sm.OLS(dfr.du.values * 100, Xm).fit(cov_type="HC1")   # du in pp per bp
    coef = res.params.drop("const"); t = res.tvalues.drop("const")
    tot = coef.clip(lower=0).sum()
    print(f"\n[latency {tag}] n={len(dfr)} R2={res.rsquared:.4f}  (dUp pp per 1 bp Binance return)")
    for k in range(11):
        print(f"  lag {k:2d}: beta={coef.iloc[k]:+.4f} t={t.iloc[k]:+6.1f}  share={coef.iloc[k] / tot if tot > 0 else 0:.2f}")
    return dict(n=int(len(dfr)), r2=float(res.rsquared),
                beta={int(k): float(coef.iloc[k]) for k in range(11)},
                tstat={int(k): float(t.iloc[k]) for k in range(11)})


def brier(p: pd.DataFrame, col: str, T0: int, start, end) -> tuple[float, int]:
    q = p[(p.rel >= T0) & (p.ts >= start.timestamp()) & (p.ts < end.timestamp())]
    q = q.groupby(["ts", "t"]).agg(pm=(col, "mean"), y=("outcome_up", "first")).dropna()
    return float(((q.pm - q.y) ** 2).mean()), int(len(q))


def calibration(p: pd.DataFrame, col: str, T0: int, tag: str):
    import statsmodels.api as sm
    q = p[(p.rel >= T0) & np.isfinite(p[col])]
    q = q.groupby(["ts", "t"]).agg(u=("u", "mean"), pm=(col, "mean"), y=("outcome_up", "first")).reset_index()
    q["diff"] = q.pm - q.u
    bins = [-1, -0.2, -0.1, -0.05, -0.03, 0.03, 0.05, 0.1, 0.2, 1]
    q["b"] = pd.cut(q["diff"], bins)
    tab = q.groupby("b", observed=True).agg(n=("y", "size"), mkt=("u", "mean"), model=("pm", "mean"), realized=("y", "mean"))
    bm = float(((q.u - q.y) ** 2).mean()); bmo = float(((q.pm - q.y) ** 2).mean())
    print(f"\n[calibration {tag}] second-level prints rel>={T0}, by (model - market):  Brier market={bm:.4f} model={bmo:.4f}")
    print(tab.to_string(float_format=lambda v: f"{v:.3f}"))
    eps = 1e-3
    lm = np.log(np.clip(q.u, eps, 1 - eps) / (1 - np.clip(q.u, eps, 1 - eps)))
    lp = np.log(np.clip(q.pm, eps, 1 - eps) / (1 - np.clip(q.pm, eps, 1 - eps)))
    Xm = sm.add_constant(pd.DataFrame(dict(logit_mkt=lm, logit_model=lp)))
    res = sm.Logit(q.y.values, Xm).fit(disp=0)
    print(f"  logit(y) ~ logit_mkt {res.params['logit_mkt']:.3f} (z={res.tvalues['logit_mkt']:.1f}) "
          f"+ logit_model {res.params['logit_model']:.3f} (z={res.tvalues['logit_model']:.1f})  n={len(q)}")
    return dict(brier_market=bm, brier_model=bmo,
                tab=[dict(bin=str(i), **{k: float(v) for k, v in r.items()}) for i, r in tab.iterrows()],
                beta_mkt=float(res.params["logit_mkt"]), z_mkt=float(res.tvalues["logit_mkt"]),
                beta_model=float(res.params["logit_model"]), z_model=float(res.tvalues["logit_model"]))


# ---------------------------------------------------------------------------
def main():
    meta = load_meta()
    b = load_binance_1s()
    days = set(pd.DatetimeIndex(b.index.floor("D")).unique().date)
    meta = meta[meta.dt.dt.date.isin(days)].copy()
    meta = add_strikes(meta, b)
    print(f"windows with Binance-1s coverage: {len(meta)}  (binance 1s rows {len(b)})")
    prints_raw = load_prints(min_rel=-10_000, max_rel=100_000)
    prints_raw = prints_raw[prints_raw.ts.isin(meta.ts)]
    prints_all = prints_raw[(prints_raw.rel >= 0) & (prints_raw.rel < 300)]
    print(f"prints rel in [0,300): {len(prints_all)}")
    p = add_model(prints_all[prints_all.rel >= PHASE_MIN], meta, b)
    print(f"late prints (rel>={PHASE_MIN}) with model: {int(np.isfinite(p['pm_binance_s1_L6']).sum())} of {len(p)}")

    fs, fe = FULL_START.timestamp(), FULL_END.timestamp()
    full = p[(p.ts >= fs) & (p.ts < fe)].reset_index(drop=True)
    strat = p[p.ts < fs].reset_index(drop=True)
    print(f"full-span late prints {len(full)} windows {full.ts.nunique()} ; stratified late prints {len(strat)} windows {strat.ts.nunique()}")
    period = (FULL_START, FULL_END)
    bounds = C.fold_bounds(period, 3)
    print("folds:", [(s.strftime('%m-%d %H:%M'), e.strftime('%m-%d %H:%M')) for s, e in bounds])
    out = dict(key=STRATEGY, period=[str(FULL_START), str(FULL_END)])

    # ---------------- data-integrity diagnostics
    out["timestamps"] = timestamp_diagnostics(prints_raw[(prints_raw.ts >= fs) & (prints_raw.ts < fe)], meta)
    pa = prints_all[(prints_all.ts >= fs) & (prints_all.ts < fe)]
    out["latency_all"] = latency_regression(pa, b, 30, 300, "rel 30-300")
    out["latency_last90"] = latency_regression(pa, b, 210, 300, "rel 210-300")

    # ---------------- model choice on FOLD 1 ONLY (Brier at L=6, T0=210)
    print("\n=== model selection on fold 1 (Brier, second-level, rel>=210, L=6) ===")
    bt = {}
    for st in STRIKES:
        for sname in SIGMAS:
            col = f"pm_{st}_{sname}_L6"
            bs, n = brier(full, col, 210, *bounds[0])
            bt[f"{st}/{sname}"] = bs
            print(f"  strike={st:8s} sigma={sname:4s} Brier={bs:.4f} n={n}")
    bmk, _ = (lambda q: (float(((q.u - q.y) ** 2).mean()), len(q)))(
        full[(full.rel >= 210) & (full.ts >= bounds[0][0].timestamp()) & (full.ts < bounds[0][1].timestamp())]
        .groupby(["ts", "t"]).agg(u=("u", "mean"), y=("outcome_up", "first")))
    print(f"  (market price Brier on the same prints: {bmk:.4f})")
    best_model = min(bt, key=bt.get); strike, sname = best_model.split("/")
    print("  chosen:", best_model)
    out["model_selection"] = dict(brier=bt, market_brier=bmk, chosen=best_model)
    model_params = dict(strike=strike, sigma=sname)

    out["calib_L6_T210"] = calibration(full, f"pm_{strike}_{sname}_L6", 210, f"full span {best_model} L=6 T0=210")
    out["calib_L6_T270"] = calibration(full, f"pm_{strike}_{sname}_L6", 270, f"full span {best_model} L=6 T0=270")
    out["calib_L1_T210"] = calibration(full, f"pm_{strike}_{sname}_L1", 210, f"CONTAMINATED {best_model} L=1 T0=210")

    # ---------------- walk-forward on the honest grid
    run_fn = make_run_fn(full, strike, sname)
    rep = C.full_report(GRID, run_fn, period, n_folds=3, min_trades=10)
    best, oos, table = rep["best_params"], rep["oos"], rep["insample"]
    print("\n=== IN-SAMPLE GRID (fold 1 only; honest L>=6) ===")
    print(table[["idx", "params", "is_n", "is_net", "is_pf", "is_wr", "is_sharpe", "is_net_bps", "selected"]].to_string(index=False))
    print("\nselected:", best, model_params)
    print("HEADLINE OOS (folds 2+3):", fmt(oos))
    for _, row in table.iterrows():
        prm = json.loads(row.params)
        r1 = C.evaluate(run_fn(prm, bounds[0][0], bounds[0][1]), n_folds=1)
        C.record_to_lab(STRATEGY, f"is_X{prm['X']}_T{prm['T0']}_L{prm['L']}", INSTR, TF, {**prm, **model_params}, r1,
                        period=bounds[0], source=SRC, notes="in-sample fold1 cell; taker prints-only; $50/window; honest L")
    C.record_to_lab(STRATEGY, "wf_oos", INSTR, TF, {**best, **model_params}, oos, period=period, source=SRC,
                    notes="HEADLINE walk-forward OOS folds 2+3 (fold1 empty by construction); honest L>=settlement delay")
    out.update(best_params={**best, **model_params}, oos=slim(oos), insample=table.to_dict("records"),
               oos_folds=oos["folds"][1:])

    # ---------------- neighbours: OOS of every honest cell (sensitivity, not the headline)
    print("\n=== OOS (folds 2+3) of every honest grid cell — sensitivity only ===")
    neigh = []
    for prm in GRID:
        parts = [run_fn(prm, s, e) for s, e in bounds[1:]]
        parts = [x for x in parts if len(x)]
        tr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        r = C.oos_result(tr, period, 3)
        neigh.append(dict(params=prm, **slim(r)))
        print(f"  {prm}  {fmt(r)}")
        C.record_to_lab(STRATEGY, f"oos_X{prm['X']}_T{prm['T0']}_L{prm['L']}", INSTR, TF, {**prm, **model_params}, r,
                        period=period, source=SRC, notes="OOS folds2+3 of a non-selected honest cell (sensitivity)")
    out["neighbors_oos"] = neigh

    # ---------------- contamination decay: same rule with L=1..5 (look-ahead vs settlement delay)
    print("\n=== CONTAMINATION DIAGNOSTIC: X=0.10 T0=210, L=1..8 over the full span (NOT tradeable for L<6) ===")
    decay = []
    for prm in GRID_CONTAM + [dict(X=0.10, T0=210, L=6), dict(X=0.10, T0=210, L=8)]:
        col = f"pm_{strike}_{sname}_L{prm['L']}"
        tr = build_trades(full, prm["X"], prm["T0"], col)
        r = C.evaluate(tr, 3, *period)
        decay.append(dict(params=prm, **slim(r)))
        print(f"  L={prm['L']}  {fmt(r)}")
        if prm["L"] in L_CONTAM:
            C.record_to_lab(STRATEGY, f"CONTAM_X{prm['X']}_T{prm['T0']}_L{prm['L']}", INSTR, TF, {**prm, **model_params}, r,
                            period=period, source=SRC, trust="suspect",
                            notes="LOOK-AHEAD: model lag < print settlement delay; diagnostic only, not tradeable")
    out["contamination_decay"] = decay

    # ---------------- breakdowns for the selected honest params over the full span
    tr_all = build_trades(full, best["X"], best["T0"], f"pm_{strike}_{sname}_L{best['L']}")
    r_all = C.evaluate(tr_all, 3, *period)
    print("\nselected params, full span all 3 folds (fold1 in-sample):", fmt(r_all))
    C.record_to_lab(STRATEGY, "selected_fullspan", INSTR, TF, {**best, **model_params}, r_all, period=period, source=SRC,
                    notes="selected honest params over all 3 folds (fold 1 is in-sample)")
    if len(tr_all):
        tr_all = C.add_pnl(tr_all)
        def agg(g):
            return g.agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), wr=("exit_px", "mean"), avg_px=("entry_px", "mean"), pm=("pm_first", "mean"))
        print("\nby side:"); print(agg(tr_all.groupby("side_up")).to_string())
        print("\nby fee schedule:"); print(agg(tr_all.groupby("fee_rate")).to_string())
        tr_all["px_bin"] = pd.cut(tr_all.entry_px, [0, 0.3, 0.5, 0.7, 0.9, 1.0])
        print("\nby entry price:"); print(agg(tr_all.groupby("px_bin", observed=True)).to_string())
        tr_all["rel_bin"] = pd.cut(tr_all.first_rel, [199, 240, 270, 285, 295, 300])
        print("\nby first-fill rel:"); print(agg(tr_all.groupby("rel_bin", observed=True)).to_string())
        day = tr_all.groupby(tr_all.entry_time.dt.date).net_pnl.agg(["size", "sum"])
        print("\nby day:"); print(day.to_string())
        out["by_day"] = {str(k): [int(v["size"]), float(v["sum"])] for k, v in day.iterrows()}
        out["by_px"] = {str(k): [int(v["n"]), float(v["net"]), float(v["wr"]), float(v["avg_px"])] for k, v in agg(tr_all.groupby("px_bin", observed=True)).iterrows()}

    # ---------------- shuffle test: model from a random other window at the same rel
    rng = np.random.default_rng(7)
    sh_res = []
    col = f"pm_{strike}_{sname}_L{best['L']}"
    for k in range(3):
        sh = full[["ts", "t", "rel", "u", "size", "fee_rate", "fee_exp", "outcome_up", "ask_up", "ask_dn", col]].copy()
        uts = sh.ts.unique(); perm = dict(zip(uts, rng.permutation(uts)))
        src = sh[["ts", "rel", col]].copy(); src["ts"] = src.ts.map(perm)
        src = src.groupby(["ts", "rel"])[col].mean().rename("pm_sh").reset_index()
        sh = sh.merge(src, on=["ts", "rel"], how="left")
        tr_sh = build_trades(sh, best["X"], best["T0"], "pm_sh")
        r = C.evaluate(tr_sh, 3, *period)
        sh_res.append(slim(r)); print(f"\nshuffle {k}: {fmt(r)}")
        C.record_to_lab(STRATEGY, f"shuffle_{k}", INSTR, TF, {**best, **model_params}, r, period=period, source=SRC,
                        notes="signal shuffled across windows (same rel); should destroy any edge")
    out["shuffle"] = sh_res

    # ---------------- fourth check: stratified Feb-Aug sample with the selected params
    if len(strat):
        tr_s = build_trades(strat, best["X"], best["T0"], col)
        sp = (pd.Timestamp(int(strat.ts.min()), unit="s", tz="UTC"), pd.Timestamp(int(strat.ts.max()) + 300, unit="s", tz="UTC"))
        r_s = C.evaluate(tr_s, 3, *sp)
        print("\nstratified Feb-Aug sample, selected params:", fmt(r_s))
        if len(tr_s):
            tr_s = C.add_pnl(tr_s)
            mon = tr_s.groupby(tr_s.entry_time.dt.strftime("%Y-%m")).net_pnl.agg(["size", "sum"])
            print(mon.to_string())
            out["strat_by_month"] = {str(k): [int(v["size"]), float(v["sum"])] for k, v in mon.iterrows()}
        C.record_to_lab(STRATEGY, "strat_feb_jul", INSTR, TF, {**best, **model_params}, r_s, period=sp, source=SRC,
                        notes="fourth check: stratified monthly sample outside the full-coverage span")
        out["strat"] = slim(r_s)

    with open(ROOT / "tests" / "h_poly_lastminute_1s_result.json", "w") as f:
        json.dump(out, f, indent=1, default=str)
    return out


if __name__ == "__main__":
    main()
