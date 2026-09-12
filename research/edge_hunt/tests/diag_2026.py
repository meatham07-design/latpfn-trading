"""Why did 2026 die? Split the recent sample by listing type, size and funding."""
import os, sys, json, re
os.environ["NOLAB"]="1"
from pathlib import Path
import numpy as np, pandas as pd
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import h_hl_listing_drift as T, common as C
UTC=lambda s: pd.Timestamp(s,tz="UTC")
BEST=dict(rule="short_after",N=24,H=7,hedge=True)
evs,btc,_,_=T.load_binance_events()
rows=[]
for ev in evs:
    t=T.rule_trade(ev,BEST,btc,True)
    if not t: continue
    t["day1_qv"]=ev.day1_qv; t["fresh"]=ev.flags.get("fresh"); t["t0"]=ev.t0
    rows.append(t)
df=C.add_pnl(pd.DataFrame(rows)); df["yr"]=df.entry_time.dt.year
df["bps"]=1e4*df.net_pnl/T.NOTIONAL
# equity/commodity-linked perps Binance listed from 2026 (ticker is a stock/ETF, not a token)
STOCKS=set("AAPL AMZN AMD NVDA TSLA MSFT META GOOGL GOOG NFLX COIN MSTR HOOD PLTR SPY QQQ GLD SLV BABA INTC AVGO ORCL CRCL IBIT MARA RIOT SMCI ARM UBER DIS BAC JPM XOM WMT".split())
def kind(s):
    b=T.base_asset(s,"binance")
    if b in STOCKS: return "equity-linked"
    if b.startswith("USD") or b in ("FDUSD","TUSD","DAI","EURI","USDC","USD1"): return "stable"
    return "crypto"
df["kind"]=df.instrument.map(kind)
print("### net by year x kind (bps/trade, n)")
piv=df.pivot_table(index="yr",columns="kind",values="bps",aggfunc=["mean","count"])
print(piv.round(1).to_string())
print("\n### 2026 only")
d=df[df.yr==2026]
for k,g in d.groupby("kind"):
    print(f"  {k:14s} n={len(g):3d} net={g.net_pnl.sum():8.1f} mean={g.bps.mean():7.1f} bps median={g.bps.median():7.1f}")
print(f"  ALL 2026       n={len(d):3d} net={d.net_pnl.sum():8.1f} mean={d.bps.mean():7.1f} bps")
c=d[d.kind=="crypto"]
print(f"\n2026 crypto-only: n={len(c)} net={c.net_pnl.sum():.1f} pf={C.evaluate(c,1)['pf']:.2f} funding={c.funding.sum():.0f} alt={c.alt_gross.sum():.0f} hedge={c.hedge_pnl.sum():.0f} fees={-c.fee_usd.sum():.0f}")
print("\n### crypto-only, by year")
cr=df[df.kind=="crypto"]
for y,g in cr.groupby("yr"):
    print(f"  {y} n={len(g):3d} net={g.net_pnl.sum():9.1f} mean={g.bps.mean():7.1f} bps  funding={1e4*g.funding.mean()/T.NOTIONAL:7.1f} bps  alt={1e4*g.alt_gross.mean()/T.NOTIONAL:7.1f} bps")
print("\n### 2026 crypto split by day-1 volume quartile")
c2=cr[cr.yr==2026].copy(); c2["q"]=pd.qcut(c2.day1_qv,4,labels=["Q1 thin","Q2","Q3","Q4 thick"])
for q,g in c2.groupby("q",observed=True):
    print(f"  {q:9s} n={len(g):3d} median day1 ${g.day1_qv.median()/1e6:7.1f}M  net={g.net_pnl.sum():8.1f} mean={g.bps.mean():7.1f} bps")
print("\n### fresh vs established, crypto only, by year")
for y,g in cr.groupby("yr"):
    f=g[g.fresh]; e=g[~g.fresh]
    print(f"  {y} fresh n={len(f):3d} {f.bps.mean():7.1f} bps | established n={len(e):3d} {e.bps.mean() if len(e) else float('nan'):7.1f} bps")
print("\n### listings per year by kind")
print(df.groupby(["yr","kind"]).size().unstack(fill_value=0).to_string())
