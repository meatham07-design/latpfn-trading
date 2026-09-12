"""Hypothesis latpfn_reversal_fade (round 3): is the repo's deployed LaT-PFN
forecaster a tradeable directional signal (RAW), a contrarian signal (FADE the
model's counter-trend calls), or useful as a FILTER - net of Hyperliquid fees,
walk-forward (select on fold 1, report folds 2+3)?

Forecasts come from tests/latpfn_batch_forecast.py (cached under
data/latpfn_preds/): the bot's own forecaster.wrapper inputs (n_history=180,
n_prompt=60, 12 lagged self-context windows at stride 60, CPU), evaluated at the
CLOSE of bar t using only bars <= t.  Signal at bar t -> entry at bar t+1.

Signals (per forecast):
  wrap60 : the wrapper's own direction (mean of forecast bars 51-60 vs last close,
           +/-0.05% dead-band) = what the bot trades.
  fc12   : sign(forecast bar 12 - last close), same dead-band (the 12-bar call).
  trend  : sign(close[t] / close[t-24] - 1)   (trailing 24-bar return)
Arms (all entered at bar t+1, held H bars, exit at open of bar t+1+H, taker):
  RAW      : side = model direction.
  FADE     : only when model direction is AGAINST trend -> side = trend (against model).
  F_AGREE  : model direction only when it agrees with trend.
  F_DISAGR : model direction only when it disagrees with trend (mirror of FADE).
  F_CONF   : model direction only when wrapper confidence >= 0.6.
Execution modes (separate walk-forwards):
  taker : entry at open[t+1] (taker), exit at open[t+1+H] (taker).
  maker : resting limit at close[t]; filled only if bar t+1 trades THROUGH the
          limit by >= 5 bps (queue priority); exit at open[t+1+H] (taker).
Hourly funding for every hour boundary inside the hold is added to fee_usd
(sign-aware).  $1,000 notional per trade; overlapping signals are independent
trades.

Round 4 additions: pure-inverse arms INV (side = -model on every call), INV_CONF (-model when
confidence >= 0.6), INV_HI (-model when confidence >= 0.999, the wrapper's saturated calls).
Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_latpfn_reversal_fade_hl.py [--interval 1h]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

STRATEGY = "latpfn_reversal_fade"
SRC = "tests/h_latpfn_reversal_fade_hl.py"
NOTIONAL = 1_000.0
TT = 5e-4          # maker trade-through requirement (5 bps)
CONF_MIN = 0.6
TREND_LB = 24
DEAD = 0.0005      # wrapper's direction dead-band

ap = argparse.ArgumentParser()
ap.add_argument("--interval", default="1h")
ap.add_argument("--no-lab", action="store_true")
ap.add_argument("--shuffle-reps", type=int, default=200)
ap.add_argument("--partial", action="store_true", help="dev only: include *_partial caches")
ARGS = ap.parse_args()
TF = ARGS.interval
PRED_DIR = C.DATA / "latpfn_preds"
BAR = pd.Timedelta(TF)

# ---------------------------------------------------------------------------
# data: forecasts + bars + funding -> one signal table
# ---------------------------------------------------------------------------
def load_preds():
    out = []
    files = sorted(PRED_DIR.glob(f"hl_*_{TF}.parquet"))
    if ARGS.partial:
        files += sorted(PRED_DIR.glob(f"hl_*_{TF}_partial.parquet"))
    for p in files:
        d = pd.read_parquet(p)
        out.append(d)
    if not out:
        raise SystemExit("no cached forecasts")
    d = pd.concat(out)
    d.index = pd.to_datetime(d.index, utc=True)
    d.index.name = "time"
    return d


def _sign_db(x):
    return np.where(x > DEAD, 1, np.where(x < -DEAD, -1, 0))


def build_signals(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for coin, d in preds.groupby("coin"):
        bars = C.hl_candles(coin, TF)
        try:
            fund = C.hl_funding(coin)["fundingRate"]
            fund.index = fund.index.floor("h")
            fund = fund[~fund.index.duplicated()]
        except FileNotFoundError:
            fund = pd.Series(dtype=float)
        d = d.sort_index()
        pos = bars.index.get_indexer(d.index)
        ok = pos >= 0
        d, pos = d[ok], pos[ok]
        n = len(bars)
        close = bars["close"].values
        opn = bars["open"].values
        low, high = bars["low"].values, bars["high"].values
        s = pd.DataFrame(index=d.index)
        s["coin"] = coin
        s["pos"] = pos
        s["close_t"] = close[pos]
        assert np.allclose(s["close_t"].values, d["current_price"].values), "pred/bar mismatch"
        s["wrap60"] = _sign_db((d["fc_end"] - d["current_price"]) / d["current_price"])
        s["fc12"] = _sign_db((d["fc_12"] - d["current_price"]) / d["current_price"])
        s["fc12_bc"] = _sign_db((d["fc_12"] - d["backcast_last"]) / d["current_price"])
        s["wrap60_bc"] = _sign_db((d["fc_end"] - d["backcast_last"]) / d["current_price"])
        s["confidence"] = d["confidence"].values
        s["regime"] = d["regime"].values
        tr = np.full(len(pos), np.nan)
        okt = pos >= TREND_LB
        tr[okt] = close[pos[okt]] / close[pos[okt] - TREND_LB] - 1
        s["trend_ret"] = tr
        s["trend"] = np.sign(tr)
        # next-bar entry data (no look-ahead: bar t+1 opens after the signal)
        p1 = pos + 1
        s["entry_ok"] = p1 < n
        s["open_t1"] = np.where(p1 < n, opn[np.minimum(p1, n - 1)], np.nan)
        s["low_t1"] = np.where(p1 < n, low[np.minimum(p1, n - 1)], np.nan)
        s["high_t1"] = np.where(p1 < n, high[np.minimum(p1, n - 1)], np.nan)
        s["entry_time"] = bars.index[np.minimum(p1, n - 1)]
        for H in (4, 8, 12):
            px = pos + 1 + H
            s[f"exit_ok_{H}"] = px < n
            s[f"exit_open_{H}"] = np.where(px < n, opn[np.minimum(px, n - 1)], np.nan)
            s[f"exit_time_{H}"] = bars.index[np.minimum(px, n - 1)]
            # funding: hour boundaries inside (entry_time, exit_time]
            if len(fund):
                et = s["entry_time"]; xt = s[f"exit_time_{H}"]
                fsum = np.zeros(len(s))
                fcum = fund.cumsum()
                # sum of funding at hours h with entry < h <= exit  (charged at each hour mark)
                a = fcum.reindex(et.dt.floor("h"), method="ffill").values
                b = fcum.reindex(xt.dt.floor("h"), method="ffill").values
                fsum = np.nan_to_num(b - a)
                s[f"fund_{H}"] = fsum
            else:
                s[f"fund_{H}"] = 0.0
        # BTC hedge legs
        rows.append(s)
    S = pd.concat(rows).sort_index()
    S = S[S["entry_ok"] & S["trend"].notna()]
    return S


PREDS = load_preds()
SIG = build_signals(PREDS)
COINS = sorted(SIG["coin"].unique())
BTC = C.hl_candles("BTC", TF)
UNIV = C.hl_universe().set_index("coin")
T0, T1 = SIG.index.min(), SIG.index.max()
BOUNDS = C.fold_bounds((T0, T1), 3)
print(f"[data] {TF}: {len(PREDS)} forecasts, {len(SIG)} usable signals, {len(COINS)} coins, {T0} -> {T1}")
print("[data] folds:", [(a.strftime('%m-%d'), b.strftime('%m-%d')) for a, b in BOUNDS])

# ---------------------------------------------------------------------------
# trade construction
# ---------------------------------------------------------------------------
def arm_sides(S: pd.DataFrame, arm: str, basis: str) -> np.ndarray:
    d = S[basis].values.astype(int)
    tr = S["trend"].values.astype(int)
    if arm == "RAW":
        return d
    if arm == "FADE":
        return np.where(d * tr < 0, tr, 0)
    if arm == "F_AGREE":
        return np.where(d * tr > 0, d, 0)
    if arm == "F_DISAGR":
        return np.where(d * tr < 0, d, 0)
    if arm == "F_CONF":
        return np.where(S["confidence"].values >= CONF_MIN, d, 0)
    if arm == "INV":            # pure fade: opposite of every model call
        return -d
    if arm == "INV_CONF":       # fade only confident calls
        return np.where(S["confidence"].values >= CONF_MIN, -d, 0)
    if arm == "INV_HI":         # fade only saturated-confidence calls
        return np.where(S["confidence"].values >= 0.999, -d, 0)
    if arm == "TREND":          # model-free baseline: side = 24-bar trend sign on every signal bar
        return tr
    if arm == "TREND_AGREE":    # trend only on bars where the model agrees (== F_AGREE trades)
        return np.where(d * tr > 0, tr, 0)
    raise ValueError(arm)


def make_trades(S: pd.DataFrame, arm: str, basis: str, H: int, mode: str,
                sides: np.ndarray | None = None) -> pd.DataFrame:
    side = arm_sides(S, arm, basis) if sides is None else sides
    m = (side != 0) & S[f"exit_ok_{H}"].values
    s = S[m]; side = side[m]
    if len(s) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    if mode == "taker":
        entry = s["open_t1"].values
        maker_entry = np.zeros(len(s), bool)
        fill = np.ones(len(s), bool)
    else:
        lim = s["close_t"].values
        fill = np.where(side > 0, s["low_t1"].values <= lim * (1 - TT), s["high_t1"].values >= lim * (1 + TT))
        entry = lim
        maker_entry = np.ones(len(s), bool)
    s, side, entry, maker_entry = s[fill], side[fill], entry[fill], maker_entry[fill]
    if len(s) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    exit_px = s[f"exit_open_{H}"].values
    qty = NOTIONAL / entry
    ne, nx = qty * entry, qty * exit_px
    fee = np.where(maker_entry, C.hl_fee(1, True), C.hl_fee(1, False)) * ne + C.hl_fee(1, False) * nx
    # funding: long pays when rate > 0 -> cost = side * rate * notional
    fee = fee + side * s[f"fund_{H}"].values * NOTIONAL
    t = pd.DataFrame(dict(entry_time=s["entry_time"].values, exit_time=s[f"exit_time_{H}"].values,
                          side=side, entry_px=entry, exit_px=exit_px, qty=qty, notional_usd=ne,
                          fee_usd=fee, instrument=s["coin"].values, multiplier=1.0,
                          signal_time=s.index.values, regime=s["regime"].values,
                          confidence=s["confidence"].values))
    return t


def in_window(t: pd.DataFrame, start, end) -> pd.DataFrame:
    if len(t) == 0:
        return t
    et = pd.to_datetime(t["entry_time"], utc=True)
    return t[(et >= start) & (et < end)].reset_index(drop=True)


GRID = []
for H in (4, 8, 12):
    for basis in ("wrap60", "fc12"):
        for arm in ("RAW", "FADE"):
            GRID.append(dict(arm=arm, basis=basis, H=H))
    for arm in ("F_AGREE", "F_DISAGR", "F_CONF", "INV", "INV_CONF", "INV_HI"):
        GRID.append(dict(arm=arm, basis="wrap60", H=H))
assert len(GRID) <= 30, len(GRID)

CACHE = {}


def trades_for(p, mode):
    key = (p["arm"], p["basis"], p["H"], mode)
    if key not in CACHE:
        CACHE[key] = make_trades(SIG, p["arm"], p["basis"], p["H"], mode)
    return CACHE[key]


def record(variant, params, res, notes=None, instrument=None, period=None):
    if ARGS.no_lab:
        return
    per = period or (T0, T1)
    instrument = instrument or f"HL_{len(COINS)}coins"
    C.record_to_lab(STRATEGY, "hl|" + variant, instrument, TF, params, res, period=per, source=SRC, notes=notes)


def fmt(r):
    return (f"n={r['n']:5d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.3f} "
            f"sh={r['sharpe']:6.2f} bps={r['net_bps']:6.2f} folds={[round(f, 1) for f in r['folds']]}")


# ---------------------------------------------------------------------------
# diagnostics: model hit rates by fold and regime
# ---------------------------------------------------------------------------
lines = []
def say(s=""):
    print(s); lines.append(s)

say(f"# latpfn_reversal_fade - Hyperliquid {TF} (cached forecasts, exact timestamps)\n")
say(f"Forecasts: {len(PREDS)}  usable signals: {len(SIG)}  coins ({len(COINS)}): {', '.join(COINS)}")
say(f"Period {T0:%Y-%m-%d} -> {T1:%Y-%m-%d}; folds: " + ", ".join(f"[{a:%m-%d},{b:%m-%d})" for a, b in BOUNDS))
say("")
say("## Model direction distribution")
for basis in ("wrap60", "fc12", "wrap60_bc", "fc12_bc"):
    vc = SIG[basis].value_counts(normalize=True).reindex([1, 0, -1]).fillna(0)
    say(f"- {basis}: long {vc[1]:.2f} neutral {vc[0]:.2f} short {vc[-1]:.2f}")
say(f"- confidence: mean {SIG.confidence.mean():.3f}, >=0.6 share {(SIG.confidence >= 0.6).mean():.2f}, ==1.0 share {(SIG.confidence >= 0.999).mean():.2f}")
say(f"- regime: {SIG.regime.value_counts(normalize=True).round(2).to_dict()}")
say(f"- model vs 24-bar trend (wrap60): agree {(SIG.wrap60 * SIG.trend > 0).mean():.2f}, disagree {(SIG.wrap60 * SIG.trend < 0).mean():.2f}")
say("## Per-fold tilt: model long share vs realised market drift (mean 12-bar fwd return, gross)")
lab0 = C.fold_labels(pd.Series(SIG.index), 3, T0, T1)
for k in range(3):
    m = lab0 == k
    fwd = (SIG["exit_open_12"] / SIG["open_t1"] - 1)[m & SIG["exit_ok_12"]]
    say(f"- fold {k+1}: n={m.sum()} long share wrap60 {(SIG.wrap60[m] > 0).mean():.2f} fc12 {(SIG.fc12[m] > 0).mean():.2f} | "
        f"trend>0 share {(SIG.trend[m] > 0).mean():.2f} | mean fwd 12-bar ret {fwd.mean()*1e4:.1f} bps")
say("")
say("## Raw directional hit rate (sign of open[t+1+H]-open[t+1] vs model call; gross, no fees)")
lab = C.fold_labels(pd.Series(SIG.index), 3, T0, T1)
for basis in ("wrap60", "fc12", "wrap60_bc"):
    for H in (4, 8, 12):
        d = SIG[basis].values; ok = (d != 0) & SIG[f"exit_ok_{H}"].values
        real = np.sign(SIG[f"exit_open_{H}"].values - SIG["open_t1"].values)
        hit = (d == real)[ok]
        by_fold = [f"{(d == real)[ok & (lab == k)].mean():.3f}(n={int((ok & (lab == k)).sum())})" for k in range(3)]
        by_reg = {r: round(float((d == real)[ok & (SIG.regime.values == r)].mean()), 3) for r in ("trending", "ranging", "volatile") if (ok & (SIG.regime.values == r)).sum() > 30}
        # against-trend subset
        at = ok & (d * SIG.trend.values < 0)
        say(f"- {basis} H={H}: hit {hit.mean():.3f} (n={ok.sum()}) folds {by_fold} regime {by_reg} | counter-trend calls hit {(d == real)[at].mean():.3f} (n={at.sum()})")
say("")

# ---------------------------------------------------------------------------
# walk-forward per execution mode
# ---------------------------------------------------------------------------
RESULTS = {}
for mode in ("taker", "maker"):
    say(f"## Walk-forward ({mode}) - select on fold 1, OOS = folds 2+3")
    run_fn = lambda p, s, e, mode=mode: in_window(trades_for(p, mode), s, e)
    rep = C.full_report(GRID, run_fn, (T0, T1), n_folds=3, min_trades=10)
    best, oos, table = rep["best_params"], rep["oos"], rep["insample"]
    say(f"selected on fold 1: {best}")
    say(f"OOS (folds 2+3): {fmt(oos)}")
    # full-period rows for every grid cell (folds visible), record all
    say("")
    say("| arm | basis | H | f1 n | f1 net | f1 pf | full n | full net | full pf | f1 | f2 | f3 | sel |")
    say("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for _, row in table.iterrows():
        p = json.loads(row["params"])
        full = C.evaluate(trades_for(p, mode), 3, T0, T1)
        say(f"| {p['arm']} | {p['basis']} | {p['H']} | {row.is_n} | {row.is_net:.1f} | {row.is_pf:.2f} | {full['n']} | {full['net']:.1f} | {full['pf']:.2f} | "
            f"{full['folds'][0]:.1f} | {full['folds'][1]:.1f} | {full['folds'][2]:.1f} | {'*' if row.selected else ''} |")
        record(f"{mode}|{p['arm']}|{p['basis']}|H{p['H']}|full", dict(p, mode=mode, scope="full3fold"), full,
               notes=f"in-sample grid cell (full period, 3 folds); fold1 net={row.is_net:.2f} pf={row.is_pf:.2f}")
    oos_notes = f"WALK-FORWARD OOS folds 2+3, selected on fold 1: {best}; fold1 is empty by construction"
    record(f"{mode}|OOS|{best['arm']}|{best['basis']}|H{best['H']}", dict(best, mode=mode, scope="walkforward_oos"), oos, notes=oos_notes)
    RESULTS[mode] = dict(best=best, oos=oos, oos_trades=rep["oos_trades"], table=table)
    say("")

    # ---- sanity checks on the selected variant ----
    oos_t = rep["oos_trades"]
    s2, e3 = BOUNDS[1][0], BOUNDS[2][1]
    say(f"### Sanity ({mode}, {best})")
    # (c) neighbours: same arm/basis at all H, and all arms at selected H (OOS period, no reselection)
    say("neighbours (OOS period, no reselection):")
    for H in (4, 8, 12):
        r = C.oos_result(in_window(trades_for(dict(best, H=H), mode), s2, e3), (T0, T1))
        say(f"- H={H}: {fmt(r)}")
        record(f"{mode}|OOSneighbour|{best['arm']}|{best['basis']}|H{H}", dict(best, H=H, mode=mode, scope="oos_neighbour"), r)
    for arm in ("RAW", "FADE", "F_AGREE", "F_DISAGR", "F_CONF", "INV", "INV_CONF", "INV_HI"):
        r = C.oos_result(in_window(trades_for(dict(best, arm=arm), mode), s2, e3), (T0, T1))
        say(f"- arm={arm}: {fmt(r)}")
        record(f"{mode}|OOSneighbour|{arm}|{best['basis']}|H{best['H']}", dict(best, arm=arm, mode=mode, scope="oos_neighbour"), r)
    for basis in ("wrap60", "fc12"):
        r = C.oos_result(in_window(trades_for(dict(best, basis=basis), mode), s2, e3), (T0, T1))
        say(f"- basis={basis}: {fmt(r)}")
    say("model-free baselines (same bars, OOS period):")
    for arm in ("TREND", "TREND_AGREE"):
        for H in (4, 8, 12):
            pb = dict(arm=arm, basis="wrap60", H=H)
            r = C.oos_result(in_window(trades_for(pb, mode), s2, e3), (T0, T1))
            rf = C.evaluate(trades_for(pb, mode), 3, T0, T1)
            say(f"- {arm} H={H}: OOS {fmt(r)} | fold1 net {rf['folds'][0]:.1f}")
            record(f"{mode}|baseline|{arm}|H{H}|full", dict(pb, mode=mode, scope="baseline_full3fold"), rf,
                   notes="model-free trend baseline on the same signal bars")
    # (a) shuffle model directions within coin (OOS period), 200 reps
    rng = np.random.default_rng(7)
    S_oos = SIG[(SIG["entry_time"] >= s2) & (SIG["entry_time"] < e3)]
    actual = oos["net"]
    nets = []
    for rep_i in range(ARGS.shuffle_reps):
        Ssh = S_oos.copy()
        for coin, idx in Ssh.groupby("coin").indices.items():
            perm = rng.permutation(len(idx))
            for col in ("wrap60", "fc12", "confidence"):
                v = Ssh[col].values.copy(); v[idx] = v[idx][perm]; Ssh[col] = v
        t = make_trades(Ssh, best["arm"], best["basis"], best["H"], mode)
        nets.append(C.evaluate(t)["net"] if len(t) else 0.0)
    nets = np.array(nets)
    pct = float((nets >= actual).mean())
    say(f"shuffle (model directions permuted within coin, {ARGS.shuffle_reps} reps, OOS period): actual {actual:.1f}; "
        f"shuffled mean {nets.mean():.1f} sd {nets.std():.1f} p5 {np.percentile(nets, 5):.1f} p95 {np.percentile(nets, 95):.1f}; "
        f"P(shuffle >= actual) = {pct:.3f}")
    record(f"{mode}|shuffle_ctrl|{best['arm']}|{best['basis']}|H{best['H']}", dict(best, mode=mode, scope="shuffle_mean"),
           dict(C.empty_result(), n=int(len(oos_t)), net=float(nets.mean()), folds=[0.0, 0.0, 0.0]),
           notes=f"mean of {ARGS.shuffle_reps} within-coin direction shuffles; actual={actual:.2f}; p={pct:.3f}", period=(s2, e3))
    # random-hour same-coin baseline: same n per coin & same side mix, random signal bars in OOS period
    nets_r = []
    per_coin = oos_t.groupby("instrument")["side"].apply(list).to_dict() if len(oos_t) else {}
    for rep_i in range(ARGS.shuffle_reps):
        parts = []
        for coin, sides in per_coin.items():
            pool = S_oos[S_oos["coin"] == coin]
            if len(pool) == 0:
                continue
            pick = pool.iloc[rng.integers(0, len(pool), len(sides))]
            parts.append(make_trades(pick, best["arm"], best["basis"], best["H"], mode, sides=np.array(sides)))
        t = pd.concat(parts) if parts else pd.DataFrame()
        nets_r.append(C.evaluate(t)["net"] if len(t) else 0.0)
    nets_r = np.array(nets_r)
    say(f"random-bar same-coin baseline (same n and side mix per coin): mean {nets_r.mean():.1f} sd {nets_r.std():.1f}; "
        f"P(random >= actual) = {(nets_r >= actual).mean():.3f}")
    # BTC-hedged version
    if len(oos_t):
        bt = BTC
        ep = bt["open"].reindex(pd.to_datetime(oos_t["entry_time"], utc=True)).values
        xp = bt["open"].reindex(pd.to_datetime(oos_t["exit_time"], utc=True)).values
        okh = np.isfinite(ep) & np.isfinite(xp)
        h = oos_t[okh].copy()
        hedge = pd.DataFrame(dict(entry_time=h["entry_time"], exit_time=h["exit_time"], side=-h["side"],
                                  entry_px=ep[okh], exit_px=xp[okh], qty=NOTIONAL / ep[okh], notional_usd=NOTIONAL,
                                  fee_usd=2 * C.hl_fee(NOTIONAL, False), instrument="BTC_hedge", multiplier=1.0))
        hp = C.add_pnl(hedge)["net_pnl"].values
        hh = h.copy(); hh["exit_px"] = hh["entry_px"] + (C.add_pnl(h)["gross_pnl"].values + hp) / (hh["side"] * hh["qty"])
        hh["fee_usd"] = h["fee_usd"].values
        rh = C.oos_result(hh, (T0, T1))
        say(f"BTC-hedged (equal-notional opposite BTC leg, taker fees on hedge): {fmt(rh)}")
        record(f"{mode}|OOS_btc_hedged|{best['arm']}|{best['basis']}|H{best['H']}", dict(best, mode=mode, scope="oos_btc_hedged"), rh)
    # top-3 trade removal on the selected variant and on the pure INV arm
    for label, tt in (("selected", oos_t), ("INV", in_window(trades_for(dict(best, arm="INV"), mode), s2, e3))):
        if len(tt) >= 4:
            pn = C.add_pnl(tt)["net_pnl"].values
            keep = np.argsort(-pn)[3:]
            r3 = C.oos_result(tt.iloc[np.sort(keep)], (T0, T1))
            say(f"top-3 removal ({label}): net {pn.sum():.1f} -> {r3['net']:.1f} pf {r3['pf']:.2f} folds {[round(f,1) for f in r3['folds']]}")
    # (d) per coin
    if len(oos_t):
        say("per-coin OOS:")
        pc = C.add_pnl(oos_t).groupby("instrument")["net_pnl"].agg(["count", "sum"])
        pc["vol24_usd_M"] = [round(UNIV.loc[c, "dayNtlVlm"] / 1e6, 1) if c in UNIV.index else np.nan for c in pc.index]
        pc["illiquid(<5M)"] = pc["vol24_usd_M"] < 5
        say(pc.sort_values("sum", ascending=False).round(2).to_string())
        say(f"positive coins: {(pc['sum'] > 0).sum()}/{len(pc)}; illiquid names in universe: {int(pc['illiquid(<5M)'].sum())}")
        say("per-regime OOS: " + str(C.add_pnl(oos_t).groupby("regime")["net_pnl"].agg(["count", "sum"]).round(1).to_dict()))
    # ---- secondary sanity on the pure-inverse arms (NOT walk-forward selected; reported for transparency) ----
    for arm in ("INV_HI", "INV_CONF", "INV", "FADE"):
        pa = dict(best, arm=arm)
        ta = in_window(trades_for(pa, mode), s2, e3)
        ra = C.oos_result(ta, (T0, T1))
        rf1 = C.evaluate(in_window(trades_for(pa, mode), BOUNDS[0][0], BOUNDS[0][1]), n_folds=1)
        say(f"secondary [{arm} basis={best['basis']} H={best['H']}]: fold1 (in-sample) net {rf1['net']:.1f} pf {rf1['pf']:.2f} n {rf1['n']} | OOS {fmt(ra)}")
        if len(ta) == 0:
            continue
        nets_a = []
        for rep_i in range(ARGS.shuffle_reps):
            Ssh = S_oos.copy()
            for coin, idx in Ssh.groupby("coin").indices.items():
                perm = rng.permutation(len(idx))
                for col in ("wrap60", "fc12", "confidence"):
                    v = Ssh[col].values.copy(); v[idx] = v[idx][perm]; Ssh[col] = v
            t = make_trades(Ssh, arm, best["basis"], best["H"], mode)
            nets_a.append(C.evaluate(t)["net"] if len(t) else 0.0)
        nets_a = np.array(nets_a)
        nets_ra = []
        per_coin_a = ta.groupby("instrument")["side"].apply(list).to_dict()
        for rep_i in range(ARGS.shuffle_reps):
            parts = []
            for coin, sides in per_coin_a.items():
                pool = S_oos[S_oos["coin"] == coin]
                if len(pool) == 0:
                    continue
                pick = pool.iloc[rng.integers(0, len(pool), len(sides))]
                parts.append(make_trades(pick, arm, best["basis"], best["H"], mode, sides=np.array(sides)))
            t = pd.concat(parts) if parts else pd.DataFrame()
            nets_ra.append(C.evaluate(t)["net"] if len(t) else 0.0)
        nets_ra = np.array(nets_ra)
        pc_a = C.add_pnl(ta).groupby("instrument")["net_pnl"].sum()
        pn_a = C.add_pnl(ta)["net_pnl"].values
        r3a = C.oos_result(ta.iloc[np.sort(np.argsort(-pn_a)[3:])], (T0, T1))
        mo = C.add_pnl(ta); mo["m"] = pd.to_datetime(mo["entry_time"], utc=True).dt.strftime("%m")
        p_sh = float((nets_a >= ra["net"]).mean()); p_rb = float((nets_ra >= ra["net"]).mean())
        say(f"  shuffle P(>=actual)={p_sh:.3f} (mean {nets_a.mean():.1f} sd {nets_a.std():.1f}) | random-bar same side-mix P(>=actual)={p_rb:.3f} "
            f"(mean {nets_ra.mean():.1f} sd {nets_ra.std():.1f}) | positive coins {(pc_a > 0).sum()}/{len(pc_a)} | "
            f"top-3 removal net {r3a['net']:.1f} folds {[round(f, 1) for f in r3a['folds']]} | monthly {mo.groupby('m')['net_pnl'].sum().round(0).to_dict()}")
        ls = C.add_pnl(ta).groupby("side")["net_pnl"].agg(["count", "sum"]).round(1)
        say(f"  by side: n {ls['count'].to_dict()} net {ls['sum'].to_dict()}")
        record(f"{mode}|secondary|{arm}|{best['basis']}|H{best['H']}", dict(pa, mode=mode, scope="oos_secondary_not_selected"), ra,
               notes=f"NOT walk-forward selected (fold1 net {rf1['net']:.1f}); shuffle p={p_sh:.3f}; random-bar same-side-mix p={p_rb:.3f}; positive coins {(pc_a > 0).sum()}/{len(pc_a)}")
    say("")

# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------
def verdict_for(mode):
    r = RESULTS[mode]["oos"]
    crit = dict(net_pos=r["net"] > 0, pf=r["pf"] >= 1.2, n=r["n"] >= 60, folds=all(f > 0 for f in r["folds"][1:]))
    return crit

summary = {}
for mode in RESULTS:
    r = RESULTS[mode]["oos"]
    crit = verdict_for(mode)
    summary[mode] = dict(best=RESULTS[mode]["best"], n=r["n"], net=r["net"], pf=r["pf"], wr=r["wr"], sharpe=r["sharpe"],
                         folds=r["folds"], net_bps=r["net_bps"], criteria=crit)
say("## Summary")
say("```")
say(json.dumps(summary, indent=1, default=str))
say("```")
out_json = ROOT / "tests" / f"h_latpfn_reversal_fade_hl_{TF}.json"
out_json.write_text(json.dumps(summary, indent=1, default=str))
(ROOT / "tests" / f"h_latpfn_reversal_fade_hl_{TF}.md").write_text("\n".join(lines))
print("written", out_json)
