"""Fetch Hyperliquid universe, candles, funding -> data/*.parquet. Public read-only."""
import json, sys, time
from pathlib import Path
import pandas as pd, requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, HL_INFO_URL, HL_INTERVALS

DATA.mkdir(exist_ok=True)
S = requests.Session()
ALWAYS = ["BTC", "ETH", "SOL", "HYPE"]
TOP_N = 50
problems = []

def post(body, tries=5):
    for k in range(tries):
        try:
            r = S.post(HL_INFO_URL, json=body, timeout=60)
            if r.status_code == 429:
                time.sleep(2 + 2 * k); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(1.5 * (k + 1))

def build_universe():
    meta, ctxs = post({"type": "metaAndAssetCtxs"})
    rows = []
    for m, c in zip(meta["universe"], ctxs):
        if m.get("isDelisted"): continue
        rows.append(dict(coin=m["name"], szDecimals=m.get("szDecimals"), maxLeverage=m.get("maxLeverage"),
                         dayNtlVlm=float(c.get("dayNtlVlm") or 0), openInterest=float(c.get("openInterest") or 0),
                         funding=float(c.get("funding") or 0), premium=float(c["premium"]) if c.get("premium") is not None else float("nan"),
                         markPx=float(c.get("markPx") or 0), oraclePx=float(c.get("oraclePx") or 0),
                         prevDayPx=float(c.get("prevDayPx") or 0)))
    df = pd.DataFrame(rows).sort_values("dayNtlVlm", ascending=False).reset_index(drop=True)
    df["oi_usd"] = df["openInterest"] * df["markPx"]
    top = list(df.head(TOP_N)["coin"])
    sel = top + [c for c in ALWAYS if c not in top and c in set(df["coin"])]
    df["selected"] = df["coin"].isin(sel)
    df["snapshot_time"] = pd.Timestamp.now(tz="UTC")
    out = df[df["selected"]].drop(columns="selected").reset_index(drop=True)
    out.to_parquet(DATA / "hl_universe.parquet")
    df.to_parquet(DATA / "hl_universe_all.parquet")
    print("universe", len(out), out["coin"].tolist())
    return out["coin"].tolist()

def fetch_candles(coin, interval):
    now = int(time.time() * 1000)
    raw = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": 0, "endTime": now}})
    if not raw: return None
    df = pd.DataFrame(raw)
    df["time"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
    out = pd.DataFrame({"open": df["o"].astype(float).values, "high": df["h"].astype(float).values,
                        "low": df["l"].astype(float).values, "close": df["c"].astype(float).values,
                        "volume": df["v"].astype(float).values, "trades": df["n"].astype(float).values},
                       index=pd.DatetimeIndex(df["time"]))
    assert out["close"].notna().all(), "NaN closes"
    out.index.name = "time"
    out = out[~out.index.duplicated(keep="last")].sort_index()
    # drop the still-forming last candle (its T is in the future)
    last_T = int(df["T"].iloc[-1])
    if last_T > now:
        out = out.iloc[:-1]
    return out

def fetch_funding(coin):
    now = int(time.time() * 1000)
    start = now - 210 * 86400000
    parts = []
    while True:
        chunk = post({"type": "fundingHistory", "coin": coin, "startTime": start, "endTime": now})
        if not chunk: break
        parts.extend(chunk)
        last = int(chunk[-1]["time"])
        if len(chunk) < 500 or last >= now: break
        start = last + 1
        time.sleep(0.15)
    if not parts: return None
    df = pd.DataFrame(parts)
    df["time"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    out = pd.DataFrame({"fundingRate": df["fundingRate"].astype(float).values,
                        "premium": df["premium"].astype(float).values}, index=pd.DatetimeIndex(df["time"]))
    assert out["fundingRate"].notna().all(), "NaN funding"
    out.index.name = "time"
    return out[~out.index.duplicated(keep="last")].sort_index()

if __name__ == "__main__":
    coins = build_universe()
    for coin in coins:
        for iv in HL_INTERVALS:
            try:
                df = fetch_candles(coin, iv)
                if df is None or len(df) == 0:
                    problems.append(f"{coin} {iv}: empty"); continue
                df.to_parquet(DATA / f"hl_{coin}_{iv}.parquet")
                print(f"{coin} {iv} rows={len(df)} {df.index[0]} -> {df.index[-1]}", flush=True)
            except Exception as e:
                problems.append(f"{coin} {iv}: {e!r}"); print("ERR", coin, iv, e, flush=True)
            time.sleep(0.15)
        try:
            f = fetch_funding(coin)
            if f is None or len(f) == 0:
                problems.append(f"{coin} funding: empty")
            else:
                f.to_parquet(DATA / f"hl_funding_{coin}.parquet")
                print(f"{coin} funding rows={len(f)} {f.index[0]} -> {f.index[-1]}", flush=True)
        except Exception as e:
            problems.append(f"{coin} funding: {e!r}"); print("ERR", coin, "funding", e, flush=True)
        time.sleep(0.15)
    (DATA / "_hl_problems.json").write_text(json.dumps(problems, indent=1))
    print("DONE problems:", problems)
