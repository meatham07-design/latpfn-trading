"""Download Binance BTCUSDT 1m klines (public archive) into data/binance/ and
build data/binance_BTCUSDT_1m.parquet (UTC index = bar open)."""
import io, zipfile, datetime as dt, sys
from pathlib import Path
import requests, pandas as pd
ROOT = Path(__file__).resolve().parent
D = ROOT / "data" / "binance"; D.mkdir(parents=True, exist_ok=True)
COLS = ["open_time","open","high","low","close","volume","close_time","qav","n","tbv","tqv","ignore"]
def load(url, name):
    f = D / name
    if not f.exists():
        r = requests.get(url, timeout=120)
        if r.status_code != 200:
            print("missing", url); return None
        f.write_bytes(r.content)
    z = zipfile.ZipFile(f); csv = z.open(z.namelist()[0])
    df = pd.read_csv(csv, header=None, names=COLS)
    if isinstance(df.iloc[0,0], str):  # header row present
        df = df.iloc[1:]
    return df
parts = []
for m in range(1, 9):
    df = load(f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-{m:02d}.zip", f"m-2026-{m:02d}.zip")
    if df is not None: parts.append(df)
    else:
        d = dt.date(2026, m, 1)
        while d.month == m and d <= dt.date.today():
            df = load(f"https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{d}.zip", f"d-{d}.zip")
            if df is not None: parts.append(df)
            d += dt.timedelta(days=1)
df = pd.concat(parts, ignore_index=True)
ot = pd.to_numeric(df["open_time"])
ot = ot.where(ot < 1e14, ot // 1000)  # micros -> ms
df.index = pd.to_datetime(ot, unit="ms", utc=True); df.index.name = "time"
df = df[["open","high","low","close","volume"]].astype(float).sort_index()
df = df[~df.index.duplicated()]
df.to_parquet(ROOT / "data" / "binance_BTCUSDT_1m.parquet")
print(df.shape, df.index.min(), df.index.max())
