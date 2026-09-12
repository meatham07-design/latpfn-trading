"""Point-in-time Hyperliquid panel for the cross-sectional tests (round 2).

Fetches (public read-only, cached under data/xsec_pit/):
  * 1h candles for every non-delisted perp in hl_universe_all.parquet that is
    not already cached in data/ (plus delisted perps from metaAndAssetCtxs, so
    that the point-in-time universe is not survivorship-filtered)
  * 1d candles for every coin (longer history -> 30d lookback available from
    the first 1h bar)
  * hourly funding for the coins requested by the caller
Existing data/hl_<coin>_1h.parquet and data/hl_funding_<coin>.parquet are
reused untouched (nothing outside data/xsec_pit/ is written).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

PIT = C.DATA / "xsec_pit"
PIT.mkdir(exist_ok=True)
S = requests.Session()
LOG = PIT / "_fetch_log.json"


def post(body, tries=6):
    for k in range(tries):
        try:
            r = S.post(C.HL_INFO_URL, json=body, timeout=60)
            if r.status_code == 429:
                time.sleep(3 + 3 * k); continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if k == tries - 1: raise
            time.sleep(2.0 * (k + 1))


def _candles_df(raw, now):
    if not raw:
        return None
    df = pd.DataFrame(raw)
    df["time"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    out = pd.DataFrame({"open": df["o"].astype(float).values, "high": df["h"].astype(float).values,
                        "low": df["l"].astype(float).values, "close": df["c"].astype(float).values,
                        "volume": df["v"].astype(float).values, "trades": df["n"].astype(float).values},
                       index=pd.DatetimeIndex(df["time"]))
    out.index.name = "time"
    out = out[~out.index.duplicated(keep="last")].sort_index()
    if int(df["T"].iloc[-1]) > now:      # drop still-forming candle
        out = out.iloc[:-1]
    return out


def fetch_candles(coin, interval):
    now = int(time.time() * 1000)
    raw = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": 0, "endTime": now}})
    return _candles_df(raw, now)


def fetch_funding(coin, days=215):
    now = int(time.time() * 1000)
    start = now - days * 86400000
    parts = []
    while True:
        chunk = post({"type": "fundingHistory", "coin": coin, "startTime": start, "endTime": now})
        if not chunk: break
        parts.extend(chunk)
        last = int(chunk[-1]["time"])
        if len(chunk) < 500 or last >= now: break
        start = last + 1
        time.sleep(0.3)
    if not parts: return None
    df = pd.DataFrame(parts)
    df["time"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    out = pd.DataFrame({"fundingRate": df["fundingRate"].astype(float).values,
                        "premium": df["premium"].astype(float).values}, index=pd.DatetimeIndex(df["time"]))
    out.index.name = "time"
    return out[~out.index.duplicated(keep="last")].sort_index()


def all_coins() -> tuple[list[str], list[str]]:
    """(listed coins from hl_universe_all, delisted coins from a fresh meta call, cached)."""
    u = pd.read_parquet(C.DATA / "hl_universe_all.parquet")
    listed = u["coin"].tolist()
    f = PIT / "_delisted.json"
    if f.exists():
        delisted = json.loads(f.read_text())
    else:
        meta, _ = post({"type": "metaAndAssetCtxs"})
        delisted = [m["name"] for m in meta["universe"] if m.get("isDelisted")]
        f.write_text(json.dumps(delisted))
    return listed, delisted


def path_1h(coin):
    p = C.DATA / f"hl_{coin}_1h.parquet"
    return p if p.exists() else PIT / f"hl_{coin}_1h.parquet"


def path_1d(coin):
    return PIT / f"hl_{coin}_1d.parquet"


def path_fund(coin):
    p = C.DATA / f"hl_funding_{coin}.parquet"
    return p if p.exists() else PIT / f"hl_funding_{coin}.parquet"


def ensure_candles(coins, sleep=0.7, verbose=True):
    problems = []
    for i, c in enumerate(coins):
        for iv, pth in (("1h", path_1h(c)), ("1d", path_1d(c))):
            if pth.exists():
                continue
            try:
                df = fetch_candles(c, iv)
                if df is None or len(df) == 0:
                    problems.append(f"{c} {iv}: empty")
                    # write an empty marker so we do not refetch
                    pd.DataFrame(columns=["open", "high", "low", "close", "volume", "trades"],
                                 index=pd.DatetimeIndex([], name="time")).to_parquet(pth)
                else:
                    df.to_parquet(pth)
                if verbose:
                    print(f"[{i+1}/{len(coins)}] {c} {iv} rows={0 if df is None else len(df)}", flush=True)
            except Exception as e:
                problems.append(f"{c} {iv}: {e!r}"); print("ERR", c, iv, e, flush=True)
            time.sleep(sleep)
    if problems:
        LOG.write_text(json.dumps(problems, indent=1))
    return problems


def ensure_funding(coins, sleep=0.4, verbose=True):
    problems = []
    for i, c in enumerate(coins):
        pth = path_fund(c)
        if pth.exists():
            continue
        try:
            f = fetch_funding(c)
            if f is None or len(f) == 0:
                problems.append(f"{c} funding: empty")
                pd.DataFrame(columns=["fundingRate", "premium"], index=pd.DatetimeIndex([], name="time")).to_parquet(pth)
            else:
                f.to_parquet(pth)
            if verbose:
                print(f"[{i+1}/{len(coins)}] {c} funding rows={0 if f is None else len(f)}", flush=True)
        except Exception as e:
            problems.append(f"{c} funding: {e!r}"); print("ERR", c, "funding", e, flush=True)
        time.sleep(sleep)
    return problems


def read(pth):
    df = pd.read_parquet(pth)
    if len(df) == 0:
        return None
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    df.index = df.index.tz_convert("UTC") if df.index.tz is not None else df.index.tz_localize("UTC")
    df.index.name = "time"
    return df.sort_index()


if __name__ == "__main__":
    listed, delisted = all_coins()
    print("listed", len(listed), "delisted", len(delisted))
    need = [c for c in listed + delisted if not (path_1h(c).exists() and path_1d(c).exists())]
    print("need candles for", len(need))
    print("problems:", ensure_candles(need))
