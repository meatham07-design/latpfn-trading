"""Shared data cache + evaluation library for the edge-hunt research campaign.

All loaders read parquet files from research/edge_hunt/data/ (built by
build_data.py).  All evaluation is NET OF FEES via the fee model below.

Conventions
-----------
* Every DataFrame from a loader has a tz-aware UTC DatetimeIndex named 'time'
  that is the candle OPEN time.  Columns: open, high, low, close, volume
  (+ trades for Hyperliquid).
* trades DataFrame passed to evaluate() must have columns:
    entry_time, exit_time, side (+1/-1), entry_px, exit_px, qty,
    notional_usd, fee_usd, instrument  [, multiplier (default 1)]
  fee_usd is the TOTAL round-trip fee for the trade in USD, computed by the
  caller with hl_fee()/cme_fee().
* Chronological folds are by entry_time; fold 1 = earliest third.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LAB_DIR = Path("/Users/molt_bot/quant-lab")
LAB_DB = str(LAB_DIR / "lab.db")
PROJECT = "edge-hunt"

HL_INFO_URL = "https://api.hyperliquid.xyz/info"
HL_INTERVALS = ["1h", "15m", "5m"]

# ---------------------------------------------------------------------------
# Fee model
# ---------------------------------------------------------------------------
FEES = {
    # Hyperliquid perps: fraction of notional, PER SIDE
    "hl_taker": 0.00045,
    "hl_maker": 0.00015,
    # CME micro/e-mini: USD per contract ROUND TRIP (commission + 1 tick
    # slippage each side)
    "cme_round_trip": {
        "MNQ": 2.24, "MES": 3.74, "MYM": 2.24, "MGC": 3.24, "MBT": 3.74,
        "M2K": 2.24, "ES": 6.80, "NQ": 7.80, "GC": 14.0, "CL": 14.0,
    },
    # USD per 1.0 price point per contract
    "cme_multiplier": {
        "MNQ": 2, "MES": 5, "MYM": 0.5, "MGC": 10, "MBT": 0.1, "M2K": 5,
        "ES": 50, "NQ": 20, "GC": 100, "CL": 1000,
    },
}
CME_MULTIPLIER = FEES["cme_multiplier"]
CME_ROUND_TRIP = FEES["cme_round_trip"]


def _cme_key(instrument: str) -> str:
    """'MNQ=F' / 'yf_MNQ_F' / 'mnq' -> 'MNQ'."""
    s = str(instrument).upper().replace("YF_", "")
    for suffix in ("=F", "_F"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


def hl_fee(notional_usd: float, maker: bool = False) -> float:
    """Hyperliquid fee in USD for ONE side (entry or exit) of a trade.
    Round trip = hl_fee(entry_notional, m) + hl_fee(exit_notional, m)."""
    rate = FEES["hl_maker"] if maker else FEES["hl_taker"]
    return abs(float(notional_usd)) * rate


def cme_fee(instrument: str, contracts: float = 1) -> float:
    """CME ROUND-TRIP cost in USD for `contracts` contracts (default 1)."""
    return CME_ROUND_TRIP[_cme_key(instrument)] * abs(float(contracts))


def cme_multiplier(instrument: str) -> float:
    return CME_MULTIPLIER[_cme_key(instrument)]


def is_cme(instrument: str) -> bool:
    return _cme_key(instrument) in CME_MULTIPLIER


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def sanitize_symbol(symbol: str) -> str:
    return symbol.replace("=", "_").replace("^", "_").replace("-", "_")


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run build_data.py")
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "time"
    return df.sort_index()


def hl_candles(coin: str, interval: str = "1h") -> pd.DataFrame:
    """Hyperliquid perp candles. Index=UTC open time; open,high,low,close,
    volume (coin units), trades. close is mark/last price."""
    return _read(DATA / f"hl_{coin}_{interval}.parquet")


def hl_funding(coin: str) -> pd.DataFrame:
    """Hourly funding history: index=UTC time, fundingRate (hourly fraction),
    premium."""
    return _read(DATA / f"hl_funding_{coin}.parquet")


def hl_universe() -> pd.DataFrame:
    """Snapshot of selected perps: coin, dayNtlVlm, openInterest, funding,
    premium, markPx, oraclePx, maxLeverage, szDecimals, snapshot_time."""
    return pd.read_parquet(DATA / "hl_universe.parquet")


def list_hl_coins() -> list[str]:
    """Coins that have a 1h candle file cached."""
    coins = sorted({p.name[len("hl_"):-len("_1h.parquet")]
                    for p in DATA.glob("hl_*_1h.parquet")})
    return coins


def list_hl_funding_coins() -> list[str]:
    return sorted(p.name[len("hl_funding_"):-len(".parquet")]
                  for p in DATA.glob("hl_funding_*.parquet"))


def yf_bars(symbol: str, interval: str = "1h") -> pd.DataFrame:
    """yfinance bars. symbol may be raw ('MNQ=F', '^VIX') or sanitized.
    Index=UTC bar open time; open,high,low,close,volume."""
    return _read(DATA / f"yf_{sanitize_symbol(symbol)}_{interval}.parquet")


def list_yf_symbols() -> list[str]:
    return sorted({p.name[len("yf_"):].rsplit("_", 1)[0]
                   for p in DATA.glob("yf_*.parquet")})


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
REQUIRED_TRADE_COLS = ["entry_time", "exit_time", "side", "entry_px", "exit_px",
                       "qty", "notional_usd", "fee_usd", "instrument"]


def empty_result(n_folds: int = 3) -> dict:
    return dict(n=0, net=0.0, gross=0.0, fees=0.0, pf=0.0, wr=0.0,
                avg_win=0.0, avg_loss=0.0, folds=[0.0] * n_folds,
                fold_n=[0] * n_folds, fold_consistent=False, sharpe=0.0,
                max_dd=0.0, avg_hold_min=0.0, net_bps=0.0, total_notional=0.0)


def _prep_trades(trades: pd.DataFrame) -> pd.DataFrame:
    t = trades.copy()
    missing = [c for c in REQUIRED_TRADE_COLS if c not in t.columns]
    if missing:
        raise ValueError(f"trades missing columns {missing}")
    if "multiplier" not in t.columns:
        t["multiplier"] = 1.0
    t["multiplier"] = t["multiplier"].fillna(1.0).astype(float)
    for c in ("side", "entry_px", "exit_px", "qty", "notional_usd", "fee_usd"):
        t[c] = t[c].astype(float)
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    t["gross_pnl"] = t["side"] * (t["exit_px"] - t["entry_px"]) * t["qty"].abs() * t["multiplier"]
    t["net_pnl"] = t["gross_pnl"] - t["fee_usd"].abs()
    t["hold_min"] = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 60.0
    return t.sort_values("entry_time").reset_index(drop=True)


def add_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    """Return trades with gross_pnl / net_pnl / hold_min columns added."""
    return _prep_trades(trades)


def _utc(x) -> pd.Timestamp:
    ts = pd.Timestamp(x)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def fold_labels(times: pd.Series, n_folds: int = 3, start=None, end=None) -> np.ndarray:
    """Assign fold index (0..n_folds-1) by chronological TIME thirds (not
    trade-count thirds), so folds are contiguous calendar periods."""
    times = pd.to_datetime(pd.Series(times), utc=True)
    if len(times) == 0:
        return np.array([], dtype=int)
    lo = _utc(start) if start is not None else times.min()
    hi = _utc(end) if end is not None else times.max()
    if hi <= lo:
        return np.zeros(len(times), dtype=int)
    frac = (times - lo) / (hi - lo)
    lab = np.floor(frac.values * n_folds).astype(int)
    return np.clip(lab, 0, n_folds - 1)


def evaluate(trades: pd.DataFrame, n_folds: int = 3, start=None, end=None) -> dict:
    """Evaluate a trade list NET OF FEES.

    Folds are chronological thirds of the entry_time range (calendar-based; pass
    start/end to force the fold boundaries to a known data period so that
    empty-fold periods count as 0 rather than being collapsed).
    """
    if trades is None or len(trades) == 0:
        return empty_result(n_folds)
    t = _prep_trades(trades)
    net = t["net_pnl"].values
    gross = t["gross_pnl"].values
    fees = t["fee_usd"].abs().values
    n = len(t)
    wins = net[net > 0]
    losses = net[net < 0]
    gw, gl = wins.sum(), -losses.sum()
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    labels = fold_labels(t["entry_time"], n_folds, start, end)
    folds = [float(net[labels == k].sum()) for k in range(n_folds)]
    fold_n = [int((labels == k).sum()) for k in range(n_folds)]
    eq = np.cumsum(net)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    max_dd = float((peak - eq).max()) if n else 0.0
    sd = net.std(ddof=1) if n > 1 else 0.0
    sharpe = float(net.mean() / sd * math.sqrt(n)) if sd > 0 else 0.0
    tot_notional = float(t["notional_usd"].abs().sum())
    return dict(
        n=int(n),
        net=float(net.sum()),
        gross=float(gross.sum()),
        fees=float(fees.sum()),
        pf=float(pf),
        wr=float((net > 0).mean()),
        avg_win=float(wins.mean()) if len(wins) else 0.0,
        avg_loss=float(losses.mean()) if len(losses) else 0.0,
        folds=folds,
        fold_n=fold_n,
        fold_consistent=bool(all(f > 0 for f in folds)),
        sharpe=sharpe,
        max_dd=max_dd,
        avg_hold_min=float(t["hold_min"].mean()),
        net_bps=float(net.sum() / tot_notional * 1e4) if tot_notional > 0 else 0.0,
        total_notional=tot_notional,
    )


def fold_bounds(times, n_folds: int = 3) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Split a time range into n contiguous [start, end) folds.
    `times` may be a (start, end) tuple or a DatetimeIndex/Series."""
    if isinstance(times, (tuple, list)) and len(times) == 2:
        lo, hi = _utc(times[0]), _utc(times[1])
    else:
        idx = pd.DatetimeIndex(times)
        lo, hi = _utc(idx.min()), _utc(idx.max())
    edges = pd.date_range(lo, hi, periods=n_folds + 1)
    return [(edges[i], edges[i + 1]) for i in range(n_folds)]


def walk_forward(param_grid: Iterable[dict], run_fn: Callable[[dict, pd.Timestamp, pd.Timestamp], pd.DataFrame],
                 times, n_folds: int = 3, select_by: str = "net", min_trades: int = 10,
                 verbose: bool = False):
    """Walk-forward selection.

    param_grid : list of param dicts
    run_fn     : run_fn(params, start, end) -> trades DataFrame (only trades
                 whose entry_time falls in [start, end)).
    times      : (start, end) tuple or DatetimeIndex covering the data.

    Picks the best params on fold 1 (by `select_by` of evaluate(), default
    'net'; variants with < min_trades trades in fold 1 are ineligible unless
    nothing qualifies). Returns (best_params, oos_trades, insample_table)
    where oos_trades are the trades of best_params over folds 2..n and
    insample_table is a DataFrame with one row per param set: fold-1 metrics
    plus (for transparency) each fold's net for that param set.
    """
    bounds = fold_bounds(times, n_folds)
    f1s, f1e = bounds[0]
    rows = []
    grid = list(param_grid)
    for i, p in enumerate(grid):
        tr = run_fn(p, f1s, f1e)
        r = evaluate(tr, n_folds=1)
        row = {"idx": i, "params": json.dumps(p, sort_keys=True, default=str),
               "is_n": r["n"], "is_net": r["net"], "is_pf": r["pf"],
               "is_wr": r["wr"], "is_sharpe": r["sharpe"], "is_net_bps": r["net_bps"],
               "is_max_dd": r["max_dd"]}
        rows.append(row)
        if verbose:
            print(f"[wf] {i}/{len(grid)} {p} -> n={r['n']} net={r['net']:.2f}")
    table = pd.DataFrame(rows)
    if len(table) == 0:
        return None, pd.DataFrame(columns=REQUIRED_TRADE_COLS), table
    key = f"is_{select_by}"
    elig = table[table["is_n"] >= min_trades]
    pick = (elig if len(elig) else table).sort_values(key, ascending=False).iloc[0]
    best = grid[int(pick["idx"])]
    oos_parts = []
    for (s, e) in bounds[1:]:
        tr = run_fn(best, s, e)
        if tr is not None and len(tr):
            oos_parts.append(tr)
    oos = pd.concat(oos_parts, ignore_index=True) if oos_parts else pd.DataFrame(columns=REQUIRED_TRADE_COLS)
    table["selected"] = table["idx"] == int(pick["idx"])
    return best, oos, table


def oos_result(oos_trades: pd.DataFrame, times, n_folds: int = 3) -> dict:
    """Evaluate walk-forward OOS trades with folds aligned to the ORIGINAL
    fold boundaries (fold 1 will be 0 / empty by construction)."""
    bounds = fold_bounds(times, n_folds)
    return evaluate(oos_trades, n_folds=n_folds, start=bounds[0][0], end=bounds[-1][1])


def full_report(param_grid, run_fn, times, n_folds=3, **kw) -> dict:
    """Convenience: walk_forward + evaluate; returns dict with best_params,
    oos (evaluate dict over the FULL period with fold 1 empty), insample table,
    and headline = OOS net over folds 2+3."""
    best, oos, table = walk_forward(param_grid, run_fn, times, n_folds=n_folds, **kw)
    res = oos_result(oos, times, n_folds)
    return dict(best_params=best, oos=res, oos_trades=oos, insample=table,
                headline_oos_net=res["net"], oos_folds=res["folds"][1:])


# ---------------------------------------------------------------------------
# quant-lab recording
# ---------------------------------------------------------------------------
def _lab():
    if str(LAB_DIR) not in sys.path:
        sys.path.insert(0, str(LAB_DIR))
    import lab  # noqa
    return lab


def _period_str(x):
    if x is None:
        return None
    try:
        return pd.Timestamp(x).strftime("%Y-%m-%d")
    except Exception:
        return str(x)


def record_to_lab(strategy: str, variant: str, instrument: str, timeframe: str,
                  params: dict, result_dict: dict, period=(None, None),
                  source=None, notes: str | None = None, baseline_net=None,
                  trust: str = "measured") -> int:
    """Record one variant to quant-lab (project='edge-hunt', unit='usd').
    result_dict is the output of evaluate(). Returns the run id."""
    lab = _lab()
    r = result_dict or empty_result()
    extra = {k: r.get(k) for k in ("pf", "sharpe", "max_dd", "net_bps", "avg_hold_min", "gross", "fees")}
    note = (notes or "")
    note = note + (" | " if note else "") + "metrics=" + json.dumps(extra, default=lambda o: round(float(o), 4))
    return lab.record_run(
        project=PROJECT, strategy=strategy, variant=variant, instrument=instrument,
        timeframe=timeframe, params=params or {},
        period=(_period_str(period[0]), _period_str(period[1])),
        n_trades=int(r.get("n", 0)), net=float(r.get("net", 0.0)), unit="usd",
        win_rate=float(r.get("wr", 0.0)), baseline_net=baseline_net,
        folds=list(r.get("folds") or []), trust=trust, source=source, notes=note,
        db=LAB_DB,
    )


# ---------------------------------------------------------------------------
# Small helpers used by many strategies
# ---------------------------------------------------------------------------
def next_bar_open(bars: pd.DataFrame, signal_times: pd.DatetimeIndex) -> pd.Series:
    """For each signal time (a bar's index / close time of decision), return the
    open price of the NEXT bar (no look-ahead). NaN when there is no next bar."""
    pos = bars.index.get_indexer(signal_times) + 1
    ok = (pos > 0) & (pos < len(bars))
    out = pd.Series(np.nan, index=signal_times)
    out[ok] = bars["open"].values[pos[ok]]
    return out


def crypto_trade(entry_time, exit_time, side, entry_px, exit_px, qty, instrument,
                 maker_entry=False, maker_exit=False) -> dict:
    """Build one Hyperliquid trade row with fees computed from the fee model."""
    ne, nx = abs(qty) * entry_px, abs(qty) * exit_px
    return dict(entry_time=entry_time, exit_time=exit_time, side=side,
                entry_px=entry_px, exit_px=exit_px, qty=abs(qty), notional_usd=ne,
                fee_usd=hl_fee(ne, maker_entry) + hl_fee(nx, maker_exit),
                instrument=instrument, multiplier=1.0)


def cme_trade(entry_time, exit_time, side, entry_px, exit_px, contracts, instrument) -> dict:
    """Build one CME futures trade row with fees + multiplier from the fee model."""
    m = cme_multiplier(instrument)
    return dict(entry_time=entry_time, exit_time=exit_time, side=side,
                entry_px=entry_px, exit_px=exit_px, qty=abs(contracts),
                notional_usd=abs(contracts) * entry_px * m,
                fee_usd=cme_fee(instrument, contracts), instrument=_cme_key(instrument),
                multiplier=m)


__all__ = [
    "FEES", "CME_MULTIPLIER", "CME_ROUND_TRIP", "DATA", "ROOT", "HL_INTERVALS",
    "hl_fee", "cme_fee", "cme_multiplier", "is_cme", "sanitize_symbol",
    "hl_candles", "hl_funding", "hl_universe", "list_hl_coins", "list_hl_funding_coins",
    "yf_bars", "list_yf_symbols",
    "evaluate", "add_pnl", "empty_result", "fold_labels", "fold_bounds",
    "walk_forward", "oos_result", "full_report", "record_to_lab",
    "next_bar_open", "crypto_trade", "cme_trade",
]
