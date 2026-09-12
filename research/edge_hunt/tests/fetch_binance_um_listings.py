"""Fetch the first two months of 1h klines + funding for every USDT-margined
perp in the public Binance archive (data.binance.vision, static S3 - fapi is
HTTP 451 from this machine).  Includes delisted symbols -> point-in-time.
Cache: data/binance_um_listings/<SYM>_1h.parquet, <SYM>_funding.parquet,
_index.json (first month per symbol).  Read-only, polite (sleep between calls).
"""
from __future__ import annotations
import io, json, re, sys, time, zipfile
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "binance_um_listings"; OUT.mkdir(exist_ok=True)
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
S = requests.Session(); S.headers["User-Agent"] = "edge-hunt-research/1.0 (read-only)"
SLEEP = 0.15
REVERSE = "--reverse" in sys.argv
IDX = OUT / ("_index_rev.json" if REVERSE else "_index.json")
index = json.loads(IDX.read_text()) if IDX.exists() else {}
OTHER = OUT / ("_index.json" if REVERSE else "_index_rev.json")


def get(url, **kw):
    for k in range(5):
        try:
            r = S.get(url, timeout=60, **kw)
            if r.status_code == 404:
                return None
            if r.status_code in (429, 503):
                time.sleep(5 * (k + 1)); continue
            r.raise_for_status(); return r
        except requests.RequestException:
            time.sleep(2 * (k + 1))
    return None


def listing(prefix):
    out, marker = [], None
    while True:
        p = {"delimiter": "/", "prefix": prefix, "max-keys": 1000}
        if marker: p["marker"] = marker
        r = get(S3, params=p); x = r.text
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:]
        out += re.findall(r"<Key>([^<]+)</Key>", x)
        if "<IsTruncated>true</IsTruncated>" not in x: break
        marker = re.search(r"<NextMarker>([^<]+)</NextMarker>", x).group(1); time.sleep(SLEEP)
    return out


def read_zip_csv(key):
    r = get(DL + key)
    if r is None: return None
    z = zipfile.ZipFile(io.BytesIO(r.content)); name = z.namelist()[0]
    raw = z.open(name).read().decode()
    first = raw.split("\n", 1)[0]
    header = 0 if not first.split(",")[0].strip().isdigit() else None
    return pd.read_csv(io.StringIO(raw), header=header)


def klines_df(df):
    df = df.iloc[:, :11].copy()
    df.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time",
                  "quote_volume", "trades", "taker_buy_volume", "taker_buy_quote_volume"]
    df["time"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    out = df.set_index("time")[["open", "high", "low", "close", "volume", "quote_volume", "trades"]].astype(float)
    out.index.name = "time"
    return out[~out.index.duplicated(keep="last")].sort_index()


def funding_df(df):
    df = df.iloc[:, :3].copy(); df.columns = ["calc_time", "interval_h", "fundingRate"]
    df["time"] = pd.to_datetime(df["calc_time"].astype("int64"), unit="ms", utc=True)
    out = df.set_index("time")[["fundingRate", "interval_h"]].astype(float)
    out.index.name = "time"
    return out[~out.index.duplicated(keep="last")].sort_index()


def main(n_months=2):
    syms = [s.split("/")[-2] for s in listing("data/futures/um/monthly/klines/")]
    syms = [s for s in syms if s.endswith("USDT") and "_" not in s]
    print(f"{len(syms)} USDT perp symbols in archive", flush=True)
    if REVERSE: syms = syms[::-1]
    for i, sym in enumerate(syms):
        if sym in index and (OUT / f"{sym}_1h.parquet").exists():
            continue
        other = json.loads(OTHER.read_text()) if OTHER.exists() else {}
        if sym in other and (OUT / f"{sym}_1h.parquet").exists():
            index[sym] = other[sym]; continue
        try:
            keys = [k for k in listing(f"data/futures/um/monthly/klines/{sym}/1h/") if k.endswith(".zip")]
            time.sleep(SLEEP)
            if not keys:
                index[sym] = {"first_month": None, "error": "no 1h zips"}; continue
            months = sorted(re.search(r"-1h-(\d{4}-\d{2})\.zip$", k).group(1) for k in keys)
            use = months[:n_months]
            if (OUT / f"{sym}_1h.parquet").exists():   # downloaded by an earlier run; only index it
                k0 = pd.read_parquet(OUT / f"{sym}_1h.parquet"); f0 = OUT / f"{sym}_funding.parquet"
                index[sym] = {"first_month": months[0], "last_month": months[-1], "n_months": len(months),
                              "n_1h": int(len(k0)), "n_funding": int(len(pd.read_parquet(f0))) if f0.exists() else 0,
                              "first_1h": str(k0.index[0])}
                continue
            parts = []
            for m in use:
                d = read_zip_csv(f"data/futures/um/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip"); time.sleep(SLEEP)
                if d is not None: parts.append(klines_df(d))
            fparts = []
            for m in use:
                d = read_zip_csv(f"data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip"); time.sleep(SLEEP)
                if d is not None: fparts.append(funding_df(d))
            if parts:
                k = pd.concat(parts).sort_index(); k = k[~k.index.duplicated()]
                k.to_parquet(OUT / f"{sym}_1h.parquet")
            if fparts:
                f = pd.concat(fparts).sort_index(); f = f[~f.index.duplicated()]
                f.to_parquet(OUT / f"{sym}_funding.parquet")
            index[sym] = {"first_month": months[0], "last_month": months[-1], "n_months": len(months),
                          "n_1h": int(sum(len(p) for p in parts)), "n_funding": int(sum(len(p) for p in fparts)),
                          "first_1h": str(parts[0].index[0]) if parts else None}
        except Exception as e:
            index[sym] = {"first_month": None, "error": repr(e)[:200]}
        if i % 20 == 0:
            IDX.write_text(json.dumps(index, indent=1)); print(i, sym, index[sym], flush=True)
    IDX.write_text(json.dumps(index, indent=1)); print("done", len(index), flush=True)


if __name__ == "__main__":
    main()
