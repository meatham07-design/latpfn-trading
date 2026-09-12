"""Fetch yfinance bars -> data/yf_{sym}_{interval}.parquet."""
import json, sys, time
from pathlib import Path
import pandas as pd, yfinance as yf
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, sanitize_symbol

DATA.mkdir(exist_ok=True)
SYMS = ["MNQ=F", "MES=F", "MYM=F", "MGC=F", "MBT=F", "M2K=F", "ES=F", "NQ=F", "GC=F", "CL=F",
        "BTC-USD", "ETH-USD", "SPY", "QQQ", "^VIX"]
FIVE_MIN = [s for s in SYMS if s.endswith("=F") or s in ("BTC-USD", "ETH-USD")]
PLAN = {"1h": dict(period="730d"), "1d": dict(period="10y"), "5m": dict(period="60d")}
problems = []

def fetch(sym, interval, kw, tries=4):
    for k in range(tries):
        try:
            df = yf.download(sym, interval=interval, auto_adjust=False, progress=False, threads=False, **kw)
            if df is None or len(df) == 0:
                raise RuntimeError("empty")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.rename(columns={c: c.lower() for c in df.columns})
            out = df[["open", "high", "low", "close", "volume"]].astype(float)
            idx = pd.to_datetime(out.index)
            idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
            out.index = idx; out.index.name = "time"
            out = out[~out.index.duplicated(keep="last")].sort_index().dropna(subset=["close"])
            return out
        except Exception as e:
            print(f"retry {sym} {interval} {k}: {e}", flush=True)
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"failed {sym} {interval}")

if __name__ == "__main__":
    for sym in SYMS:
        for iv, kw in PLAN.items():
            if iv == "5m" and sym not in FIVE_MIN: continue
            try:
                df = fetch(sym, iv, kw)
                df.to_parquet(DATA / f"yf_{sanitize_symbol(sym)}_{iv}.parquet")
                print(f"{sym} {iv} rows={len(df)} {df.index[0]} -> {df.index[-1]}", flush=True)
            except Exception as e:
                problems.append(f"{sym} {iv}: {e!r}"); print("ERR", sym, iv, e, flush=True)
            time.sleep(1)
    (DATA / "_yf_problems.json").write_text(json.dumps(problems, indent=1))
    print("DONE problems:", problems)
