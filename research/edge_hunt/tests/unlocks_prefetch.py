import sys, time, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/Users/molt_bot/latpfn-trading/research/edge_hunt/tests")
import unlocks_data as D
E = pd.read_parquet(D.U / "events_all.parquet")
E.loc[E.slug == "ton", "um_symbol"] = "TONUSDT"
E.loc[E.slug == "arbitrum-exchange", "um_symbol"] = None
H = E[E.um_symbol.notna() & (E.date >= "2021-01-01") & (E.date <= "2026-08-20") & (E.pct_circ >= 0.5)]
pairs = set()
for s, d in zip(H.um_symbol, H.date):
    for k in (-1, 0):
        pairs.add((s, (d + pd.DateOffset(months=k)).strftime("%Y-%m")))
    if d.day >= 24:
        pairs.add((s, (d + pd.DateOffset(months=1)).strftime("%Y-%m")))
pairs = sorted(pairs); print("pairs", len(pairs), flush=True)
def job(p):
    s, ym = p
    try:
        D.um_klines_month(s, ym); D.um_funding_month(s, ym)
        return "ok"
    except Exception as e:
        return f"ERR {s} {ym} {e}"
done = 0
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(job, pairs):
        done += 1
        if r != "ok": print(r, flush=True)
        if done % 100 == 0: print(done, flush=True)
print("DONE", flush=True)
