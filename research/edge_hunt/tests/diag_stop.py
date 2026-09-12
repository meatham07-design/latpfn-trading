"""Does a hard stop rescue the listing short?  Intrabar-simulated on the hourly
bars: short at h24, stop = entry*(1+x) triggered by any hour's HIGH, otherwise
cover at h24+168.  Fill at the stop level (or the bar open if it gaps through),
plus slippage.  BTC hedge unwound at the same hour.
"""
import os, sys, json
os.environ["NOLAB"]="1"
from pathlib import Path
import numpy as np, pandas as pd
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import h_hl_listing_drift as T, common as C
NOT=T.NOTIONAL; FEE=T.FEE_SIDE["binance"]
STOCKS=set("AAPL AMZN AMD NVDA TSLA MSFT META GOOGL GOOG NFLX COIN MSTR HOOD PLTR SPY QQQ GLD SLV BABA INTC AVGO ORCL CRCL IBIT MARA RIOT SMCI ARM UBER DIS BAC JPM XOM WMT".split())
L=[]
def P(*a):
    s=" ".join(str(x) for x in a); print(s); L.append(s)
evs,btc,_,_=T.load_binance_events()

def book(stop_pct=None, slip_bps=10.0, crypto_only=True, hold=168, ient=24):
    s=slip_bps/1e4; rows=[]
    for ev in evs:
        b=T.base_asset(ev.sym,"binance")
        if crypto_only and b in STOCKS: continue
        k=ev.bars; ix=ient+hold
        if ix>=len(k) or (k.index[ix]-k.index[ient])!=pd.Timedelta(hours=hold): continue
        te=k.index[ient]; pe=float(k["open"].iloc[ient])
        if not pe>0: continue
        pe_f=pe*(1-s)
        i_exit, px_raw, stopped = ix, float(k["open"].iloc[ix]), False
        if stop_pct is not None:
            lvl=pe_f*(1+stop_pct)
            seg=k.iloc[ient+1:ix+1]
            hit=np.nonzero((seg["high"].values>=lvl))[0]
            if len(hit):
                j=ient+1+hit[0]
                px_raw=max(lvl, float(k["open"].iloc[j]))   # gap-through fills at the open
                i_exit, stopped = j, True
        tx=k.index[i_exit]
        px_f=px_raw*(1+s)
        be,bx=T._px_at(btc,te),T._px_at(btc,tx)
        if not (np.isfinite(be) and np.isfinite(bx)): continue
        be_f,bx_f=be*(1+s),bx*(1-s)
        qty=NOT/pe_f; alt=-(px_f-pe_f)*qty
        fr=ev.fund; fs=float(fr[(fr.index>te)&(fr.index<=tx)].sum()) if len(fr) else 0.0
        fund=fs*NOT
        hp=(bx_f-be_f)*(NOT/be_f)
        fee=FEE*(NOT+qty*px_f)+FEE*(NOT+NOT*bx_f/be_f)
        rows.append(dict(sym=ev.sym,t=te,yr=te.year,net=alt+fund+hp-fee,stopped=stopped,
                         hold_h=i_exit-ient, day1_qv=ev.day1_qv,
                         cap1=min(float(k["quote_volume"].iloc[ient]),float(k["quote_volume"].iloc[i_exit]))*0.01))
    d=pd.DataFrame(rows); d["bps"]=1e4*d.net/NOT
    return d

P("# Does a stop rescue it?  (crypto listings only, 10 bps/side slippage)\n")
P("| stop | n | stopped% | total net | bps/trade | 2023 | 2024 | 2025 | 2026 | worst trade bps |")
P("|---|---|---|---|---|---|---|---|---|---|")
res={}
for lbl,sp in [("none",None),("+30%",0.30),("+50%",0.50),("+75%",0.75),("+100%",1.00),("+150%",1.50)]:
    d=book(stop_pct=sp)
    yr=d.groupby("yr").net.sum()
    P(f"| {lbl} | {len(d)} | {100*d.stopped.mean():.0f}% | {d.net.sum():.0f} | {d.bps.mean():.0f} | "
      + " | ".join(f"{yr.get(y,0):.0f}" for y in (2023,2024,2025,2026)) + f" | {d.bps.min():.0f} |")
    res[lbl]=dict(n=len(d), net=float(d.net.sum()), bps=float(d.bps.mean()),
                  by_year={int(y):float(v) for y,v in yr.items()}, worst_bps=float(d.bps.min()),
                  stopped_share=float(d.stopped.mean()))

P("\n## At realistic size (each event capped at 1% of the thinner of entry/exit hour volume)\n")
P("| stop | target/event | 2025 net | 2026 net | 2026 avg size |")
P("|---|---|---|---|---|")
for lbl,sp in [("none",None),("+50%",0.50),("+100%",1.00)]:
    d=book(stop_pct=sp)
    for tgt in (10_000,25_000):
        out={}
        for y in (2025,2026):
            g=d[d.yr==y]; size=np.minimum(tgt,g.cap1.values)
            out[y]=(float((g.net.values*size/NOT).sum()), float(size.mean()))
        P(f"| {lbl} | ${tgt:,} | {out[2025][0]:,.0f} | {out[2026][0]:,.0f} | ${out[2026][1]:,.0f} |")
        res.setdefault("scaled",{})[f"{lbl}@{tgt}"]=dict(y2025=out[2025][0], y2026=out[2026][0])

P("\n## Distribution with a +50% stop\n")
d=book(stop_pct=0.50)
for y in sorted(d.yr.unique()):
    g=d[d.yr==y]
    P(f"- {y}: n={len(g):3d} win {float((g.net>0).mean()):.2f} median {g.bps.median():6.0f} mean {g.bps.mean():6.0f} "
      f"p05 {g.bps.quantile(.05):7.0f} worst {g.bps.min():7.0f} stopped {100*g.stopped.mean():.0f}% median hold {g.hold_h.median():.0f}h")
Path("diag_stop.md").write_text("\n".join(L)+"\n")
Path("diag_stop.json").write_text(json.dumps(res,indent=1,default=str))
