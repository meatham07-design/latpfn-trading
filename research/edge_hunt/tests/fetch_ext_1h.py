"""Fetch 1h candles (one candleSnapshot call each, public read-only) for coins in
hl_universe_all.parquet that are NOT in the main cache. Stored under data/hl_ext/
so the main cache / list_hl_coins() are untouched. Used by h_flush_reversal_long.py
to build a point-in-time top-50 universe by trailing-30d USD volume."""
import sys, time, json
from pathlib import Path
import pandas as pd, requests
sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C
EXT = C.DATA / 'hl_ext'; EXT.mkdir(exist_ok=True)
S = requests.Session()
def post(body, tries=5):
    for k in range(tries):
        try:
            r = S.post(C.HL_INFO_URL, json=body, timeout=60)
            if r.status_code == 429: time.sleep(2 + 2 * k); continue
            r.raise_for_status(); return r.json()
        except Exception:
            if k == tries - 1: raise
            time.sleep(1.5 * (k + 1))
u = pd.read_parquet(C.DATA / 'hl_universe_all.parquet')
cached = set(C.list_hl_coins()); probs = []
todo = [c for c in u.coin if c not in cached and not (EXT / f'hl_{c}_1h.parquet').exists()]
print('to fetch', len(todo), flush=True)
now = int(time.time() * 1000)
for coin in todo:
    try:
        raw = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": 0, "endTime": now}})
        if not raw: probs.append(f'{coin}: empty'); continue
        df = pd.DataFrame(raw)
        out = pd.DataFrame({"open": df["o"].astype(float).values, "high": df["h"].astype(float).values,
                            "low": df["l"].astype(float).values, "close": df["c"].astype(float).values,
                            "volume": df["v"].astype(float).values, "trades": df["n"].astype(float).values},
                           index=pd.DatetimeIndex(pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)))
        out.index.name = 'time'; out = out[~out.index.duplicated(keep='last')].sort_index()
        if int(df["T"].iloc[-1]) > now: out = out.iloc[:-1]
        out.to_parquet(EXT / f'hl_{coin}_1h.parquet')
        print(coin, len(out), out.index[0], flush=True)
    except Exception as e:
        probs.append(f'{coin}: {e!r}'); print('ERR', coin, e, flush=True)
    time.sleep(0.25)
(EXT / '_problems.json').write_text(json.dumps(probs, indent=1))
print('DONE', probs)
