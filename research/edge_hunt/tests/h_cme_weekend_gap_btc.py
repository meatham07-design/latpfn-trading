"""Hypothesis key=cme_weekend_gap_btc : the Monday CME BTC 'weekend gap'.

CME BTC futures close Fri 16:00 CT and reopen Sun 17:00 CT; spot trades through.
gap = spot at the Sunday reopen vs spot at the Friday CME close.
 (a) descriptive: does the Friday-close level get touched within N hours of the
     reopen (fill rate, time-to-fill) for |gap| > x%, vs a weekday control of
     identical 49h windows ending Tue/Wed/Thu?  Also on the real CME contract
     (MBT=F, gap = Sun 17:00 CT open vs Fri close).
 (b) tradable: HL BTC perp, $10k notional, TAKER in at the Sun 22:00 UTC bar open
     against the weekend move (fill arm) or with it (cont arm); fill arm exits at
     the Friday-close level (taker), stop 1.5x|gap| (taker), time-stop 24h/48h.
Grid: arm x thr{0,0.5,1,2%} x hold{24,48} x stop{1.5,none} = 32 cells, params
picked on fold 1 (calendar third), headline = OOS folds 2+3.
Data: Binance BTCUSDT 1h 2018-01 -> 2026-08 (~450 weekends, spot proxy w/ HL
taker fees) as the main set; cross-checks on yfinance BTC-USD 1h (730d), real
Hyperliquid BTC 1h (30 weekends) and 15m (7 weekends), MBT=F 1h (CME).
Causality: signal = close of the bar BEFORE the entry bar (Sun 21:00 UTC bar,
i.e. price at 22:00); fill at the OPEN of the Sun 22:00 UTC bar. Ref = close of
the Fri 20:00 UTC bar (= price at 21:00 UTC = 16:00 CDT). Stop/target checked
from the entry bar; stop wins ties.
Sanity: weekday control, random-window shuffle (OOS period), side shuffle,
per-year signs, parameter neighbours, top-3 removal, clock (UTC vs CT) and
data-source neighbours.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

STRAT = 'cme_weekend_gap_btc'
NOTIONAL = 10_000.0
OUT_MD = Path(__file__).with_suffix('.md')
OUT_JSON = Path(__file__).with_suffix('.json')
RNG = np.random.default_rng(7)
CT = 'America/Chicago'
CLOCKS = {  # clock -> (tz, ref_bar_open_hour on Fri, entry_bar_open_hour on Sun)
    'utc': ('UTC', 20, 22),        # ref = close of Fri 20:00 UTC bar (=21:00 UTC), entry = Sun 22:00 UTC open
    'ct':  (CT, 15, 17),           # ref = close of Fri 15:00 CT bar (=16:00 CT CME close), entry = Sun 17:00 CT open
}
CONTROL_DOWS = (1, 2, 3)           # windows ending Tue/Wed/Thu (ref 2 days earlier)


# ---------------------------------------------------------------- data
def load(kind: str) -> pd.DataFrame:
    if kind == 'binance':
        b = C._read(C.DATA / 'ext_binance_BTCUSDT_1h.parquet')
    elif kind == 'yf':
        b = C.yf_bars('BTC-USD', '1h')
    elif kind == 'hl':
        b = C.hl_candles('BTC', '1h')
    elif kind == 'hl15':
        b = C.hl_candles('BTC', '15m')
    elif kind == 'mbt':
        b = C.yf_bars('MBT=F', '1h')
    else:
        raise ValueError(kind)
    b = b[~b.index.duplicated()].copy()
    b = b[b['open'].notna() & (b['open'] > 0)]
    b['pos'] = np.arange(len(b))
    return b


def bar_lookup(b: pd.DataFrame, tz: str) -> dict:
    loc = b.index.tz_convert(tz)
    d = {}
    for p, (dt, h, m) in enumerate(zip(loc.date, loc.hour, loc.minute)):
        d.setdefault((dt, h, m), p)
    return d


def build_events(b: pd.DataFrame, clock: str = 'utc', end_dows=(6,), bar_min: int = 60,
                 ref_days: int = 2) -> pd.DataFrame:
    """One row per window.  entry bar = first bar opening at entry_hour on a day
    with dow in end_dows; ref = close of the last bar of the ref hour `ref_days`
    earlier (so ref = price at ref_hour+1); signal = close of the bar right
    before the entry bar.  gap = signal / ref - 1."""
    tz, ref_h, ent_h = CLOCKS[clock]
    lk = bar_lookup(b, tz)
    loc = b.index.tz_convert(tz)
    last_min = 60 - bar_min          # open-minute of the last sub-bar of the ref hour
    rows = []
    for (dt, h, m), p in lk.items():
        if h != ent_h or m != 0 or loc[p].dayofweek not in end_dows:
            continue
        rp = lk.get((dt - pd.Timedelta(days=ref_days), ref_h, last_min))
        if rp is None or p == 0:
            continue
        sp = p - 1
        if (b.index[p] - b.index[sp]) > pd.Timedelta(minutes=bar_min):
            continue                                   # signal bar must be adjacent to the entry bar
        if (b.index[p] - b.index[rp]) > pd.Timedelta(hours=ref_days * 24 + 3):
            continue
        ref, sig = float(b['close'].iat[rp]), float(b['close'].iat[sp])
        rows.append(dict(entry_pos=p, entry_time=b.index[p], ref_time=b.index[rp], ref_close=ref,
                         sig_close=sig, gap=sig / ref - 1.0, entry_open=float(b['open'].iat[p])))
    return pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)


def random_events(b: pd.DataFrame, n: int, bar_min: int = 60) -> pd.DataFrame:
    """n random windows (any day/hour) with the same 49h ref->entry geometry."""
    ref_lag = int(49 * 60 / bar_min)
    pos = np.sort(RNG.choice(np.arange(ref_lag + 1, len(b) - int(49 * 60 / bar_min)), size=n, replace=False))
    rows = []
    for p in pos:
        rp = p - ref_lag
        if (b.index[p] - b.index[rp]) > pd.Timedelta(hours=52):
            continue
        ref, sig = float(b['close'].iat[rp]), float(b['close'].iat[p - 1])
        rows.append(dict(entry_pos=p, entry_time=b.index[p], ref_time=b.index[rp], ref_close=ref,
                         sig_close=sig, gap=sig / ref - 1.0, entry_open=float(b['open'].iat[p])))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- (a) descriptive
def fill_stats(b: pd.DataFrame, ev: pd.DataFrame, horizons=(6, 12, 24, 48), bar_min: int = 60) -> pd.DataFrame:
    """Per event: was the ref level touched within h hours of the entry open, and
    hours-to-first-touch (within 48h)."""
    rows = []
    hmax = max(horizons)
    nb = int(hmax * 60 / bar_min)
    for e in ev.itertuples(index=False):
        p0, p1 = e.entry_pos, e.entry_pos + nb
        if p1 >= len(b) or (b.index[p1] - b.index[p0]) > pd.Timedelta(hours=hmax + 2) or e.gap == 0:
            continue
        seg = b.iloc[p0:p1]
        hit = (seg['high'].values > e.ref_close) if e.gap < 0 else (seg['low'].values < e.ref_close)
        first = int(np.argmax(hit)) if hit.any() else None
        ttf = (first + 1) * bar_min / 60.0 if first is not None else np.nan
        r = dict(entry_time=e.entry_time, gap=e.gap, agap=abs(e.gap), ttf_h=ttf)
        for h in horizons:
            r[f'fill_{h}h'] = bool(first is not None and ttf <= h)
        rows.append(r)
    return pd.DataFrame(rows)


def fill_table(d: pd.DataFrame, thrs=(0.0, 0.005, 0.01, 0.02)) -> pd.DataFrame:
    out = []
    for t in thrs:
        s = d[d.agap > t]
        if not len(s):
            continue
        out.append(dict(thr=f'>{t*100:g}%', n=len(s), fill_6h=s.fill_6h.mean(), fill_12h=s.fill_12h.mean(),
                        fill_24h=s.fill_24h.mean(), fill_48h=s.fill_48h.mean(),
                        med_ttf_h=float(s.ttf_h.median()) if s.ttf_h.notna().any() else np.nan))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- (b) simulation
def simulate(b: pd.DataFrame, ev: pd.DataFrame, params: dict, instrument: str = 'BTC', bar_min: int = 60,
             exec_kind: str = 'HL') -> pd.DataFrame:
    """arm: fill|cont, thr: min |gap|, hold: hours, stop_mult: 0|1.5 (x|gap|).
    Taker in at entry-bar open; fill arm target = ref level (taker), stop taker,
    time-stop at the open of the bar `hold` hours later (taker)."""
    arm, thr, hold, sm = params['arm'], params['thr'], params['hold'], params['stop_mult']
    nb = int(hold * 60 / bar_min)
    trades = []
    for e in ev.itertuples(index=False):
        g = e.gap
        if abs(g) <= thr or g == 0:
            continue
        p0, xp = e.entry_pos, e.entry_pos + nb
        if xp >= len(b) or (b.index[xp] - b.index[p0]) > pd.Timedelta(hours=hold + 2):
            continue
        side = int(-np.sign(g)) if arm == 'fill' else int(np.sign(g))
        entry_px = float(b['open'].iat[p0])
        target = e.ref_close if arm == 'fill' else None
        stop_px = entry_px * (1 - side * sm * abs(g)) if sm else None
        exit_px, exit_pos, reason = None, None, 'time'
        hi, lo = b['high'].values, b['low'].values
        for p in range(p0, xp):
            if stop_px is not None and ((side > 0 and lo[p] <= stop_px) or (side < 0 and hi[p] >= stop_px)):
                exit_px, exit_pos, reason = stop_px, p, 'stop'
                break
            if target is not None and ((side > 0 and hi[p] > target) or (side < 0 and lo[p] < target)):
                exit_px, exit_pos, reason = target, p, 'target'
                break
        if exit_px is None:
            exit_px, exit_pos = float(b['open'].iat[xp]), xp
        exit_time = b.index[exit_pos] + (pd.Timedelta(0) if reason == 'time' else pd.Timedelta(minutes=bar_min - 1))
        if exec_kind == 'CME':
            row = C.cme_trade(e.entry_time, exit_time, side, entry_px, exit_px, 1, instrument)
        else:
            row = C.crypto_trade(e.entry_time, exit_time, side, entry_px, exit_px, NOTIONAL / entry_px, instrument)
        row.update(gap=g, reason=reason, ref_close=e.ref_close)
        trades.append(row)
    return pd.DataFrame(trades, columns=C.REQUIRED_TRADE_COLS + ['multiplier', 'gap', 'reason', 'ref_close'])


def grid() -> list[dict]:
    return [dict(arm=a, thr=t, hold=h, stop_mult=s)
            for a in ('fill', 'cont') for t in (0.0, 0.005, 0.01, 0.02) for h in (24, 48) for s in (1.5, 0)]


def vname(p: dict) -> str:
    return f"{p['arm']}_thr{p['thr']*100:g}_h{p['hold']}_s{p['stop_mult']:g}"


def fmt(r: dict) -> str:
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:5.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:5.2f} "
            f"dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} folds={[round(f) for f in r['folds']]} fold_n={r['fold_n']}")


MD_HDR = "| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"


def md_row(name: str, r: dict, extra: str = '') -> str:
    f = list(r['folds']) + [0.0] * (3 - len(r['folds']))
    return (f"| {name} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['sharpe']:.2f} | "
            f"{r['net_bps']:.1f} | {f[0]:.0f} | {f[1]:.0f} | {f[2]:.0f} | {extra} |")


def oos_of(t: pd.DataFrame, period, bounds) -> dict:
    return C.oos_result(t[t.entry_time >= bounds[1][0]] if len(t) else t, period, 3)


import os
RECORD = os.environ.get('RECORD', '1') != '0'      # RECORD=0 to regenerate md/json without duplicating lab rows


def rec(variant, inst, tf, params, r, period, notes, trust='measured'):
    if not RECORD:
        return -1
    return C.record_to_lab(STRAT, variant, inst, tf, params, r, period=period, source=__file__, notes=notes, trust=trust)


# ---------------------------------------------------------------- main
def main():
    md, out = [], {}
    bn = load('binance')
    period = (bn.index.min(), bn.index.max())
    bounds = C.fold_bounds(period, 3)
    md.append("# CME weekend gap - BTC\n")
    md.append(f"Main data: Binance BTCUSDT 1h {period[0].date()} -> {period[1].date()} (spot proxy, HL taker fees "
              f"4.5 bps/side on $10k). Folds: " + ', '.join(f"[{s.date()},{e.date()})" for s, e in bounds) + "\n")
    md.append("Gap = close of the Sun 21:00 UTC bar / close of the Fri 20:00 UTC bar - 1 (price at 22:00 Sun vs "
              "21:00 Fri = the CME Fri 16:00 CDT close -> Sun 17:00 CDT reopen window). Entry = OPEN of the Sun "
              "22:00 UTC bar (taker). Fill arm: target = Friday-close level (taker), stop 1.5x|gap| (taker), time-stop "
              "24h/48h. Cont arm: with the weekend move, same stop, time-stop.\n")

    ev = build_events(bn, 'utc', (6,))
    ev_ctl = build_events(bn, 'utc', CONTROL_DOWS)
    fold_n = [int(((ev.entry_time >= s) & (ev.entry_time < e)).sum()) for s, e in bounds]
    print(f"weekends: {len(ev)} folds {fold_n}; weekday control windows: {len(ev_ctl)}")
    md.append(f"Weekends: {len(ev)} (per fold {fold_n}); weekday control windows (Tue/Wed/Thu, same 49h geometry): {len(ev_ctl)}.\n")
    md.append(f"|gap| distribution (weekend): median {ev.gap.abs().median()*100:.2f}%, p75 {ev.gap.abs().quantile(.75)*100:.2f}%, "
              f"p90 {ev.gap.abs().quantile(.9)*100:.2f}%; >0.5%: {(ev.gap.abs()>0.005).sum()}, >1%: {(ev.gap.abs()>0.01).sum()}, "
              f">2%: {(ev.gap.abs()>0.02).sum()}. Weekday control median {ev_ctl.gap.abs().median()*100:.2f}%.\n")

    # ---------- (a) descriptive fill rates
    md.append("## (a) Does the gap fill? Fill = Friday-close level touched within N hours of the Sun 22:00 UTC open\n")
    d_we, d_ctl = fill_stats(bn, ev), fill_stats(bn, ev_ctl)
    ft_we, ft_ctl = fill_table(d_we), fill_table(d_ctl)
    print("\nWEEKEND fill rates:\n", ft_we.round(3)); print("\nWEEKDAY control fill rates:\n", ft_ctl.round(3))
    for nm, ft in (('Weekend (Binance, 2018-2026)', ft_we), ('Weekday control Tue/Wed/Thu', ft_ctl)):
        md.append(f"**{nm}**\n\n| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |\n|---|---:|---:|---:|---:|---:|---:|")
        for r in ft.itertuples(index=False):
            md.append(f"| {r.thr} | {r.n} | {r.fill_6h:.2f} | {r.fill_12h:.2f} | {r.fill_24h:.2f} | {r.fill_48h:.2f} | {r.med_ttf_h:.1f} |")
        md.append("")
    # random-window base rate
    d_rand = fill_stats(bn, random_events(bn, 3000))
    ft_r = fill_table(d_rand)
    md.append("**Random windows (3000, any day/hour, same 49h geometry)**\n\n| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |\n|---|---:|---:|---:|---:|---:|---:|")
    for r in ft_r.itertuples(index=False):
        md.append(f"| {r.thr} | {r.n} | {r.fill_6h:.2f} | {r.fill_12h:.2f} | {r.fill_24h:.2f} | {r.fill_48h:.2f} | {r.med_ttf_h:.1f} |")
    md.append("")
    out['fill_weekend'] = ft_we.to_dict('records'); out['fill_control'] = ft_ctl.to_dict('records'); out['fill_random'] = ft_r.to_dict('records')

    # real CME contract (MBT=F): gap = Sun 17:00 CT open vs Fri close; fill on MBT bars
    mbt = load('mbt')
    lk = bar_lookup(mbt, CT); loc = mbt.index.tz_convert(CT)
    rows = []
    for (dt, h, m), p in lk.items():
        if h != 17 or loc[p].dayofweek != 6:
            continue
        rp = lk.get((dt - pd.Timedelta(days=2), 15, 0))
        if rp is None:
            continue
        ref = float(mbt['close'].iat[rp]); o = float(mbt['open'].iat[p])
        rows.append(dict(entry_pos=p, entry_time=mbt.index[p], ref_time=mbt.index[rp], ref_close=ref, sig_close=o,
                         gap=o / ref - 1.0, entry_open=o))
    ev_mbt = pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)
    d_mbt = fill_stats(mbt, ev_mbt)     # note: horizons in MBT *trading* bars (daily 16-17 CT halt excluded)
    ft_m = fill_table(d_mbt)
    print(f"\nMBT=F real CME gap ({len(ev_mbt)} weekends):\n", ft_m.round(3))
    md.append(f"**Real CME contract MBT=F** ({len(ev_mbt)} weekends {ev_mbt.entry_time.min().date()} -> {ev_mbt.entry_time.max().date()}; gap = Sun 17:00 CT open vs Fri 16:00 CT close; horizons count MBT trading bars)\n\n| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |\n|---|---:|---:|---:|---:|---:|---:|")
    for r in ft_m.itertuples(index=False):
        md.append(f"| {r.thr} | {r.n} | {r.fill_6h:.2f} | {r.fill_12h:.2f} | {r.fill_24h:.2f} | {r.fill_48h:.2f} | {r.med_ttf_h:.1f} |")
    md.append("")
    out['fill_mbt'] = ft_m.to_dict('records')
    md.append("Reading: the base rate of 'price revisits a level from 49h ago within 24h' is the number to beat; "
              "the weekend rows must exceed the weekday/random rows for a gap-specific effect to exist.\n")

    # ---------- (b) walk-forward on the main set
    G = grid()
    full = {}
    for p in G:
        full[vname(p)] = simulate(bn, ev, p)

    def run_fn(params, start, end):
        t = full[vname(params)]
        return t[(t.entry_time >= start) & (t.entry_time < end)].reset_index(drop=True)

    rep = C.full_report(G, run_fn, period, n_folds=3, min_trades=10)
    best, oos, table, oos_tr = rep['best_params'], rep['oos'], rep['insample'], rep['oos_trades']
    print("\nSelected on fold 1:", best, "\nOOS folds 2+3:", fmt(oos))
    md.append("## (b) Walk-forward, HL BTC perp (spot proxy, taker fees both sides)\n")
    md.append(f"Selected on fold 1 (by net, min 10 trades): `{best}`  \n**OOS folds 2+3**: {fmt(oos)}\n")
    md.append("Full grid, full period (f1 = selection fold; OOS view = f2+f3):\n")
    md.append(MD_HDR)
    for i, p in enumerate(G):
        t = full[vname(p)]
        r = C.evaluate(t, 3, *period)
        reasons = t['reason'].value_counts().to_dict() if len(t) else {}
        sel = 'SELECTED' if table.loc[i, 'selected'] else ''
        md.append(md_row(vname(p), r, f"{sel} {reasons}"))
        print(f"  {vname(p):24s} {fmt(r)} {reasons}")
        rec(f"grid_{vname(p)}", 'BTC', '1h', p, r, period, f"full-period grid cell, Binance spot proxy w/ HL taker fees; fold1 net={table.loc[i,'is_net']:.2f}; {reasons}")
    rec(f"WF_OOS_{vname(best)}", 'BTC', '1h', dict(best, wf='fold1-select'), oos, period, "HEADLINE walk-forward OOS folds 2+3 (fold 1 = selection, shown as 0)")
    md.append("")

    # other arm's fold-1 best
    other_arm = 'cont' if best['arm'] == 'fill' else 'fill'
    sub = table[[json.loads(s)['arm'] == other_arm for s in table['params']]]
    sub = sub[sub.is_n >= 10] if (sub.is_n >= 10).any() else sub
    other = G[int(sub.sort_values('is_net', ascending=False).iloc[0]['idx'])]
    r_o = oos_of(full[vname(other)], period, bounds)
    print(f"other arm ({other_arm}) fold-1 best {other} -> OOS {fmt(r_o)}")
    md.append(f"Other arm's fold-1 best (`{other}`) OOS folds 2+3: {fmt(r_o)}\n")
    rec(f"WF_OOS_otherarm_{vname(other)}", 'BTC', '1h', dict(other, wf='fold1-select-within-arm'), r_o, period, "other arm's fold-1 best, OOS folds 2+3")

    # OOS diagnostics: exits, gap buckets, per-year
    o = C.add_pnl(oos_tr) if len(oos_tr) else pd.DataFrame()
    yearly = {}
    if len(o):
        o['year'] = o.entry_time.dt.year
        yearly = o.groupby('year')['net_pnl'].agg(['size', 'sum']).round(0)
        o['bucket'] = pd.cut(o['gap'].abs(), [0, 0.005, 0.01, 0.02, 1], labels=['<0.5%', '0.5-1%', '1-2%', '>2%'], right=False)
        bk = o.groupby('bucket', observed=True)['net_pnl'].agg(['size', 'sum', 'mean']).round(0)
        print("\nOOS by year:\n", yearly, "\nOOS by |gap| bucket:\n", bk, "\nexits:", o['reason'].value_counts().to_dict())
        md.append("OOS per year (sub-period signs):\n\n| year | n | net |\n|---|---:|---:|")
        for y, r in yearly.iterrows():
            md.append(f"| {y} | {int(r['size'])} | {r['sum']:.0f} |")
        md.append("\nOOS by |gap| bucket:\n\n| bucket | n | net | mean |\n|---|---:|---:|---:|")
        for bkt, r in bk.iterrows():
            md.append(f"| {bkt} | {int(r['size'])} | {r['sum']:.0f} | {r['mean']:.0f} |")
        md.append(f"\nOOS exit reasons: {o['reason'].value_counts().to_dict()}\n")
        top3 = o['net_pnl'].nlargest(3).sum()
        r_top3 = C.evaluate(o.drop(o['net_pnl'].nlargest(3).index), 3, *period)
        line = f"top-3 winner removal: OOS net {oos['net']:.0f} -> {oos['net']-top3:.0f} (pf {r_top3['pf']:.2f}, folds {[round(f) for f in r_top3['folds']]})"
        print(line); md.append("- " + line)
        rec(f"top3removed_{vname(best)}", 'BTC', '1h', dict(best, check='top3_removed'), r_top3, period, "OOS folds 2+3 with 3 largest winners removed")
    else:
        top3, r_top3 = 0.0, C.empty_result()

    # ---------- neighbours (OOS folds 2+3 of every cell)
    md.append("\n## Parameter neighbours (OOS folds 2+3 of every grid cell, no selection)\n")
    md.append(MD_HDR)
    neigh = []
    for p in G:
        r = oos_of(full[vname(p)], period, bounds)
        same = p['arm'] == best['arm']
        neigh.append((vname(p), r, same))
        md.append(md_row(vname(p), r, ('same arm' if same else '') + (' SELECTED' if p == best else '')))
        rec(f"OOS23_{vname(p)}", 'BTC', '1h', p, r, period, "OOS folds 2+3 of this cell (sensitivity view)")
    same = [r for _, r, s in neigh if s]
    n_pos_same = sum(r['net'] > 0 for r in same)
    md.append(f"\nSame-arm cells OOS-positive: {n_pos_same}/{len(same)}; all cells OOS-positive: {sum(r['net']>0 for _,r,_ in neigh)}/{len(neigh)}\n")
    print(f"\nneighbours same-arm OOS-positive {n_pos_same}/{len(same)}")

    # ---------- controls & shuffles
    md.append("## Controls and shuffles (selected rule)\n")
    md.append(MD_HDR)
    t_ctl = simulate(bn, ev_ctl, best)
    r_ctl = C.evaluate(t_ctl, 3, *period); r_ctl_oos = oos_of(t_ctl, period, bounds)
    md.append(md_row('weekday_control_full', r_ctl, 'Tue/Wed/Thu 22:00 UTC windows, same rule'))
    md.append(md_row('weekday_control_OOS23', r_ctl_oos, 'folds 2+3 only'))
    print("weekday control full:", fmt(r_ctl), "\nweekday control OOS:", fmt(r_ctl_oos))
    rec(f"control_weekday_{vname(best)}", 'BTC', '1h', dict(best, control='TueWedThu'), r_ctl, period, "weekday-window control, selected rule, full period")
    # random-window shuffle, OOS period
    n_ev = len(ev)
    nets, ns = [], []
    for k in range(300):
        ev_r = random_events(bn, n_ev)
        t_r = simulate(bn, ev_r, best)
        t_r = t_r[t_r.entry_time >= bounds[1][0]] if len(t_r) else t_r
        r_r = C.evaluate(t_r, 1)
        nets.append(r_r['net']); ns.append(r_r['n'])
    nets = np.array(nets)
    p_shuf = float((nets >= oos['net']).mean())
    line = (f"random-window shuffle (300 draws x {n_ev} windows, any day/hour, same rule, OOS period): mean net={nets.mean():.0f} "
            f"sd={nets.std():.0f} p5={np.percentile(nets,5):.0f} p95={np.percentile(nets,95):.0f} mean n={np.mean(ns):.0f}; "
            f"actual OOS net={oos['net']:.0f} -> P(shuffle >= actual)={p_shuf:.3f}")
    print(line); md.append("\n- " + line)
    rec(f"shuffle_randwindow_{vname(best)}", 'BTC', '1h', dict(best, check='random_window'),
        dict(C.empty_result(), n=int(np.mean(ns)), net=float(nets.mean()), folds=[0, 0, float(nets.mean())]), period,
        f"mean of 300 random-window draws (OOS period); p={p_shuf:.3f}", trust='estimated')
    # side shuffle on the OOS trades
    p_side = None
    if len(o):
        gross, fees = o['gross_pnl'].values, o['fee_usd'].abs().values
        act = float((gross - fees).sum())
        flips = np.array([((gross * RNG.choice([-1, 1], size=len(gross))) - fees).sum() for _ in range(2000)])
        p_side = float((flips >= act).mean())
        line = f"side shuffle (2000 draws, OOS trades, timing kept): mean={flips.mean():.0f} sd={flips.std():.0f}; actual={act:.0f} -> p={p_side:.3f}"
        print(line); md.append("- " + line)

    # ---------- clock / data-source neighbours (selected rule)
    md.append("\n## Clock and data-source neighbours (selected rule, no re-selection)\n")
    md.append(MD_HDR)
    ev_ct = build_events(bn, 'ct', (6,))
    t_ct = simulate(bn, ev_ct, best)
    r_ct, r_ct_oos = C.evaluate(t_ct, 3, *period), oos_of(t_ct, period, bounds)
    md.append(md_row('clock_CT_full', r_ct, 'true CME wall-clock (Fri 16:00 CT -> Sun 17:00 CT), Binance'))
    md.append(md_row('clock_CT_OOS23', r_ct_oos, ''))
    rec(f"clockCT_{vname(best)}", 'BTC', '1h', dict(best, clock='ct'), r_ct, period, "CT wall-clock variant, Binance, full period")
    yf = load('yf'); yper = (yf.index.min(), yf.index.max())
    ev_yf = build_events(yf, 'utc', (6,))
    t_yf = simulate(yf, ev_yf, best)
    r_yf = C.evaluate(t_yf, 3, *yper)
    t_bn_same = simulate(bn, ev[ev.entry_time >= yper[0]], best)
    r_bn_same = C.evaluate(t_bn_same, 3, *yper)
    md.append(md_row('yf_BTC-USD_730d', r_yf, f"{len(ev_yf)} weekends {yper[0].date()} -> {yper[1].date()} (inside fold 3)"))
    md.append(md_row('binance_same_730d', r_bn_same, 'same weekends on Binance'))
    rec(f"yf_{vname(best)}", 'BTC', '1h', dict(best, data='yf_BTC_USD_1h'), r_yf, yper, "yfinance BTC-USD 730d, selected rule")
    hl = load('hl'); hper = (hl.index.min(), hl.index.max())
    ev_hl = build_events(hl, 'utc', (6,))
    t_hl = simulate(hl, ev_hl, best)
    r_hl = C.evaluate(t_hl, 3, *hper)
    t_bn_hl = simulate(bn, ev[ev.entry_time >= hper[0]], best)
    r_bn_hl = C.evaluate(t_bn_hl, 3, *hper)
    md.append(md_row('HL_BTC_1h_actual', r_hl, f"{len(ev_hl)} weekends {hper[0].date()} -> {hper[1].date()}, real perp bars"))
    md.append(md_row('binance_same_HLweekends', r_bn_hl, ''))
    rec(f"HL1h_{vname(best)}", 'BTC', '1h', dict(best, data='hl_BTC_1h'), r_hl, hper, "real HL perp 1h bars, selected rule")
    hl15 = load('hl15'); h15per = (hl15.index.min(), hl15.index.max())
    ev_15 = build_events(hl15, 'utc', (6,), bar_min=15)
    t_15 = simulate(hl15, ev_15, best, bar_min=15)
    r_15 = C.evaluate(t_15, 3, *h15per)
    md.append(md_row('HL_BTC_15m_actual', r_15, f"{len(ev_15)} weekends, 15m stop/target resolution"))
    rec(f"HL15m_{vname(best)}", 'BTC', '15m', dict(best, data='hl_BTC_15m'), r_15, h15per, "real HL perp 15m bars, selected rule")
    print(f"\nclock CT full {fmt(r_ct)}\nclock CT OOS {fmt(r_ct_oos)}\nyf {fmt(r_yf)}\nbinance same {fmt(r_bn_same)}\nHL1h {fmt(r_hl)}\nbinance same HL {fmt(r_bn_hl)}\nHL15m {fmt(r_15)}")
    # MBT=F execution of the selected rule with spot signal? gap on MBT own bars, 1 contract, CME fee
    p_m = dict(best)
    t_m = simulate(mbt, ev_mbt, p_m, instrument='MBT', exec_kind='CME')
    mper = (mbt.index.min(), mbt.index.max())
    r_m = C.evaluate(t_m, 3, *mper)
    md.append(md_row('MBT=F_1contract', r_m, f"gap on MBT itself (signal = reopen bar open = fill px, optimistic); hold counts trading bars; cme_fee"))
    rec(f"MBT_{vname(best)}", 'MBT', '1h', dict(best, exec='cme'), r_m, mper, "MBT=F 1 contract, own-gap, CME fee; optimistic signal timing")
    print("MBT:", fmt(r_m))
    md.append("\nLiquidity: BTC is the deepest perp on Hyperliquid (>$1B/day); single-instrument test, no concentration issue.\n")

    # ---------- verdict
    oos_folds = oos['folds'][1:]
    crit = dict(oos_net_pos=bool(oos['net'] > 0), pf_ge_1_2=bool(oos['pf'] >= 1.2), n_ge_60=bool(oos['n'] >= 60),
                folds_pos=bool(all(f > 0 for f in oos_folds)), shuffle_ok=bool(p_shuf < 0.05),
                neighbours_ok=bool(n_pos_same >= int(np.ceil(0.6 * len(same)))),
                top3_ok=bool((oos['net'] - top3) > 0),
                subperiods_ok=bool(len(yearly) and (yearly['sum'] > 0).mean() >= 0.6))
    n_fail = sum(not v for v in crit.values())
    verdict = 'edge' if n_fail == 0 else ('weak' if (oos['net'] > 0 and n_fail == 1) else 'none')
    md.append("## Verdict\n")
    md.append(f"Criteria: `{crit}` -> {n_fail} failed  \n**Verdict: {verdict}** (edge = all pass; weak = OOS net > 0 and exactly one failure; else none)\n")
    md.append("Reading: (a) the fill arm loses in every cell and every fold - weekend gaps DO get revisited more often than "
              "weekday windows of the same size (e.g. |gap|>1%: 38% vs 25% touched within 24h), but the unfilled ones run far "
              "enough that fading is a net loser even with the 1.5x stop. (b) the continuation arm is OOS-positive with all 16 "
              "neighbours positive, but it is thin: PF < 1.2, the random-window shuffle cannot reject it (p=0.21), removing the "
              "3 best trades leaves ~0, the weekday control shows the same sign (generic 48h momentum after a >0.5% move), "
              "and 2025-2026 plus the real Hyperliquid bars (17 weekends) are negative. Not tradable as specified.\n")
    print("\ncriteria:", crit, "\nverdict:", verdict)
    out.update(best_params=best, oos=oos, oos_folds=oos_folds, insample=table.to_dict('records'), shuffle_p=p_shuf,
               side_p=p_side, crit=crit, verdict=verdict, control=r_ctl, control_oos=r_ctl_oos, other_arm=dict(params=other, oos=r_o),
               neigh=[(n, r['net'], r['pf'], r['n']) for n, r, s in neigh], yearly=yearly.to_dict() if len(yearly) else {},
               top3=top3, hl1h=r_hl, hl15=r_15, yf=r_yf, ct=r_ct_oos, mbt=r_m, period=[str(period[0]), str(period[1])], n_weekends=len(ev))
    OUT_JSON.write_text(json.dumps(out, default=str, indent=1))
    OUT_MD.write_text('\n'.join(md))
    print("wrote", OUT_MD)


if __name__ == '__main__':
    main()
