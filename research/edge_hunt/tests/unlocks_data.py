"""Data layer for h_token_unlocks: DefiLlama cliff-unlock events + Binance UM perp
daily klines / funding (data.binance.vision monthly zips, public, cached).
Everything cached under data/unlocks/.  Public read-only endpoints only.
"""
from __future__ import annotations
import io, json, re, sys, time, zipfile
from pathlib import Path
import numpy as np, pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

U = C.DATA / "unlocks"
UM = U / "um"; UM.mkdir(exist_ok=True, parents=True)
S = requests.Session()
VISION = "https://data.binance.vision/data/futures/um/monthly"


# ---------------------------------------------------------------- tickers ----
def ticker_maps():
    gecko = {c["id"]: c["symbol"].upper() for c in json.load(open(U / "gecko_coins_list.json"))}
    prot = json.load(open(U / "llama_protocols.json"))
    by_pid = {str(p["id"]): (p.get("symbol") or "").upper() for p in prot}
    by_slug = {p["slug"]: (p.get("symbol") or "").upper() for p in prot}
    by_gecko = {p["gecko_id"]: (p.get("symbol") or "").upper() for p in prot if p.get("gecko_id")}
    chains = {c["gecko_id"]: (c.get("tokenSymbol") or "").upper() for c in json.load(open(U / "llama_chains.json")) if c.get("gecko_id")}
    chain_by_name = {c["name"].lower(): (c.get("tokenSymbol") or "").upper() for c in json.load(open(U / "llama_chains.json"))}
    return gecko, by_pid, by_slug, by_gecko, chains, chain_by_name


def um_symbols() -> list[str]:
    x = (U / "um_symbols_s3.xml").read_text()
    return sorted(set(re.findall(r"monthly/klines/([A-Z0-9]+)/", x)))


def resolve_symbol(slug, d, maps):
    gecko, by_pid, by_slug, by_gecko, chains, chain_by_name = maps
    g = d.get("gecko_id")
    cands = []
    if g:
        for m in (gecko, by_gecko, chains):
            if m.get(g): cands.append(m[g])
    for pid in d.get("defillamaIds") or []:
        if by_pid.get(str(pid)): cands.append(by_pid[str(pid)])
    if by_slug.get(slug): cands.append(by_slug[slug])
    nm = (d.get("name") or "").lower()
    if chain_by_name.get(nm): cands.append(chain_by_name[nm])
    t = (d.get("metadata") or {}).get("ticker")
    if t: cands.append(str(t).upper())
    cands = [c for c in cands if c and c != "-"]
    return cands[0] if cands else None


def um_symbol_for(sym: str, ums: set[str]) -> str | None:
    for pre in ("", "1000", "1000000", "1M"):
        s = f"{pre}{sym}USDT"
        if s in ums: return s
    return None


# ----------------------------------------------------------------- events ----
def build_events(min_pct=0.0, verbose=True) -> pd.DataFrame:
    """One row per (protocol, UTC date) cliff unlock. pct_circ = cliff tokens /
    circulating supply (documented cumulative unlocked excl. noncirculating
    labels) at the END of the day BEFORE the unlock."""
    out = U / "events_all.parquet"
    if out.exists():
        return pd.read_parquet(out)
    maps = ticker_maps(); ums = set(um_symbols())
    rows = []
    for f in sorted((U / "protocols").glob("*.json")):
        slug = f.stem
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict) or "documentedData" not in d:
            continue
        noncirc = set((d.get("categories") or {}).get("noncirculating") or [])
        # daily cumulative unlocked per label
        series = {}
        for lab in d["documentedData"]["data"]:
            s = pd.Series({pd.Timestamp(x["timestamp"], unit="s", tz="UTC").normalize(): float(x.get("unlocked") or 0) for x in lab["data"]})
            s = s[~s.index.duplicated(keep="last")].sort_index()
            series[lab["label"]] = s
        if not series:
            continue
        cum = pd.DataFrame(series).ffill().fillna(0.0)
        circ = cum[[c for c in cum.columns if c not in noncirc]].sum(axis=1)
        total = cum.sum(axis=1)
        daily_inc = total.diff()
        ev = (d.get("metadata") or {}).get("events") or []
        cliffs = [e for e in ev if e.get("unlockType") == "cliff" and e.get("noOfTokens")]
        if not cliffs:
            continue
        sym = resolve_symbol(slug, d, maps)
        df = pd.DataFrame([dict(ts=int(e["timestamp"]), tokens=float(sum(e["noOfTokens"])), category=e.get("category") or "Uncategorized") for e in cliffs])
        df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.normalize()
        g = df.groupby("date")
        agg = pd.DataFrame({"tokens_all": g["tokens"].sum(),
                            "tokens_circ": df[df["category"] != "noncirculating"].groupby("date")["tokens"].sum(),
                            "n_cliffs": g.size(),
                            "cats": g["category"].agg(lambda x: ",".join(sorted(set(x))))}).fillna({"tokens_circ": 0.0})
        for dt, r in agg.iterrows():
            prev = dt - pd.Timedelta(days=1)
            c_prev = float(circ.asof(prev)) if len(circ) and prev >= circ.index[0] else np.nan
            t_prev = float(total.asof(prev)) if len(total) and prev >= total.index[0] else np.nan
            # baseline linear daily emission over the prior 30d (median of positive daily increments)
            win = daily_inc[(daily_inc.index < dt) & (daily_inc.index >= dt - pd.Timedelta(days=31))]
            base = float(win[win > 0].median()) if (win > 0).any() else 0.0
            rows.append(dict(slug=slug, name=d.get("name"), gecko_id=d.get("gecko_id"), symbol=sym,
                             um_symbol=um_symbol_for(sym, ums) if sym else None,
                             date=dt, tokens_all=float(r["tokens_all"]), tokens_circ=float(r["tokens_circ"]),
                             n_cliffs=int(r["n_cliffs"]), cats=r["cats"], circ_prev=c_prev, total_prev=t_prev,
                             pct_circ=(float(r["tokens_circ"]) / c_prev * 100 if c_prev and c_prev > 0 else np.nan),
                             pct_all=(float(r["tokens_all"]) / c_prev * 100 if c_prev and c_prev > 0 else np.nan),
                             base_daily=base, max_supply=(d.get("supplyMetrics") or {}).get("maxSupply")))
    E = pd.DataFrame(rows).sort_values(["date", "slug"]).reset_index(drop=True)
    E.to_parquet(out)
    if verbose:
        print("events", len(E), "protocols", E.slug.nunique(), "with symbol", E.symbol.notna().sum(), "with um", E.um_symbol.notna().sum())
    return E


# --------------------------------------------------------- binance vision ----
def _get_zip_csv(url, cache: Path, cols):
    if cache.exists():
        if cache.stat().st_size == 0:
            return None
        return pd.read_parquet(cache)
    for k in range(4):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404:
                cache.touch(); return None
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            raw = z.read(z.namelist()[0]).decode()
            df = pd.read_csv(io.StringIO(raw), header=None)
            if isinstance(df.iloc[0, 0], str) and not str(df.iloc[0, 0]).lstrip("-").isdigit():
                df = df.iloc[1:].reset_index(drop=True)
            df = df.iloc[:, :len(cols)]; df.columns = cols
            df.to_parquet(cache); time.sleep(0.25)
            return df
        except Exception as e:
            time.sleep(2 * (k + 1))
    raise RuntimeError(url)


KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "tbv", "tbqv", "ignore"]
FCOLS = ["calc_time", "funding_interval_hours", "last_funding_rate"]


def um_klines_month(sym, ym: str) -> pd.DataFrame | None:
    df = _get_zip_csv(f"{VISION}/klines/{sym}/1d/{sym}-1d-{ym}.zip", UM / f"k_{sym}_{ym}.parquet", KCOLS)
    if df is None or len(df) == 0: return None
    df = df.astype({c: float for c in ["open", "high", "low", "close", "volume", "quote_volume", "trades"]})
    ot = df["open_time"].astype("int64")
    ot = np.where(ot > 1e14, ot // 1000, ot)  # microseconds since 2025 for some files
    df["time"] = pd.to_datetime(ot, unit="ms", utc=True)
    return df.set_index("time")[["open", "high", "low", "close", "volume", "quote_volume", "trades"]]


def um_funding_month(sym, ym: str) -> pd.DataFrame | None:
    df = _get_zip_csv(f"{VISION}/fundingRate/{sym}/{sym}-fundingRate-{ym}.zip", UM / f"f_{sym}_{ym}.parquet", FCOLS)
    if df is None or len(df) == 0: return None
    ct = df["calc_time"].astype("int64")
    ct = np.where(ct > 1e14, ct // 1000, ct)
    df["time"] = pd.to_datetime(ct, unit="ms", utc=True)
    df["rate"] = df["last_funding_rate"].astype(float)
    return df.set_index("time")[["rate"]]


def months_between(a: pd.Timestamp, b: pd.Timestamp) -> list[str]:
    p = pd.period_range(a.to_period("M"), b.to_period("M"), freq="M")
    return [str(x) for x in p]


def um_panel(sym, start: pd.Timestamp, end: pd.Timestamp):
    """Daily klines + funding for [start, end], fetched by month, cached."""
    ks, fs = [], []
    for ym in months_between(start, end):
        k = um_klines_month(sym, ym)
        if k is not None: ks.append(k)
        f = um_funding_month(sym, ym)
        if f is not None: fs.append(f)
    K = pd.concat(ks).sort_index() if ks else None
    F = pd.concat(fs).sort_index() if fs else None
    if K is not None: K = K[~K.index.duplicated(keep="last")]
    if F is not None: F = F[~F.index.duplicated(keep="last")]
    return K, F


def btc_daily() -> pd.DataFrame:
    p = C.DATA / "binance_spot_1d" / "BTCUSDT.parquet"
    return pd.read_parquet(p)


if __name__ == "__main__":
    E = build_events()
    print(E.tail())
