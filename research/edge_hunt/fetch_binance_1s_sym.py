"""Binance spot 1s klines for SYMBOL over the given days into data/binance_1s_<SYMBOL>/ (BTCUSDT -> data/binance_1s/).
Usage: venv/bin/python fetch_binance_1s_sym.py ETHUSDT 2026-08-13 2026-08-27"""
import sys, zipfile, datetime as dt, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, pandas as pd
ROOT = Path(__file__).resolve().parent
SYM = sys.argv[1]
D = ROOT / "data" / ("binance_1s" if SYM == "BTCUSDT" else f"binance_1s_{SYM}"); D.mkdir(parents=True, exist_ok=True)
COLS = ["open_time","open","high","low","close","volume","close_time","qav","n","tbv","tqv","ignore"]
URL = "https://data.binance.vision/data/spot/daily/klines/{s}/1s/{s}-1s-{d}.zip"
def one(d):
    out = D / f"{SYM}-1s-{d}.parquet"
    if out.exists(): return d, "cached"
    z = D / f"d-{d}.zip"
    for k in range(4):
        try:
            r = requests.get(URL.format(s=SYM, d=d), timeout=120)
            if r.status_code == 200: z.write_bytes(r.content); break
            if r.status_code == 404: return d, "404"
        except Exception: time.sleep(2*(k+1))
    if not z.exists(): return d, "fail"
    zf = zipfile.ZipFile(z); df = pd.read_csv(zf.open(zf.namelist()[0]), header=None, names=COLS)
    if isinstance(df.iloc[0,0], str): df = df.iloc[1:]
    ot = pd.to_numeric(df["open_time"]); ot = ot.where(ot < 1e14, ot // 1000)
    df.index = pd.to_datetime(ot, unit="ms", utc=True); df.index.name = "time"
    df = df[["open","high","low","close","volume"]].astype(float).sort_index(); df = df[~df.index.duplicated()]
    df.to_parquet(out); z.unlink(); return d, f"ok {len(df)}"
if __name__ == "__main__":
    d0, d1 = dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3])
    days = [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1-d0).days+1)]
    with ThreadPoolExecutor(4) as ex:
        for d, s in ex.map(one, days): print(d, s, flush=True)
    print("DONE", flush=True)
