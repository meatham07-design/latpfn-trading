"""Fetch Binance SPOT daily klines for every USDT pair in exchangeInfo (incl.
delisted / BREAK) from 2018-11-01 -> now via the data-api.binance.vision mirror
(api.binance.com and fapi.binance.com return HTTP 451 from this region).
Cache: data/binance_spot_1d/<SYMBOL>.parquet ; merged panel: data/binance_panel_1d.parquet
"""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "binance_spot_1d"; CACHE.mkdir(exist_ok=True)
PANEL = ROOT / "data" / "binance_panel_1d.parquet"
BASE = "https://data-api.binance.vision/api/v3"
START = int(pd.Timestamp("2018-11-01", tz="UTC").timestamp() * 1000)
STABLES = {"USDC","BUSD","TUSD","USDP","PAX","DAI","FDUSD","USDS","USDSB","EUR","GBP","AUD","USD1","BRL","TRY",
           "RUB","UAH","BIDR","IDRT","NGN","VAI","UST","USTC","SUSD","AEUR","EURI","XUSD","USDE","RLUSD","PYUSD",
           "BKRW","ZAR","FRAX","LUSD","GUSD","USDD","WBTC","WBETH","BETH","WETH","STETH","BNSOL","BFUSD","USDY","USDTB"}
LEV_SUFFIX = ("UP", "DOWN", "BULL", "BEAR")

def wanted(s):
    if s["quoteAsset"] != "USDT": return False
    b = s["baseAsset"]
    if b in STABLES: return False
    if any(b.endswith(x) and len(b) > len(x) for x in LEV_SUFFIX) and b not in ("SUN","MOON"):  # leveraged tokens
        # keep genuine names like 'BEAR'? none exist as base; guard loosely
        return False
    return True

def fetch(sym):
    out = CACHE / f"{sym}.parquet"
    if out.exists():
        return sym, "cached"
    rows = []; st = START
    for _ in range(20):
        for att in range(6):
            try:
                r = requests.get(f"{BASE}/klines", params=dict(symbol=sym, interval="1d", startTime=st, limit=1000), timeout=30)
                if r.status_code in (429, 418):
                    time.sleep(10 * (att + 1)); continue
                r.raise_for_status(); data = r.json(); break
            except Exception as e:
                time.sleep(2 * (att + 1)); data = None
        if not data: break
        rows += data
        if len(data) < 1000: break
        st = data[-1][0] + 1
    if not rows:
        pd.DataFrame(columns=["open","high","low","close","volume","quote_volume","trades"]).to_parquet(out)
        return sym, "empty"
    df = pd.DataFrame(rows, columns=["t","open","high","low","close","volume","ct","quote_volume","trades","tbv","tbqv","ig"])
    df["time"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.set_index("time")[["open","high","low","close","volume","quote_volume","trades"]].astype(float)
    df = df[~df.index.duplicated()].sort_index()
    df.to_parquet(out)
    return sym, f"{len(df)} rows {df.index[0].date()}->{df.index[-1].date()}"

if __name__ == "__main__":
    info = requests.get(f"{BASE}/exchangeInfo", timeout=120).json()["symbols"]
    syms = sorted(s["symbol"] for s in info if wanted(s))
    (ROOT / "data" / "binance_symbols.json").write_text(json.dumps(
        {s["symbol"]: dict(base=s["baseAsset"], status=s["status"]) for s in info if wanted(s)}, indent=0))
    print("symbols:", len(syms), flush=True)
    done = 0
    with ThreadPoolExecutor(6) as ex:
        futs = [ex.submit(fetch, s) for s in syms]
        for f in as_completed(futs):
            sym, msg = f.result(); done += 1
            if done % 50 == 0 or msg == "empty": print(done, sym, msg, flush=True)
    # merge panel (long format)
    parts = []
    for p in sorted(CACHE.glob("*.parquet")):
        d = pd.read_parquet(p)
        if len(d) == 0: continue
        d = d.reset_index(); d["symbol"] = p.stem; parts.append(d)
    panel = pd.concat(parts, ignore_index=True)
    panel.to_parquet(PANEL)
    print("panel", panel.shape, panel["symbol"].nunique(), panel["time"].min(), panel["time"].max(), flush=True)
