"""Download Binance BTCUSDT 1s klines (public archive, daily zips) for the days
needed by the Polymarket 5m tests into data/binance_1s/, and build one
parquet per day (UTC index = bar open, open/high/low/close). Resumable."""
import io, zipfile, datetime as dt, sys, glob, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, pandas as pd
ROOT = Path(__file__).resolve().parent
D = ROOT / "data" / "binance_1s"; D.mkdir(parents=True, exist_ok=True)
COLS = ["open_time","open","high","low","close","volume","close_time","qav","n","tbv","tqv","ignore"]
URL = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1s/BTCUSDT-1s-{d}.zip"

def needed_days():
    m = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(str(ROOT/'data/polymarket/meta_*.parquet')))], ignore_index=True)
    m = m[m.ok == 1]
    days = set(pd.to_datetime(m.ts, unit='s', utc=True).dt.date.tolist())
    return sorted(days)

def one(d):
    out = D / f"BTCUSDT-1s-{d}.parquet"
    if out.exists():
        return d, "cached"
    z = D / f"d-{d}.zip"
    if not z.exists():
        for k in range(4):
            try:
                r = requests.get(URL.format(d=d), timeout=120)
                if r.status_code == 200:
                    z.write_bytes(r.content); break
                if r.status_code == 404:
                    return d, "404"
            except Exception as e:
                time.sleep(2 * (k + 1))
        else:
            return d, "fail"
        if not z.exists():
            return d, "fail"
    zf = zipfile.ZipFile(z); df = pd.read_csv(zf.open(zf.namelist()[0]), header=None, names=COLS)
    if isinstance(df.iloc[0, 0], str):
        df = df.iloc[1:]
    ot = pd.to_numeric(df["open_time"])
    ot = ot.where(ot < 1e14, ot // 1000)
    df.index = pd.to_datetime(ot, unit="ms", utc=True); df.index.name = "time"
    df = df[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
    df = df[~df.index.duplicated()]
    df.to_parquet(out)
    z.unlink()
    return d, f"ok {len(df)}"

if __name__ == "__main__":
    days = needed_days()
    # full-span first (most recent 25 days), then the stratified sample
    days = sorted(days, reverse=True)
    print("days", len(days), days[0], days[-1], flush=True)
    with ThreadPoolExecutor(6) as ex:
        for d, s in ex.map(one, days):
            print(d, s, flush=True)
    print("DONE", flush=True)
