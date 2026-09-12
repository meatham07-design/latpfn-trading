"""Is there a version of the listing-drift short that is still alive in 2026 and
worth capital?  Filters are CHOSEN ON DATA THROUGH 2024 ONLY and then tested on
2025 and 2026 separately.  10 bps/side slippage on all four legs throughout.
"""
import os, sys, json
os.environ["NOLAB"]="1"
from pathlib import Path
import numpy as np, pandas as pd
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import h_hl_listing_drift as T, common as C
NOT=T.NOTIONAL; FEE=T.FEE_SIDE["binance"]; SLIP=10/1e4
STOCKS=set("AAPL AMZN AMD NVDA TSLA MSFT META GOOGL GOOG NFLX COIN MSTR HOOD PLTR SPY QQQ GLD SLV BABA INTC AVGO ORCL CRCL IBIT MARA RIOT SMCI ARM UBER DIS BAC JPM XOM WMT".split())
L=[]
def P(*a):
    s=" ".join(str(x) for x in a); print(s); L.append(s)

evs,btc,_,_=T.load_binance_events()
rows=[]
for ev in evs:
    k=ev.bars; ie,ix=24,24+168
    if ix>=len(k) or (k.index[ix]-k.index[ie])!=pd.Timedelta(hours=168): continue
    te,tx=k.index[ie],k.index[ix]
    pe,px=float(k["open"].iloc[ie])*(1-SLIP), float(k["open"].iloc[ix])*(1+SLIP)
    be,bx=T._px_at(btc,te),T._px_at(btc,tx)
    if not (pe>0 and px>0 and np.isfinite(be) and np.isfinite(bx)): continue
    be,bx=be*(1+SLIP),bx*(1-SLIP)
    qty=NOT/pe; alt=-(px-pe)*qty
    fr=ev.fund; fs=float(fr[(fr.index>te)&(fr.index<=tx)].sum()) if len(fr) else 0.0
    fund=fs*NOT
    hp=(bx-be)*(NOT/be)
    fee=FEE*(NOT+qty*px)+FEE*(NOT+NOT*bx/be)
    b=T.base_asset(ev.sym,"binance")
    rows.append(dict(sym=ev.sym, t=te, yr=te.year, net=alt+fund+hp-fee, alt=alt, fund=fund, hedge=hp, fee=fee,
                     day1_qv=ev.day1_qv, qv_entry=float(k["quote_volume"].iloc[ie]),
                     qv_exit=float(k["quote_volume"].iloc[ix]),
                     kind=("equity-linked" if b in STOCKS else "crypto")))
d=pd.DataFrame(rows); d["bps"]=1e4*d.net/NOT
d["cap1"]=d[["qv_entry","qv_exit"]].min(axis=1)*0.01
P("# Deployable? — listing short at h24, 7d hold, BTC-hedged, 10 bps/side slippage\n")
P(f"all events n={len(d)} net=${d.net.sum():,.0f}\n")

TRAIN=d[d.yr<=2024]; 
P("## Filters chosen on 2020-2024 only\n")
P("| filter | train n | train bps | 2025 n | 2025 bps | 2025 net | 2026 n | 2026 bps | 2026 net |")
P("|---|---|---|---|---|---|---|---|---|")
def row(lbl, m):
    tr=TRAIN[m(TRAIN)]; y5=d[(d.yr==2025)&m(d)]; y6=d[(d.yr==2026)&m(d)]
    P(f"| {lbl} | {len(tr)} | {tr.bps.mean():.0f} | {len(y5)} | {y5.bps.mean():.0f} | {y5.net.sum():.0f} | "
      f"{len(y6)} | {y6.bps.mean() if len(y6) else float('nan'):.0f} | {y6.net.sum():.0f} |")
    return dict(train_n=len(tr), train_bps=float(tr.bps.mean()), y2025_n=len(y5), y2025_net=float(y5.net.sum()),
                y2026_n=len(y6), y2026_bps=float(y6.bps.mean()) if len(y6) else None, y2026_net=float(y6.net.sum()))
out={}
q75=TRAIN.day1_qv.quantile(.75); q50=TRAIN.day1_qv.quantile(.50)
out["all"]=row("no filter", lambda x: pd.Series(True,index=x.index))
out["crypto"]=row("crypto only (no stock perps)", lambda x: x.kind=="crypto")
out["q50"]=row(f"crypto & day-1 vol > ${q50/1e6:.0f}M (train median)", lambda x: (x.kind=="crypto")&(x.day1_qv>q50))
out["q75"]=row(f"crypto & day-1 vol > ${q75/1e6:.0f}M (train p75)", lambda x: (x.kind=="crypto")&(x.day1_qv>q75))
out["cap"]=row("crypto & 1%-hour capacity > $10k", lambda x: (x.kind=="crypto")&(x.cap1>10_000))

P("\n## Capacity and realistic $ P&L of the surviving filters (2026 only)\n")
for lbl,m in [("crypto only", lambda x:x.kind=="crypto"),
              (f"crypto & day1>${q75/1e6:.0f}M", lambda x:(x.kind=="crypto")&(x.day1_qv>q75))]:
    y6=d[(d.yr==2026)&m(d)]
    if not len(y6): continue
    for tgt in (10_000, 25_000, 50_000):
        size=np.minimum(tgt, y6.cap1.values)
        P(f"- {lbl}, target ${tgt:,}/event: n={len(y6)}, avg size ${size.mean():,.0f}, "
          f"2026 net ${(y6.net.values*size/NOT).sum():,.0f} (${(y6.net.values*size/NOT).sum()/7:,.0f}/month over 7 months)")
P("\n## Loss-tail shape (crypto, 2025 vs 2026)\n")
for y in (2025,2026):
    g=d[(d.yr==y)&(d.kind=="crypto")]
    P(f"- {y}: n={len(g)} win rate {float((g.net>0).mean()):.2f}, median {g.bps.median():.0f} bps, mean {g.bps.mean():.0f} bps, "
      f"p05 {g.bps.quantile(.05):.0f}, p01 {g.bps.quantile(.01):.0f}, worst {g.bps.min():.0f} bps")
P("\n## Would a stop help? (cap each trade's loss at X bps, crypto only)\n")
for y in (2025,2026):
    g=d[(d.yr==y)&(d.kind=="crypto")]
    line=[f"- {y}: raw {g.bps.mean():.0f} bps"]
    for cap in (500,1000,2000):
        line.append(f"stop@-{cap}bps -> {np.maximum(g.bps.values,-cap).mean():.0f}")
    P("  ".join(line) + "   (a stop cannot be executed at exactly that level; upper bound only)")
Path("diag_deployable.md").write_text("\n".join(L)+"\n")
Path("diag_deployable.json").write_text(json.dumps(out,indent=1,default=str))
