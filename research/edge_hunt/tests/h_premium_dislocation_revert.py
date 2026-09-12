"""premium_dislocation_revert (round 3)

Hypothesis: on Hyperliquid, a 1h flush (bar return <= -2.5x ATR24) whose HL
premium (mark vs oracle, stamped at the bar end) is dislocated (<= -X bps, or
fell by >= X bps over the bar) is PERP-LED (forced perp selling) and reverts as
the oracle anchors mark and funding pays the longs; a flush with an unchanged
premium is SPOT-LED and continues.

Mechanics (identical for all cells):
  signal   : close of 1h bar t (premium row stamped at bar end, floored to the hour)
  universe : every HL perp with a cached funding/premium series (50 snapshot
             coins + PIT extension in data/xsec_pit), eligible at t only if the
             trailing-24h USD volume through bar t >= $5M
  entry    : maker limit at close_t, filled only if bar t+1 trades through it by
             >= 1 tick (low_{t+1} <= limit - tick); taker arm = open_{t+1}
  exit     : open of the first bar after the premium (bar-end value) returns to
             >= -5 bps (long) / <= +5 bps (short)   -> 'norm', taker
             else time stop after H bars (open of bar t+1+H)  -> 'time', taker
             stop at entry -/+ 1.5 x flush-bar range, checked intra-bar  -> 'stop', taker
  funding  : hourly funding accrued for every hour end in (entry, exit]; folded
             into exit_px (long RECEIVES when funding < 0)
Cells: perp_led (flush & premium dislocated), spot_led (flush & premium not
dislocated), prem_only (dislocated & no flush), market_wide (>= 5 eligible
coins flushing the same hour), mirror short arm, absorption arm, BTC-hedged arm.
Walk-forward: params chosen on fold 1 (calendar third), OOS = folds 2+3.
"""
from __future__ import annotations
import json, sys, itertools, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

PIT = C.DATA / "xsec_pit"
OUT_MD = ROOT / "tests" / "h_premium_dislocation_revert.md"
OUT_JSON = ROOT / "tests" / "h_premium_dislocation_revert_result.json"
STRATEGY = "premium_dislocation_revert"
SRC = "tests/h_premium_dislocation_revert.py"
NOTIONAL = 1000.0
LIQ_USD = 5e6
FLUSH_K = 2.5
ATR_N = 24
NORM_BPS = 5.0
STOP_MULT = 1.5
MW_MIN = 5
N_SHUFFLE = 200
SEED = 7
GRID = [dict(X=X, pmode=pm, H=H) for X in (20, 30, 50) for pm in ("level", "change") for H in (6, 12, 24)]
# secondary (diagnostic) grid: coin-relative premium, lower thresholds - the specified grid is too sparse
GRID_REL = [dict(X=X, pmode="rel", H=H) for X in (10, 20, 30) for H in (6, 12, 24)]
BAR = pd.Timedelta(hours=1)

LOG = []


def log(s=""):
    print(s, flush=True); LOG.append(s)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def _read(p):
    df = pd.read_parquet(p)
    if len(df) == 0:
        return None
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    df.index = df.index.tz_convert("UTC") if df.index.tz is not None else df.index.tz_localize("UTC")
    df.index.name = "time"
    return df.sort_index()


def load_panel():
    ref = C.hl_candles("BTC", "1h")
    t0, t1 = ref.index[0], ref.index[-1]
    u = pd.read_parquet(C.DATA / "hl_universe_all.parquet").set_index("coin")
    szd = u["szDecimals"].to_dict()
    fund_files = {p.name[len("hl_funding_"):-len(".parquet")]: p for p in C.DATA.glob("hl_funding_*.parquet")}
    for p in PIT.glob("hl_funding_*.parquet"):
        fund_files.setdefault(p.name[len("hl_funding_"):-len(".parquet")], p)
    panel = {}
    skipped = []
    for coin, fp in sorted(fund_files.items()):
        cp = C.DATA / f"hl_{coin}_1h.parquet"
        if not cp.exists():
            cp = PIT / f"hl_{coin}_1h.parquet"
        if not cp.exists():
            skipped.append(coin); continue
        b = _read(cp); f = _read(fp)
        if b is None or f is None:
            skipped.append(coin); continue
        b = b[(b.index >= t0) & (b.index <= t1)]
        if len(b) < 24 * 8:
            skipped.append(coin); continue
        # regular hourly grid (gaps -> NaN, no forward fill of prices)
        idx = pd.date_range(b.index[0], b.index[-1], freq="h", tz="UTC")
        b = b.reindex(idx)
        f.index = f.index.floor("h")
        f = f[~f.index.duplicated(keep="last")]
        end_t = idx + BAR                              # bar-end stamps
        prem = f["premium"].reindex(end_t).values * 1e4   # bps at bar end
        rate = f["fundingRate"].reindex(end_t).values     # funding paid at bar end
        o, h, l, c, v = (b[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
        pc = np.concatenate([[np.nan], c[:-1]])
        tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
        tr = np.where(np.isfinite(h), tr, np.nan)
        atr = pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().shift(1).values / pc  # prior 24 bars, fraction
        ret = c / o - 1.0
        dvol = v * c
        liq24 = pd.Series(dvol).rolling(24, min_periods=20).sum().values          # through bar t (known at close t)
        medvol = pd.Series(v).rolling(24 * 7, min_periods=48).median().shift(1).values
        prem_prev = np.concatenate([[np.nan], prem[:-1]])
        # premium relative to the coin's own trailing-7d median (through the previous bar end):
        # several names carry a persistent structural premium (e.g. -50..-100 bps), which the
        # absolute-level condition would otherwise pick up as a permanent "dislocation"
        prem_rel = prem - pd.Series(prem).rolling(168, min_periods=48).median().shift(1).values
        px = np.nanmedian(c)
        sd = int(szd.get(coin, 0))
        tick = max(10 ** (math.floor(math.log10(px)) - 4), 10 ** (-(6 - sd)))
        panel[coin] = dict(idx=idx, o=o, h=h, l=l, c=c, v=v, prem=prem, dprem=prem - prem_prev, prem_rel=prem_rel, rate=rate,
                           atr=atr, ret=ret, liq24=liq24, medvol=medvol, tick=tick, n=len(idx),
                           rng=h - l, in_snap=(C.DATA / f"hl_{coin}_1h.parquet").exists())
    return panel, skipped, (t0, t1)


PANEL, SKIPPED, PERIOD = load_panel()
COINS = sorted(PANEL)
HOURS = pd.date_range(PERIOD[0], PERIOD[1], freq="h", tz="UTC")
HPOS = {t: i for i, t in enumerate(HOURS)}


def base_flags():
    """Per-coin eligibility, flush (down), spike (up) flags + market-wide flush count per hour."""
    mw = np.zeros(len(HOURS), dtype=int)
    for coin, P in PANEL.items():
        elig = np.isfinite(P["atr"]) & np.isfinite(P["ret"]) & np.isfinite(P["prem"]) & np.isfinite(P["dprem"]) & np.isfinite(P["prem_rel"]) \
            & (P["liq24"] >= LIQ_USD) & (P["atr"] > 0)
        flush = elig & (P["ret"] <= -FLUSH_K * P["atr"])
        spike = elig & (P["ret"] >= FLUSH_K * P["atr"])
        P["elig"], P["flush"], P["spike"] = elig, flush, spike
        pos = np.array([HPOS[t] for t in P["idx"]])
        mw[pos[flush]] += 1
    for P in PANEL.values():
        pos = np.array([HPOS[t] for t in P["idx"]])
        P["mw"] = mw[pos]
    return mw


MW = base_flags()
BTC = PANEL["BTC"]
RNG = np.random.default_rng(SEED)


# ---------------------------------------------------------------------------
# signal cells
# ---------------------------------------------------------------------------
def dislocated(P, X, pmode, side):
    if pmode == "level":
        return (P["prem"] <= -X) if side == 1 else (P["prem"] >= X)
    if pmode == "rel":
        return (P["prem_rel"] <= -X) if side == 1 else (P["prem_rel"] >= X)
    return (P["dprem"] <= -X) if side == 1 else (P["dprem"] >= X)


def signal_mask(P, cell, X, pmode, side):
    if cell == "perp_led":
        return (P["flush"] if side == 1 else P["spike"]) & dislocated(P, X, pmode, side)
    if cell == "spot_led":
        return (P["flush"] if side == 1 else P["spike"]) & ~dislocated(P, X, pmode, side)
    if cell == "prem_only":
        return P["elig"] & dislocated(P, X, pmode, side) & ~(P["flush"] if side == 1 else P["spike"])
    if cell == "market_wide":
        return P["flush"] & (P["mw"] >= MW_MIN)
    if cell == "market_wide_perp":
        return P["flush"] & (P["mw"] >= MW_MIN) & dislocated(P, X, pmode, 1)
    if cell == "flush_any":
        return P["flush"] if side == 1 else P["spike"]
    raise ValueError(cell)


def funding_sum(P, e, xbar_end):
    """sum of hourly funding rates at bar ends in (entry_time, exit_time]; entry at open of bar e
    = end of bar e-1, so bar ends e .. xbar_end (inclusive)."""
    r = P["rate"][e:xbar_end + 1]
    return float(np.nansum(r))


def simulate(cell, params, side=1, mode="maker", absorb=False, hedged=False, sig_override=None,
             start=None, end=None, sig_side=None):
    """sig_side: side used to build the signal (default = trade side). sig_side=+1 with side=-1 is the
    CONTINUATION arm (short the dislocated flush)."""
    X, pmode, H = params["X"], params["pmode"], params["H"]
    sig_side = side if sig_side is None else sig_side
    rows = []
    for coin, P in PANEL.items():
        if sig_override is not None:
            if coin not in sig_override:
                continue
            sig_idx = np.asarray(sorted(sig_override[coin]), dtype=int)
        else:
            sig_idx = np.flatnonzero(signal_mask(P, cell, X, pmode, sig_side))
        if len(sig_idx) == 0:
            continue
        o, h, l, c, v, prem, rng, tick, n, idx = (P[k] for k in ("o", "h", "l", "c", "v", "prem", "rng", "tick", "n", "idx"))
        busy_until = -1
        for i in sig_idx:
            e = i + 1
            R = rng[i]
            if absorb:
                # confirmation: bar t+1 closes above (below) the flush close on >= median volume; enter open t+2
                if e >= n or not np.isfinite(c[e]) or not np.isfinite(P["medvol"][e]):
                    continue
                if side == 1 and not (c[e] > c[i] and v[e] >= P["medvol"][e]):
                    continue
                if side == -1 and not (c[e] < c[i] and v[e] >= P["medvol"][e]):
                    continue
                e = i + 2
            if e >= n or e + H >= n or e < busy_until or not np.isfinite(R) or R <= 0:
                continue
            et = idx[e]
            if start is not None and not (start <= et < end):
                continue
            if not np.isfinite(o[e]) or not np.isfinite(l[e]) or not np.isfinite(h[e]):
                continue
            if mode == "maker" and not absorb:
                lim = c[i]
                if side == 1:
                    if not (l[e] <= lim - tick):
                        continue
                    if o[e] < lim:      # gap through the limit: filled at the better open
                        lim = o[e]
                else:
                    if not (h[e] >= lim + tick):
                        continue
                    if o[e] > lim:
                        lim = o[e]
                px, entry_maker = lim, True
            else:
                px, entry_maker = o[e], False
            stop = px - side * STOP_MULT * R
            reason = xpx = xbar = xt = None
            for k in range(e, e + H):
                if not np.isfinite(l[k]) or not np.isfinite(h[k]):
                    continue
                if (side == 1 and l[k] <= stop) or (side == -1 and h[k] >= stop):
                    reason, xpx, xbar, xt = "stop", stop, k, idx[k] + BAR
                    break
                pk = prem[k]
                # normalisation is defined by the SIGNAL side: a negative-premium signal is resolved when the
                # premium is back >= -5 bps (also for the continuation short), a positive one when <= +5 bps
                normal = np.isfinite(pk) and ((sig_side == 1 and pk >= -NORM_BPS) or (sig_side == -1 and pk <= NORM_BPS))
                if normal or k == e + H - 1:
                    if not np.isfinite(o[k + 1]):
                        continue
                    reason, xpx, xbar, xt = ("norm" if normal else "time"), o[k + 1], k + 1, idx[k + 1]
                    break
            if reason is None:
                continue
            busy_until = xbar + 1
            qty = NOTIONAL / px
            fees = C.hl_fee(NOTIONAL, entry_maker) + C.hl_fee(qty * xpx, False)
            # funding at bar ends in (entry, exit]: bars e .. (xbar-1 for open exits, xbar for stop exits)
            fsum = funding_sum(P, e, xbar if reason == "stop" else xbar - 1)
            fund_usd = -side * NOTIONAL * fsum          # USD received (+) / paid (-)
            raw_ret = side * (xpx / px - 1.0)
            row = dict(entry_time=et, exit_time=xt, side=side, entry_px=px, qty=qty, notional_usd=NOTIONAL,
                       instrument=coin, multiplier=1.0, reason=reason, signal_time=idx[i], hold_h=(xbar - e) + (1 if reason == "stop" else 0),
                       fees_only=fees, funding_usd=fund_usd, raw_ret=raw_ret, prem_sig=prem[i], dprem_sig=P["dprem"][i],
                       mw=int(P["mw"][i]), in_snap=bool(P["in_snap"]), liq24=float(P["liq24"][i]))
            if hedged:
                bpos = HPOS.get(et)
                be = BTC["o"][bpos] if bpos is not None and bpos < BTC["n"] else np.nan
                bxpos = HPOS.get(xt)
                bx = BTC["o"][bxpos] if bxpos is not None and bxpos < BTC["n"] else np.nan
                if not (np.isfinite(be) and np.isfinite(bx)):
                    continue
                hedge_ret = -side * (bx / be - 1.0)
                bfsum = funding_sum(BTC, bpos, (bxpos - 1) if bxpos is not None else bpos)
                bfund = side * NOTIONAL * bfsum        # short BTC receives positive funding (side=1 long alt)
                fees += 2 * C.hl_fee(NOTIONAL, False)
                tot = raw_ret + hedge_ret
                row.update(entry_px=1000.0, qty=1.0, side=1,
                           exit_px=1000.0 * (1 + tot) + (fund_usd + bfund), hedge_ret=hedge_ret)
            else:
                row["exit_px"] = xpx + side * fund_usd / qty
            row["fee_usd"] = fees
            rows.append(row)
    cols = C.REQUIRED_TRADE_COLS + ["multiplier", "reason", "signal_time", "hold_h", "fees_only", "funding_usd",
                                    "raw_ret", "prem_sig", "dprem_sig", "mw", "in_snap", "liq24"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["entry_time", "instrument"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
BOUNDS = C.fold_bounds(PERIOD, 3)


def pkey(p):
    return f"X{p['X']}_{p['pmode']}_H{p['H']}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:8.1f} pf={r['pf']:.2f} wr={r['wr']:.2f} sh={r['sharpe']:.2f} "
            f"bps={r['net_bps']:6.1f} folds={[round(x, 1) for x in r['folds']]} fold_n={r['fold_n']} maxdd={r['max_dd']:.1f} hold={r['avg_hold_min']/60:.1f}h")


def md_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)


def r1(x):
    return round(float(x), 1)


def n_hours(t):
    return int(t["signal_time"].nunique()) if len(t) else 0


def run_cell(cell, side=1, mode="maker", absorb=False, hedged=False, grid=GRID, label=None, record=True, sig_side=None):
    """Walk-forward for one cell. Returns dict with best, oos result, table rows, trades cache."""
    label = label or f"{cell}_{'long' if side == 1 else 'short'}_{mode}{'_absorb' if absorb else ''}{'_hedged' if hedged else ''}"
    cache = {}
    kw = dict(side=side, mode=mode, absorb=absorb, hedged=hedged, sig_side=sig_side)

    def all_trades(p):
        k = pkey(p)
        if k not in cache:
            cache[k] = simulate(cell, p, **kw)
        return cache[k]

    def run_fn(p, s, e):
        t = all_trades(p)
        if len(t) == 0:
            return t
        return t[(t.entry_time >= s) & (t.entry_time < e)].reset_index(drop=True)

    best, oos, table = C.walk_forward(grid, run_fn, PERIOD, n_folds=3, min_trades=10)
    res = C.oos_result(oos, PERIOD, 3)
    rows = []
    for _, tr in table.iterrows():
        p = grid[int(tr["idx"])]
        full = C.evaluate(all_trades(p), 3, PERIOD[0], PERIOD[1])
        oo = C.evaluate(run_fn(p, BOUNDS[1][0], BOUNDS[2][1]), 3, PERIOD[0], PERIOD[1])
        rows.append(dict(params=pkey(p), is_n=int(tr["is_n"]), is_net=r1(tr["is_net"]), is_pf=round(tr["is_pf"], 2),
                         is_wr=round(tr["is_wr"], 2), is_bps=r1(tr["is_net_bps"]), n_full=full["n"],
                         f1=r1(full["folds"][0]), f2=r1(full["folds"][1]), f3=r1(full["folds"][2]),
                         oos_n=oo["n"], oos_net=r1(oo["net"]), oos_pf=round(oo["pf"], 2), oos_bps=r1(oo["net_bps"]),
                         sel="*" if tr["selected"] else ""))
        if record:
            C.record_to_lab(STRATEGY, f"{label}_{pkey(p)}_full", "HL-panel", "1h", dict(p, cell=cell, side=side, mode=mode, absorb=absorb, hedged=hedged),
                            full, period=PERIOD, source=SRC,
                            notes=f"full period all 3 folds (fold 1 = in-sample); cell={cell}; PIT universe >= $5M/24h; funding incl.")
    if record:
        C.record_to_lab(STRATEGY, f"{label}_OOS", "HL-panel", "1h", dict(best or {}, cell=cell, side=side, mode=mode, absorb=absorb, hedged=hedged),
                        res, period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC,
                        notes=f"walk-forward OOS folds 2+3, params selected on fold 1; cell={cell}; funding incl.")
    log(f"\n## {label}\n\nbest (fold 1): `{best}`\n\nOOS folds 2+3: {fmt(res)}  distinct signal hours={n_hours(oos)}\n")
    log(md_table(rows, ["params", "is_n", "is_net", "is_pf", "is_wr", "is_bps", "n_full", "f1", "f2", "f3", "oos_n", "oos_net", "oos_pf", "oos_bps", "sel"]))
    if len(oos):
        by = oos.assign(net=C.add_pnl(oos)["net_pnl"]).groupby("reason").agg(n=("net", "size"), net=("net", "sum"), raw_bps=("raw_ret", lambda x: x.mean() * 1e4))
        log("\nOOS by exit reason:\n")
        log(md_table([dict(reason=k, n=int(v.n), net=r1(v.net), raw_bps=r1(v.raw_bps)) for k, v in by.iterrows()], ["reason", "n", "net", "raw_bps"]))
        log(f"\nOOS funding received total = {oos.funding_usd.sum():.2f} USD; fees only = {oos.fees_only.sum():.2f} USD")
    return dict(label=label, best=best, oos=res, oos_trades=oos, rows=rows, all_trades=all_trades, run_fn=run_fn, cell=cell, kw=kw, grid=grid)



def sanity(R, tag):
    """(a) shuffle, (c) neighbours, (d) per-coin / liquidity / universe split, fee + funding stress."""
    oos, res, best, grid, cell, kw = R["oos_trades"], R["oos"], R["best"], R["grid"], R["cell"], R["kw"]
    log(f"\n## Sanity checks: {tag} (walk-forward OOS, best={best})\n")
    log(f"OOS: {fmt(res)}; distinct signal hours = {n_hours(oos)}")
    Xs = sorted({p["X"] for p in grid}); Hs = sorted({p["H"] for p in grid})
    neigh = []
    for p in grid:
        if p["pmode"] != best["pmode"]:
            continue
        dx = abs(Xs.index(p["X"]) - Xs.index(best["X"])); dh = abs(Hs.index(p["H"]) - Hs.index(best["H"]))
        if 0 < dx + dh <= 1:
            r = C.evaluate(R["run_fn"](p, BOUNDS[1][0], BOUNDS[2][1]), 3, PERIOD[0], PERIOD[1])
            neigh.append((pkey(p), r1(r["net"]), r["n"]))
    om = [p for p in grid if p["pmode"] != best["pmode"] and p["X"] == best["X"] and p["H"] == best["H"]]
    if om:
        r = C.evaluate(R["run_fn"](om[0], BOUNDS[1][0], BOUNDS[2][1]), 3, PERIOD[0], PERIOD[1])
        neigh.append((pkey(om[0]), r1(r["net"]), r["n"]))
    n_pos = sum(1 for _, v, _ in neigh if v > 0)
    log(f"Neighbours OOS net: {neigh} -> {n_pos}/{len(neigh)} positive")
    p_sh = float("nan"); null = np.array([])
    if len(oos):
        counts = oos.groupby("instrument").size().to_dict()
        s, e = BOUNDS[1][0], BOUNDS[2][1]
        pools = {}
        for coin in counts:
            P = PANEL[coin]
            pools[coin] = np.flatnonzero(P["elig"] & (P["idx"] + BAR >= s) & (P["idx"] + BAR < e))
        nets = []
        for rep in range(N_SHUFFLE):
            ov = {}
            for coin, k in counts.items():
                pool = pools[coin]
                if len(pool) == 0:
                    continue
                # the maker fill rule / stop rejects some random hours: over-draw, then keep the first k fills
                ov[coin] = sorted(RNG.choice(pool, size=min(len(pool), 4 * k), replace=False).tolist())
            t = simulate(cell, best, sig_override=ov, start=s, end=e, **kw)
            if len(t):
                keep = []
                for coin, g in t.groupby("instrument"):
                    keep.append(g.sample(min(len(g), counts[coin]), random_state=int(RNG.integers(1 << 30))))
                t = pd.concat(keep)
            nets.append(C.evaluate(t, 3, PERIOD[0], PERIOD[1])["net"])
        null = np.array(nets)
        p_sh = float((null >= res["net"]).mean())
        log(f"Shuffle test ({N_SHUFFLE} random eligible hours, same coins/counts/params/mechanics): real={res['net']:.1f} "
            f"null mean={null.mean():.1f} sd={null.std():.1f} p(null >= real)={p_sh:.3f}")
        C.record_to_lab(STRATEGY, f"{R['label']}_SHUFFLE_null_mean", "HL-panel", "1h", dict(best, reps=N_SHUFFLE),
                        dict(C.empty_result(), n=int(res["n"]), net=float(null.mean()), folds=[0.0, 0.0, 0.0]),
                        period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC, notes=f"random-hour same-coin control; p(null>=real)={p_sh:.3f}; sd={null.std():.1f}")
        t = C.add_pnl(oos)
        pc = t.groupby("instrument")["net_pnl"].agg(["sum", "size"]).sort_values("sum")
        log("\nOOS per coin (net USD, n): " + ", ".join(f"{k}={v['sum']:.0f}({int(v['size'])})" for k, v in pc.iterrows()))
        pos_sum = t["net_pnl"][t["net_pnl"] > 0].sum()
        log(f"Top coin share of gross positive PnL: {(pc['sum'].max() / pos_sum if pos_sum > 0 else 0):.2f}; coins traded: {len(pc)}; coins net>0: {int((pc['sum'] > 0).sum())}")
        ph = t.groupby("signal_time")["net_pnl"].sum().sort_values()
        ph_t = ph.mean() / ph.std(ddof=1) * math.sqrt(len(ph)) if len(ph) > 1 and ph.std(ddof=1) > 0 else float("nan")
        log(f"OOS per signal-hour: {len(ph)} hours; best hour {ph.max():.0f} ({ph.idxmax()}), worst {ph.min():.0f} ({ph.idxmin()}); "
            f"hours net>0: {int((ph > 0).sum())}; net excluding best hour: {(t['net_pnl'].sum() - ph.max()):.1f}; "
            f"hour-level mean={ph.mean():.1f} t={ph_t:.2f} (trades in the same hour are one correlated bet)")
        for name, m in (("snapshot-50 coins", t.in_snap), ("PIT-extension coins", ~t.in_snap),
                        ("liq24 $5-20M", t.liq24 < 20e6), ("liq24 >= $20M", t.liq24 >= 20e6)):
            r = C.evaluate(t[m], 3, PERIOD[0], PERIOD[1])
            log(f"OOS {name}: {fmt(r)}")
        tt = oos.copy(); tt["fee_usd"] = tt["fee_usd"] + C.hl_fee(NOTIONAL, False) - C.hl_fee(NOTIONAL, True)
        log(f"OOS same fills charged taker fees both sides: {fmt(C.evaluate(tt, 3, PERIOD[0], PERIOD[1]))}")
        tn = oos.copy(); tn["exit_px"] = tn["exit_px"] - tn["side"] * tn["funding_usd"] / tn["qty"]
        log(f"OOS excluding funding accrual: {fmt(C.evaluate(tn, 3, PERIOD[0], PERIOD[1]))}")
        by = t.groupby("reason").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), hold=("hold_h", "mean"))
        log("OOS exit reasons: " + ", ".join(f"{k}: n={int(v.n)} net={v.net:.0f} hold={v.hold:.1f}h" for k, v in by.iterrows()))
    return dict(p_shuffle=p_sh, neigh=neigh, n_pos=n_pos, n_hours=n_hours(oos), null_mean=float(null.mean()) if len(null) else None,
                oos_n=res["n"], oos_net=res["net"], oos_pf=res["pf"], oos_folds=res["folds"])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    log(f"# premium_dislocation_revert - results\n")
    log(f"Period {PERIOD[0].date()} -> {PERIOD[1].date()}; folds start {[b[0].date().isoformat() for b in BOUNDS]}; "
        f"{len(COINS)} coins with premium series ({sum(P['in_snap'] for P in PANEL.values())} snapshot-50 + "
        f"{sum(not P['in_snap'] for P in PANEL.values())} PIT extension); skipped (no candles) = {SKIPPED}")
    n_elig = sum(int(P["elig"].sum()) for P in PANEL.values())
    n_flush = sum(int(P["flush"].sum()) for P in PANEL.values())
    n_spike = sum(int(P["spike"].sum()) for P in PANEL.values())
    log(f"Eligible coin-hours (>= $5M/24h, ATR+premium available): {n_elig}; flush bars (ret <= -2.5 ATR24): {n_flush}; "
        f"up-spikes: {n_spike}; hours with >= {MW_MIN} flushes: {int((MW >= MW_MIN).sum())}")
    prem_all = np.concatenate([P["prem"][P["elig"]] for P in PANEL.values()])
    log(f"Eligible premium bps quantiles 1/5/50/95/99: {np.round(np.nanpercentile(prem_all, [1, 5, 50, 95, 99]), 1).tolist()}; "
        f"share <= -20/-30/-50 bps: {[(round(float((prem_all <= -x).mean() * 100), 2)) for x in (20, 30, 50)]} %")

    med = {c: float(np.nanmedian(P["prem"][P["elig"]])) for c, P in PANEL.items() if P["elig"].sum() > 100}
    med = pd.Series(med).sort_values()
    log(f"Coins with a structural (median) premium <= -15 bps while eligible: {med[med <= -15].round(1).to_dict()} -> absolute-level "
        f"conditions flag these permanently; the 'rel' mode removes the coin's trailing-7d median.")
    # ---- descriptive: forward raw returns of flush bars by premium bucket (open t+1 -> open t+1+h) ----
    log("\n## Descriptive: flush bars, raw forward return (bps, open_{t+1} -> open_{t+1+h}) by premium at bar end\n")
    recs = []
    for coin, P in PANEL.items():
        for i in np.flatnonzero(P["flush"]):
            if i + 25 >= P["n"]:
                continue
            o = P["o"]
            fw = {f"r{h}": (o[i + 1 + h] / o[i + 1] - 1) * 1e4 for h in (1, 6, 12, 24)}
            recs.append(dict(coin=coin, t=P["idx"][i], prem=P["prem"][i], dprem=P["dprem"][i], prem_rel=P["prem_rel"][i], mw=P["mw"][i],
                             fold=int(C.fold_labels(pd.Series([P["idx"][i]]), 3, PERIOD[0], PERIOD[1])[0]) + 1, **fw))
    D = pd.DataFrame(recs)
    D["prem_bucket"] = pd.cut(D["prem"], [-1e9, -50, -30, -20, -10, 0, 1e9], labels=["<=-50", "-50..-30", "-30..-20", "-20..-10", "-10..0", ">0"])
    D["dprem_bucket"] = pd.cut(D["dprem"], [-1e9, -50, -30, -20, -10, 0, 1e9], labels=["<=-50", "-50..-30", "-30..-20", "-20..-10", "-10..0", ">0"])
    D["prem_rel_bucket"] = pd.cut(D["prem_rel"], [-1e9, -30, -20, -10, -5, 0, 1e9], labels=["<=-30", "-30..-20", "-20..-10", "-10..-5", "-5..0", ">0"])
    for col in ("prem_bucket", "dprem_bucket", "prem_rel_bucket"):
        g = D.groupby(col, observed=True).agg(n=("r1", "size"), r1=("r1", "mean"), r6=("r6", "mean"), r12=("r12", "mean"), r24=("r24", "mean"),
                                              med12=("r12", "median"), f1=("fold", lambda x: (x == 1).sum()), f2=("fold", lambda x: (x == 2).sum()), f3=("fold", lambda x: (x == 3).sum()))
        log(f"\nby {col}:\n")
        log(md_table([dict(bucket=k, **{c: (int(v[c]) if c in ("n", "f1", "f2", "f3") else r1(v[c])) for c in g.columns}) for k, v in g.iterrows()],
                     ["bucket", "n", "r1", "r6", "r12", "r24", "med12", "f1", "f2", "f3"]))
    # by fold x dislocated
    D["disl20"] = D["prem"] <= -20
    g = D.groupby(["fold", "disl20"]).agg(n=("r12", "size"), r6=("r6", "mean"), r12=("r12", "mean"), r24=("r24", "mean"))
    log("\nby fold x (premium <= -20 bps):\n")
    log(md_table([dict(fold=k[0], disl=k[1], n=int(v.n), r6=r1(v.r6), r12=r1(v.r12), r24=r1(v.r24)) for k, v in g.iterrows()], ["fold", "disl", "n", "r6", "r12", "r24"]))
    g = D.groupby(D["mw"] >= MW_MIN).agg(n=("r12", "size"), r6=("r6", "mean"), r12=("r12", "mean"), r24=("r24", "mean"))
    log("\nby market-wide (>= 5 flushes same hour):\n")
    log(md_table([dict(mw=k, n=int(v.n), r6=r1(v.r6), r12=r1(v.r12), r24=r1(v.r24)) for k, v in g.iterrows()], ["mw", "n", "r6", "r12", "r24"]))

    results = {}
    # ---- primary cell ----
    main_r = run_cell("perp_led", 1, "maker")
    results["perp_led_long_maker"] = main_r
    best = main_r["best"]
    # ---- taker arm of the primary ----
    results["perp_led_long_taker"] = run_cell("perp_led", 1, "taker")
    # ---- comparison cells (same grid, same mechanics) ----
    results["spot_led_long_maker"] = run_cell("spot_led", 1, "maker")
    results["prem_only_long_maker"] = run_cell("prem_only", 1, "maker")
    results["market_wide_long_maker"] = run_cell("market_wide", 1, "maker", grid=[dict(X=20, pmode="level", H=H) for H in (6, 12, 24)])
    results["market_wide_perp_long_maker"] = run_cell("market_wide_perp", 1, "maker")
    # ---- mirror short arm ----
    results["perp_led_short_maker"] = run_cell("perp_led", -1, "maker")
    # ---- absorption arm (taker at open t+2 after confirmation) ----
    results["perp_led_long_absorb"] = run_cell("perp_led", 1, "taker", absorb=True)
    # ---- BTC-hedged arm ----
    results["perp_led_long_hedged"] = run_cell("perp_led", 1, "maker", hedged=True)
    # ---- continuation arm (inverse of the hypothesis): SHORT the flush whose premium is dislocated ----
    results["perp_led_cont_short_maker"] = run_cell("perp_led", -1, "maker", sig_side=1, label="perp_led_CONTINUATION_short_maker")
    results["perp_led_cont_short_maker_rel"] = run_cell("perp_led", -1, "maker", sig_side=1, grid=GRID_REL, label="perp_led_CONTINUATION_short_maker_relprem")
    # ---- secondary diagnostic grid: coin-relative premium (7d median removed), lower thresholds ----
    log("\n# Secondary diagnostic grid (premium relative to the coin's trailing-7d median; X in 10/20/30 bps)\n")
    results["perp_led_long_maker_rel"] = run_cell("perp_led", 1, "maker", grid=GRID_REL, label="perp_led_long_maker_relprem")
    results["perp_led_long_taker_rel"] = run_cell("perp_led", 1, "taker", grid=GRID_REL, label="perp_led_long_taker_relprem")
    results["spot_led_long_maker_rel"] = run_cell("spot_led", 1, "maker", grid=GRID_REL, label="spot_led_long_maker_relprem")
    results["prem_only_long_maker_rel"] = run_cell("prem_only", 1, "maker", grid=GRID_REL, label="prem_only_long_maker_relprem")
    results["perp_led_short_maker_rel"] = run_cell("perp_led", -1, "maker", grid=GRID_REL, label="perp_led_short_maker_relprem")

    # ---- spot-led vs perp-led with the SELECTED params (same X/pmode/H) ----
    log("\n## Cell comparison at the primary's selected params (OOS folds 2+3, maker, long)\n")
    comp_rows = []
    for cell in ("perp_led", "spot_led", "prem_only", "market_wide", "market_wide_perp", "flush_any"):
        t = simulate(cell, best, 1, "maker", start=BOUNDS[1][0], end=BOUNDS[2][1])
        r = C.evaluate(t, 3, PERIOD[0], PERIOD[1])
        comp_rows.append(dict(cell=cell, n=r["n"], net=r1(r["net"]), pf=round(r["pf"], 2), wr=round(r["wr"], 2), bps=r1(r["net_bps"]),
                              f2=r1(r["folds"][1]), f3=r1(r["folds"][2]), raw_bps=r1(t.raw_ret.mean() * 1e4) if len(t) else 0))
        C.record_to_lab(STRATEGY, f"{cell}_long_maker_at_primary_params_OOS", "HL-panel", "1h", dict(best, cell=cell), r,
                        period=(BOUNDS[1][0], BOUNDS[2][1]), source=SRC, notes="cell comparison at the primary cell's fold-1 params, OOS folds 2+3")
    log(md_table(comp_rows, ["cell", "n", "net", "pf", "wr", "bps", "f2", "f3", "raw_bps"]))

    # ---- sanity checks ----
    S_main = sanity(main_r, "PRIMARY perp_led_long_maker")
    S_spot = sanity(results["spot_led_long_maker"], "spot_led_long_maker (comparison cell)")
    S_mw = sanity(results["market_wide_long_maker"], "market_wide_long_maker (comparison cell)")
    S_cont = sanity(results["perp_led_cont_short_maker"], "CONTINUATION arm: short the dislocated flush")
    p_sh, neigh, n_pos = S_main["p_shuffle"], S_main["neigh"], S_main["n_pos"]
    res = main_r["oos"]

    # ---- verdict ----
    oos_ok = res["n"] >= 60 and res["net"] > 0 and res["pf"] >= 1.2 and all(f > 0 for f in res["folds"][1:])
    shuffle_ok = (p_sh < 0.05) if np.isfinite(p_sh) else False
    neigh_ok = n_pos >= max(1, len(neigh) - 1)
    if res["net"] > 0 and oos_ok and shuffle_ok and neigh_ok:
        verdict = "edge"
    elif res["net"] > 0:
        verdict = "weak"
    else:
        verdict = "none"
    log(f"\n## Verdict: **{verdict}**  (OOS n={res['n']} net={res['net']:.1f} pf={res['pf']:.2f} folds2+3={[round(x,1) for x in res['folds'][1:]]}; "
        f"shuffle p={p_sh:.3f}; neighbours {n_pos}/{len(neigh)} positive)")

    out = dict(key=STRATEGY, best_params=best, oos_n=res["n"], oos_net=res["net"], oos_pf=res["pf"], oos_wr=res["wr"], oos_sharpe=res["sharpe"],
               oos_folds=res["folds"], verdict=verdict, shuffle_p=p_sh, neighbours=neigh,
               sanity=dict(primary=S_main, spot_led=S_spot, market_wide=S_mw, continuation=S_cont),
               cells={k: dict(best=v["best"], oos_n=v["oos"]["n"], oos_net=v["oos"]["net"], oos_pf=v["oos"]["pf"], oos_folds=v["oos"]["folds"]) for k, v in results.items()},
               comparison=comp_rows, insample=main_r["rows"])
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    OUT_MD.write_text("\n".join(LOG) + "\n")
    return out


if __name__ == "__main__":
    main()
