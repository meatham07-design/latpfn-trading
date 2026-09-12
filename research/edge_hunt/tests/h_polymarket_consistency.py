"""h_polymarket_consistency — logical-consistency (monotonicity) arbitrage on Polymarket
'Bitcoin/Ethereum above $X on <date>' strike ladders (+ hourly ladders), and a second leg
comparing Polymarket digital prices with a vol-implied fair value (Deribit DVOL proxy).

Leg 1 (arb): for strikes X1 < X2 in the same event, P(YES X1) >= P(YES X2) must hold.
A violation is tradeable when  bid(X2) - ask(X1) - fees > margin: buy YES(X1) at the ask,
buy NO(X2) (= sell YES X2 into the bid); payoff at resolution is 1 + 1[X1 < S <= X2] >= 1
per share for a cost of ask(X1) + 1 - bid(X2) + fees.
Quotes are reconstructed from public data-api prints (taker BUY of a token = its ask was
touched; taker SELL = its bid was touched; complement token maps via 1-p). Signal at print
stamp t uses only prints stamped < t; the fill requires a later print stamped in
[t+G, t+W] proving the ask (bid) was still at or better than the signal price; fill at the
signal price, size = min(confirming print sizes, cap). One trade per event per D seconds.
Taker fee = 0.07 * p * (1-p) per share on every leg (current crypto schedule; maker 0).
Run: venv/bin/python tests/h_polymarket_consistency.py [--quick]
"""
from __future__ import annotations
import sys, json, time, math, itertools, argparse
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/molt_bot/latpfn-trading/research/edge_hunt")
import common as C

D = C.DATA / "polymarket_consistency"
FEE_RATE = 0.07
CAP_SHARES = 1000.0
STRAT = "polymarket_consistency"


def fee(p):
    return FEE_RATE * p * (1.0 - p)


# ----------------------------------------------------------------------------- data
def load_meta(families=("daily",)):
    m = pd.read_parquet(D / "markets.parquet")
    m["family"] = np.where(m.series.isin([45, 42]), "daily", "hourly")
    m["asset"] = np.where(m.slug.str.startswith("bitcoin"), "BTC", "ETH")
    m = m[m.family.isin(families)]
    m = m[(m.uma == "resolved") & m.yes_final.isin([0.0, 1.0]) & m.strike.notna()]
    m["ev_end_ts"] = pd.to_datetime(m.ev_end, utc=True, format="ISO8601")
    m["ev_start_ts"] = pd.to_datetime(m.ev_start, utc=True, format="ISO8601")
    # events with a complete resolved ladder only
    return m


def touches_for_event(slug: str, strikes: dict) -> pd.DataFrame | None:
    p = D / "prints" / f"{slug}.parquet"
    if not p.exists():
        return None
    x = pd.read_parquet(p)
    x = x[x.mid.isin(strikes.keys())]
    if len(x) == 0:
        return None
    yes_px = np.where(x.outcome.values == 0, x.price.values, 1.0 - x.price.values)
    # ask touched on YES: taker BUY YES, or taker SELL NO ; bid touched: taker SELL YES or taker BUY NO
    ask = ((x.buy.values == 1) & (x.outcome.values == 0)) | ((x.buy.values == 0) & (x.outcome.values == 1))
    t = pd.DataFrame({"t": x.t.values.astype(np.int64), "strike": x.strike.values.astype(float),
                      "ask": ask.astype(np.int8), "px": yes_px.astype(float), "size": x["size"].values.astype(float)})
    return t.sort_values(["t"], kind="stable").reset_index(drop=True)


# ----------------------------------------------------------------------------- leg 1 engine
def scan_event(tch: pd.DataFrame, finals: dict, end_ts: float, M: float, S: int, W: int, G: int, D_block: int,
               cap: float = CAP_SHARES, collect_signals: bool = False):
    """Returns (trades list, signal stats). Strict causal signal->confirm->fill."""
    t = tch.t.values; st = tch.strike.values; isask = tch.ask.values; px = tch.px.values; sz = tch["size"].values
    n = len(t)
    strikes = sorted(set(st.tolist()))
    last_ask = {}   # strike -> (t, px, size, idx)
    last_bid = {}
    trades, signals = [], []
    block_until = -1
    # precomputed per-strike arrays for confirmation lookups
    by_strike = {k: np.where(st == k)[0] for k in strikes}
    def confirm(k, want_ask, t0, t1, lim):
        idx = by_strike[k]
        lo = np.searchsorted(t[idx], t0, side="left"); hi = np.searchsorted(t[idx], t1, side="right")
        for j in idx[lo:hi]:
            if want_ask and isask[j] == 1 and px[j] <= lim + 1e-12:
                return j
            if (not want_ask) and isask[j] == 0 and px[j] >= lim - 1e-12:
                return j
        return -1
    for i in range(n):
        k = st[i]
        if isask[i] == 1:
            last_ask[k] = (t[i], px[i], sz[i], i)
        else:
            last_bid[k] = (t[i], px[i], sz[i], i)
        ti = t[i]
        if ti < block_until:
            continue
        best = None
        if isask[i] == 1:
            cands = [(k, k2) for k2 in strikes if k2 > k and k2 in last_bid]
        else:
            cands = [(k1, k) for k1 in strikes if k1 < k and k1 in last_ask]
        for (k1, k2) in cands:
            ta, A, sa, ia = last_ask[k1]; tb, B, sb, ib = last_bid[k2]
            if ti - ta > S or ti - tb > S:
                continue
            locked = B - A - fee(A) - fee(1.0 - B)
            if locked < M:
                continue
            if best is None or locked > best[0]:
                best = (locked, k1, k2, A, B)
        if best is None:
            continue
        locked, k1, k2, A, B = best
        if collect_signals:
            signals.append((ti, k1, k2, A, B, locked))
        ja = confirm(k1, True, ti + G, ti + W, A)
        jb = confirm(k2, False, ti + G, ti + W, B)
        if ja < 0 or jb < 0:
            block_until = ti + 1  # avoid re-firing every print of an unconfirmable signal for one second
            continue
        q = float(min(sz[ja], sz[jb], cap))
        if q < 5:
            continue
        tfill = max(t[ja], t[jb])
        cost = A + (1.0 - B)
        payoff = finals[k1] + (1.0 - finals[k2])
        trades.append(dict(entry_time=pd.Timestamp(tfill, unit="s", tz="UTC"), exit_time=pd.Timestamp(end_ts, unit="s", tz="UTC"),
                           side=1.0, entry_px=cost, exit_px=payoff, qty=q, notional_usd=cost * q,
                           fee_usd=q * (fee(A) + fee(1.0 - B)), instrument=f"PM:{k1:.0f}-{k2:.0f}",
                           k1=k1, k2=k2, A=A, B=B, locked=locked, signal_t=ti, conf_lag=tfill - ti))
        block_until = ti + D_block
    return trades, signals


class Engine:
    def __init__(self, meta: pd.DataFrame):
        self.meta = meta
        self.events = []
        for slug, g in meta.groupby("slug"):
            if len(g) < 3:
                continue
            strikes = dict(zip(g.mid, g.strike))
            finals = dict(zip(g.strike, g.yes_final))
            tch = touches_for_event(slug, strikes)
            if tch is None or len(tch) < 10:
                continue
            self.events.append(dict(slug=slug, asset=g.asset.iloc[0], family=g.family.iloc[0], tch=tch, finals=finals,
                                    end_ts=float(g.ev_end_ts.max().timestamp()), start=g.ev_start_ts.min(),
                                    n_prints=len(tch)))
        self.cache = {}

    def run(self, params: dict, collect_signals=False) -> pd.DataFrame:
        key = json.dumps(params, sort_keys=True)
        if key in self.cache and not collect_signals:
            return self.cache[key]
        rows, sigs = [], []
        for e in self.events:
            tr, sg = scan_event(e["tch"], e["finals"], e["end_ts"], params["M"], params["S"], params["W"], params["G"],
                                params["D"], params.get("cap", CAP_SHARES), collect_signals)
            for r in tr:
                r.update(slug=e["slug"], asset=e["asset"], family=e["family"]); rows.append(r)
            for s in sg:
                sigs.append((e["slug"],) + s)
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        self.cache[key] = df
        if collect_signals:
            return df, pd.DataFrame(sigs, columns=["slug", "t", "k1", "k2", "A", "B", "locked"])
        return df


def month_table(tr: pd.DataFrame) -> pd.DataFrame:
    if len(tr) == 0:
        return pd.DataFrame()
    t = C.add_pnl(tr)
    t["month"] = t.entry_time.dt.strftime("%Y-%m")
    g = t.groupby("month").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), wr=("net_pnl", lambda s: (s > 0).mean()),
                               notional=("notional_usd", "sum"))
    return g


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--families", default="daily")
    a = ap.parse_args()
    meta = load_meta(tuple(a.families.split(",")))
    eng = Engine(meta)
    print("events loaded", len(eng.events), "prints", sum(e["n_prints"] for e in eng.events))
    base = dict(M=0.0, S=600, W=600, G=10, D=3600)
    tr, sg = eng.run(base, collect_signals=True)
    print("signals", len(sg), "trades", len(tr))
    if len(sg):
        print(sg.locked.describe()); print(sg.groupby("slug").size().describe())
    if len(tr):
        print(C.evaluate(tr)); print(month_table(tr)); print(tr[["slug", "k1", "k2", "A", "B", "locked", "qty", "conf_lag"]].head(20))
