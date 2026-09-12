"""Hypothesis (round 2, key=cme_weekend_gap_btc): the CME BTC 'weekend gap'.

CME BTC futures close Fri 17:00 ET and reopen Sun 18:00 ET.  gap = spot move
over that 49h window.  Two arms, walk-forward selected on fold 1:
  A) GAP-FILL    : at the Sun 18:00 ET reopen fade the gap (toward Fri close).
                   Entry maker limit at the 18:00 bar open (touch rule: filled
                   only if the bar trades THROUGH the limit) or taker at open.
                   Exit: resting maker limit at the Friday-close level, taker
                   stop at 2x|gap| against, taker time-stop Mon 17:00 ET open.
  B) CONTINUATION: at Sun 18:00 ET go WITH the weekend move, taker in, taker
                   out at Mon 17:00 ET open (or Mon 09:00 ET open), no stop or
                   2x|gap| stop.
Thresholds |gap| > 0.5 / 1 / 2 %.  $10,000 notional on the HL BTC perp (fees
per mode from common.FEES).  Extra arms: MBT=F 1 contract priced with cme_fee,
HL BTC bars for the last 30 weekends (cross-check of the spot proxy), ETH-USD
with the BTC-selected params.

Causality: gap signal = close of the Sun 17:00 ET bar (i.e. price at 18:00) vs
close of the Fri 16:00 ET bar (price at the 17:00 CME close).  Fill at the OPEN
of the Sun 18:00 ET bar (next bar after the signal bar).  Limit exits are
checked on bars strictly after the entry bar for maker entries (fill time inside
the bar unknown) and from the entry bar for taker entries; stop is checked from
the entry bar and wins whenever stop & target touch in the same bar.

Controls: identical rule on 49h windows ending Tue/Wed/Thu 18:00 ET (weekday
control), random-window shuffle (random 49h windows, any hour/day), side
shuffle (continuation arm), 3 calendar folds (~35 weekends each).
Data: yf BTC-USD 1h 2024-08-28 -> 2026-08-27 (104 weekends), MBT=F 1h (2024-04
-> 2026-08), hl_BTC_1h (2026-01-31 -> 2026-08-27).
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

ET = 'America/New_York'
STRAT = 'cme_weekend_gap_btc'
TF = '1h'
NOTIONAL = 10_000.0
OUT_MD = Path(__file__).with_suffix('.md')
RNG = np.random.default_rng(11)
HOLD_REF_H = 50          # entry bar open (Sun 18:00) - 50h = Fri 16:00 bar open (closes at 17:00 ET)


# ---------------------------------------------------------------- data
def load(kind: str) -> pd.DataFrame:
    if kind == 'BTC':
        b = C.yf_bars('BTC-USD', '1h')
    elif kind == 'ETH':
        b = C.yf_bars('ETH-USD', '1h')
    elif kind == 'MBT':
        b = C.yf_bars('MBT=F', '1h')
    elif kind == 'HL':
        b = C.hl_candles('BTC', '1h')
    else:
        raise ValueError(kind)
    b = b[~b.index.duplicated()].copy()
    b = b[b['open'].notna() & (b['open'] > 0)]
    et = b.index.tz_convert(ET)
    b['date'] = et.date
    b['hour'] = et.hour
    b['dow'] = et.dayofweek
    b['pos'] = np.arange(len(b))
    return b


def key_lookup(b: pd.DataFrame) -> dict:
    """(ET date, ET hour) -> integer position (first bar of that wall-clock hour)."""
    d = {}
    for p, (dt, h) in enumerate(zip(b['date'].values, b['hour'].values)):
        d.setdefault((dt, h), p)
    return d


# ---------------------------------------------------------------- events
def build_events(b: pd.DataFrame, end_dows=(6,), sig_b: pd.DataFrame | None = None,
                 entry_hour: int = 18, ref_hour: int = 16, ref_days: int = 2) -> pd.DataFrame:
    """One row per candidate window ending at `entry_hour` ET on a day whose dow
    is in end_dows.  gap is measured on `sig_b` (defaults to b); levels
    (Fri close target) are taken from b.  ref = close of the (date-ref_days,
    ref_hour) bar = price at the CME close; sig = close of the bar before the
    entry bar (= price at the reopen); entry = OPEN of the entry bar."""
    if sig_b is None:
        sig_b = b
    lk, slk = key_lookup(b), key_lookup(sig_b)
    rows = []
    for (dt, h), p in lk.items():
        if h != entry_hour or b['dow'].iat[p] not in end_dows:
            continue
        ref_dt = dt - pd.Timedelta(days=ref_days)
        rp = lk.get((ref_dt, ref_hour))
        sp_ref = slk.get((ref_dt, ref_hour))
        sp_sig = slk.get((dt, entry_hour))
        if rp is None or sp_ref is None or sp_sig is None or sp_sig == 0:
            continue
        # signal bar = bar immediately before the entry bar in sig_b
        sig_prev = sp_sig - 1
        if sig_b.index[sig_prev] >= sig_b.index[sp_sig]:
            continue
        if (sig_b.index[sp_sig] - sig_b.index[sig_prev]) > pd.Timedelta(hours=2):
            continue          # signal must be fresh (bar right before the reopen)
        ref_close_sig = float(sig_b['close'].iat[sp_ref])
        sig_close = float(sig_b['close'].iat[sig_prev])
        rows.append(dict(entry_pos=p, entry_time=b.index[p], date=dt,
                         ref_time=b.index[rp], ref_close=float(b['close'].iat[rp]),
                         sig_close=sig_close, gap=sig_close / ref_close_sig - 1.0,
                         entry_open=float(b['open'].iat[p])))
    ev = pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)
    return ev


# ---------------------------------------------------------------- simulation
def simulate(b: pd.DataFrame, ev: pd.DataFrame, params: dict, instrument: str = 'BTC',
             exec_kind: str = 'HL') -> pd.DataFrame:
    """Run one rule over the events.  params:
       arm: 'fill' | 'cont'; thr: min |gap|; entry: 'maker'|'taker';
       exit_hour: ET hour on entry date + 1 for the time-stop; stop_mult: 0|2."""
    arm, thr, entry_mode = params['arm'], params['thr'], params.get('entry', 'taker')
    exit_hour, stop_mult = params.get('exit_hour', 17), params.get('stop_mult', 2)
    lk = key_lookup(b)
    trades, diag = [], []
    for e in ev.itertuples(index=False):
        g = e.gap
        if abs(g) <= thr:
            continue
        xp = lk.get((e.date + pd.Timedelta(days=1), exit_hour))
        if xp is None or xp <= e.entry_pos:
            continue
        # path must be gap-free (hourly) between entry and exit
        span = b.index[xp] - b.index[e.entry_pos]
        if (xp - e.entry_pos) < span.total_seconds() / 3600 * 0.9:
            continue
        side = -np.sign(g) if arm == 'fill' else np.sign(g)
        side = int(side)
        p0 = e.entry_pos
        o, hi, lo = float(b['open'].iat[p0]), float(b['high'].iat[p0]), float(b['low'].iat[p0])
        entry_px = o
        if entry_mode == 'maker':
            touched = (lo < o) if side > 0 else (hi > o)
            if not touched:
                diag.append(dict(entry_time=e.entry_time, filled=False))
                continue
            maker_entry, first_target_pos = True, p0 + 1
        else:
            maker_entry, first_target_pos = False, p0
        target = e.ref_close if arm == 'fill' else None
        stop_px = entry_px * (1 - side * stop_mult * abs(g)) if stop_mult else None
        exit_px, exit_pos, maker_exit, reason = None, None, False, 'time'
        for p in range(p0, xp):
            h, l = float(b['high'].iat[p]), float(b['low'].iat[p])
            if stop_px is not None:
                if (side > 0 and l <= stop_px) or (side < 0 and h >= stop_px):
                    exit_px, exit_pos, reason = stop_px, p, 'stop'
                    break
            if target is not None and p >= first_target_pos:
                if (side > 0 and h > target) or (side < 0 and l < target):
                    exit_px, exit_pos, maker_exit, reason = target, p, True, 'target'
                    break
        if exit_px is None:
            exit_px, exit_pos = float(b['open'].iat[xp]), xp
        exit_time = b.index[exit_pos] + (pd.Timedelta(0) if reason == 'time' else pd.Timedelta(minutes=59))
        if exec_kind == 'CME':
            row = C.cme_trade(e.entry_time, exit_time, side, entry_px, exit_px, 1, instrument)
        else:
            qty = NOTIONAL / entry_px
            row = C.crypto_trade(e.entry_time, exit_time, side, entry_px, exit_px, qty, instrument,
                                 maker_entry=maker_entry, maker_exit=maker_exit)
        row.update(gap=g, reason=reason, ref_close=e.ref_close)
        trades.append(row)
        diag.append(dict(entry_time=e.entry_time, filled=True))
    cols = C.REQUIRED_TRADE_COLS + ['multiplier', 'gap', 'reason', 'ref_close']
    t = pd.DataFrame(trades, columns=cols)
    t.attrs['n_signals'] = len(diag)
    t.attrs['n_filled'] = int(sum(d['filled'] for d in diag))
    return t


def descriptive(b: pd.DataFrame, ev: pd.DataFrame, horizon_h: int = 23) -> pd.DataFrame:
    """Per event: |gap| bucket, whether the Fri-close level is touched within the
    horizon, max excursion toward the level (fraction of |gap|), horizon return
    signed toward the Fri close (+ = moved toward the level)."""
    rows = []
    for e in ev.itertuples(index=False):
        p0, p1 = e.entry_pos, e.entry_pos + horizon_h
        if p1 >= len(b):
            continue
        if (b.index[p1] - b.index[p0]) > pd.Timedelta(hours=horizon_h + 1):
            continue
        g = e.gap
        if g == 0:
            continue
        seg = b.iloc[p0:p1]
        toward = -np.sign(g)
        if toward > 0:
            touched = bool((seg['high'] > e.ref_close).any())
            exc = (seg['high'].max() / e.entry_open - 1)
        else:
            touched = bool((seg['low'] < e.ref_close).any())
            exc = (1 - seg['low'].min() / e.entry_open)
        ret_toward = toward * (float(b['open'].iat[p1]) / e.entry_open - 1)
        rows.append(dict(entry_time=e.entry_time, gap=g, agap=abs(g), touched=touched,
                         exc_frac=exc / abs(g), ret_toward_bps=ret_toward * 1e4))
    return pd.DataFrame(rows)


def bucketize(d: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 0.005, 0.01, 0.02, 1.0]
    labels = ['<0.5%', '0.5-1%', '1-2%', '>2%']
    d = d.copy()
    d['bucket'] = pd.cut(d['agap'], bins=bins, labels=labels, right=False)
    g = d.groupby('bucket', observed=False).agg(n=('gap', 'size'), touch_rate=('touched', 'mean'),
                                                mean_exc_frac=('exc_frac', 'mean'),
                                                mean_ret_toward_bps=('ret_toward_bps', 'mean'))
    return g


# ---------------------------------------------------------------- grid
def grid() -> list[dict]:
    g = []
    for thr in (0.005, 0.01, 0.02):
        for entry in ('maker', 'taker'):
            g.append(dict(arm='fill', thr=thr, entry=entry, exit_hour=17, stop_mult=2))
        for exit_hour in (9, 17):
            for stop_mult in (0, 2):
                g.append(dict(arm='cont', thr=thr, entry='taker', exit_hour=exit_hour, stop_mult=stop_mult))
        g.append(dict(arm='cont', thr=thr, entry='maker', exit_hour=17, stop_mult=0))
    return g


def vname(p: dict) -> str:
    return f"{p['arm']}_thr{p['thr'] * 100:g}_{p.get('entry', 'taker')}_x{p.get('exit_hour', 17)}_s{p.get('stop_mult', 2)}"


def fmt(r: dict) -> str:
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:5.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:5.2f} "
            f"dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} folds={[round(f) for f in r['folds']]} fold_n={r['fold_n']}")


def md_row(name: str, r: dict, extra: str = '') -> str:
    return (f"| {name} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['sharpe']:.2f} | "
            f"{r['net_bps']:.1f} | {r['folds'][0]:.0f} | {r['folds'][1]:.0f} | {r['folds'][2]:.0f} | {extra} |")


MD_HDR = "| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"


# ---------------------------------------------------------------- main
def main():
    md = []
    btc = load('BTC')
    period = (btc.index.min(), btc.index.max())
    bounds = C.fold_bounds(period, 3)
    md.append("# CME weekend gap - BTC (round 2)\n")
    md.append(f"Data yf BTC-USD 1h {period[0].date()} -> {period[1].date()}; folds: " +
              ', '.join(f"[{s.date()},{e.date()})" for s, e in bounds) + "\n")
    md.append("Signal: close of the Sun 17:00 ET bar vs close of the Fri 16:00 ET bar (49h). Fill at the OPEN of "
              "the Sun 18:00 ET bar. $10k notional, HL fees per mode (maker 1.5 bps / taker 4.5 bps per side). "
              "Stop = 2x|gap| against entry (taker), gap-fill target = maker limit at the Friday close, time-stop taker.\n")

    ev_we = build_events(btc, end_dows=(6,))
    ev_ctl = build_events(btc, end_dows=(1, 2, 3))
    print(f"weekend events: {len(ev_we)}  weekday-control events: {len(ev_ctl)}")
    print("fold weekend counts:", [int(((ev_we.entry_time >= s) & (ev_we.entry_time < e)).sum()) for s, e in bounds])

    # ---------------- descriptive
    d_we, d_ctl = descriptive(btc, ev_we), descriptive(btc, ev_ctl)
    md.append("## Descriptive (23h horizon from the 18:00 ET open)\n")
    md.append(f"Weekend events n={len(d_we)}; weekday (Tue/Wed/Thu 18:00 ET, 49h window) control n={len(d_ctl)}.\n")
    for nm, d in (('Weekend', d_we), ('Weekday control', d_ctl)):
        bk = bucketize(d)
        print(f"\n{nm} by |gap| bucket:\n{bk.round(3)}")
        md.append(f"**{nm}** by |gap| bucket (touch = Fri-close level touched within 23h; exc_frac = max excursion "
                  f"toward the level / |gap|; ret_toward = 23h open-to-open return signed toward the level):\n")
        md.append("| bucket | n | touch_rate | mean_exc_frac | mean_ret_toward_bps |\n|---|---:|---:|---:|---:|")
        for idx, r in bk.iterrows():
            md.append(f"| {idx} | {int(r['n'])} | {r['touch_rate']:.2f} | {r['mean_exc_frac']:.2f} | {r['mean_ret_toward_bps']:.1f} |")
        md.append("")
    for thr in (0.005, 0.01):
        a, c = d_we[d_we.agap > thr], d_ctl[d_ctl.agap > thr]
        line = (f"|gap|>{thr*100:g}%: weekend touch {a.touched.mean():.2f} (n={len(a)}) vs control {c.touched.mean():.2f} "
                f"(n={len(c)}); ret_toward weekend {a.ret_toward_bps.mean():.1f} bps vs control {c.ret_toward_bps.mean():.1f} bps")
        print(line); md.append("- " + line)
    md.append("")

    # ---------------- walk-forward on the HL-fee spot proxy
    G = grid()

    def run_fn(params, start, end, b=btc, ev=ev_we, inst='BTC'):
        t = simulate(b, ev, params, instrument=inst)
        if len(t) == 0:
            return t
        return t[(t.entry_time >= start) & (t.entry_time < end)].reset_index(drop=True)

    rep = C.full_report(G, run_fn, period, n_folds=3, min_trades=8)
    best, oos, table = rep['best_params'], rep['oos'], rep['insample']
    print("\nSelected on fold 1:", best)
    print("OOS folds 2+3:", fmt(oos))

    md.append("## Walk-forward (BTC spot proxy, HL fees)\n")
    md.append(f"Selected on fold 1: `{best}`  \n**OOS folds 2+3**: {fmt(oos)}\n")
    md.append("Full grid, full period (f1 = selection fold; the OOS view of every cell is f2+f3):\n")
    md.append(MD_HDR)
    full_rows = {}
    for i, p in enumerate(G):
        t = simulate(btc, ev_we, p)
        r = C.evaluate(t, 3, *period)
        full_rows[vname(p)] = (p, r, t)
        sel = '*' if table.loc[i, 'selected'] else ''
        fr = f"fill {t.attrs['n_filled']}/{t.attrs['n_signals']}" if p['entry'] == 'maker' else ''
        reasons = t['reason'].value_counts().to_dict() if len(t) else {}
        md.append(md_row(vname(p), r, f"{sel} {fr} {reasons}"))
        print(f"  {vname(p):32s} {fmt(r)} {fr} {reasons}")
        C.record_to_lab(STRAT, f"grid_{vname(p)}", 'BTC', TF, p, r, period=period, source=__file__,
                        notes=f"full-period grid cell; spot proxy w/ HL fees; fold1 net={table.loc[i, 'is_net']:.2f}; {reasons}")
    C.record_to_lab(STRAT, f"WF_OOS_{vname(best)}", 'BTC', TF, dict(best, wf='fold1-select'), oos, period=period,
                    source=__file__, notes="walk-forward OOS folds 2+3 (fold 1 = selection, reported 0)")
    md.append("")

    # OOS net by |gap| bucket for the selected rule
    if len(oos):
        o = C.add_pnl(oos)
        o['bucket'] = pd.cut(o['gap'].abs(), [0, 0.005, 0.01, 0.02, 1], labels=['<0.5%', '0.5-1%', '1-2%', '>2%'], right=False)
        bk = o.groupby('bucket', observed=True)['net_pnl'].agg(['size', 'sum', 'mean'])
        print("\nOOS net by |gap| bucket:\n", bk.round(1))
        md.append("OOS net by |gap| bucket (selected rule):\n\n| bucket | n | net | mean |\n|---|---:|---:|---:|")
        for idx, r in bk.iterrows():
            md.append(f"| {idx} | {int(r['size'])} | {r['sum']:.0f} | {r['mean']:.0f} |")
        md.append("")
        md.append("OOS exit reasons: " + json.dumps(o['reason'].value_counts().to_dict()) + "\n")

    # ---------------- the OTHER arm's best (for the record)
    other_arm = 'cont' if best['arm'] == 'fill' else 'fill'
    sub = table[[json.loads(s)['arm'] == other_arm for s in table['params']]].sort_values('is_net', ascending=False)
    other = G[int(sub.iloc[0]['idx'])]
    t_o = simulate(btc, ev_we, other)
    r_o = C.oos_result(t_o[t_o.entry_time >= bounds[1][0]], period, 3)
    print(f"\nBest {other_arm} arm on fold 1: {other} -> OOS {fmt(r_o)}")
    md.append(f"Best **{other_arm}** cell on fold 1 (`{other}`), OOS folds 2+3: {fmt(r_o)}\n")
    C.record_to_lab(STRAT, f"WF_OOS_otherarm_{vname(other)}", 'BTC', TF, dict(other, wf='fold1-select-within-arm'), r_o,
                    period=period, source=__file__, notes="other arm's fold-1 best, OOS folds 2+3")

    # ---------------- sanity: neighbors of the selected params (OOS folds 2+3)
    md.append("## Neighbor robustness (OOS folds 2+3 for every grid cell)\n")
    md.append(MD_HDR)
    neigh = []
    for p in G:
        t = full_rows[vname(p)][2]
        r = C.oos_result(t[t.entry_time >= bounds[1][0]] if len(t) else t, period, 3)
        same_arm = p['arm'] == best['arm']
        neigh.append((vname(p), r, same_arm))
        md.append(md_row(vname(p), r, ('same arm' if same_arm else '') + (' SELECTED' if p == best else '')))
        C.record_to_lab(STRAT, f"OOS23_{vname(p)}", 'BTC', TF, p, r, period=period, source=__file__,
                        notes="OOS folds 2+3 of this cell (sensitivity view, no selection)")
    same = [r for _, r, s in neigh if s]
    n_pos_same = sum(r['net'] > 0 for r in same)
    print(f"\nneighbors (same arm): {n_pos_same}/{len(same)} cells OOS-positive")
    md.append(f"\nSame-arm cells OOS-positive: {n_pos_same}/{len(same)}\n")

    # ---------------- control: weekday windows with the selected rule
    md.append("## Controls\n")
    md.append(MD_HDR)
    t_ctl = simulate(btc, ev_ctl, best)
    r_ctl = C.evaluate(t_ctl, 3, *period)
    print("\nWeekday control (Tue/Wed/Thu 18:00 ET, selected rule):", fmt(r_ctl))
    md.append(md_row('weekday_control_TueWedThu', r_ctl, 'same rule, 49h windows ending Tue/Wed/Thu 18:00 ET'))
    C.record_to_lab(STRAT, f"control_weekday_{vname(best)}", 'BTC', TF, dict(best, control='TueWedThu'), r_ctl,
                    period=period, source=__file__, notes="weekday control windows (Tue/Wed/Thu 18:00 ET), selected rule")
    for dow, nm in ((1, 'Tue'), (2, 'Wed'), (3, 'Thu')):
        t_d = simulate(btc, build_events(btc, end_dows=(dow,)), best)
        r_d = C.evaluate(t_d, 3, *period)
        md.append(md_row(f'control_{nm}', r_d, ''))
        print(f"  control {nm}: {fmt(r_d)}")
    # OOS-period comparison of weekend vs control
    r_ctl_oos = C.oos_result(t_ctl[t_ctl.entry_time >= bounds[1][0]], period, 3)
    md.append(md_row('weekday_control_OOSperiod', r_ctl_oos, 'folds 2+3 only, for like-for-like with the headline'))

    # ---------------- shuffle 1: random 49h windows, any hour/day
    all_pos = np.arange(HOLD_REF_H + 1, len(btc) - 30)
    n_ev = len(ev_we)
    lk = key_lookup(btc)
    shuffle_nets, shuffle_ns = [], []
    for k in range(300):
        pos = np.sort(RNG.choice(all_pos, size=n_ev, replace=False))
        rows = []
        for p in pos:
            rp = p - HOLD_REF_H
            if (btc.index[p] - btc.index[rp]) > pd.Timedelta(hours=HOLD_REF_H + 1):
                continue
            rows.append(dict(entry_pos=p, entry_time=btc.index[p], date=btc['date'].iat[p],
                             ref_time=btc.index[rp], ref_close=float(btc['close'].iat[rp]),
                             sig_close=float(btc['close'].iat[p - 1]),
                             gap=float(btc['close'].iat[p - 1]) / float(btc['close'].iat[rp]) - 1,
                             entry_open=float(btc['open'].iat[p])))
        ev_r = pd.DataFrame(rows)
        # random windows keep the same hold (exit at +23h or +15h open) via a synthetic exit
        t_r = simulate_random(btc, ev_r, best)
        t_r = t_r[t_r.entry_time >= bounds[1][0]] if len(t_r) else t_r
        r_r = C.evaluate(t_r, 1)
        shuffle_nets.append(r_r['net']); shuffle_ns.append(r_r['n'])
    shuffle_nets = np.array(shuffle_nets)
    pct = float((shuffle_nets >= oos['net']).mean())
    line = (f"random-window shuffle (300 draws, {n_ev} random 49h windows each, same rule, OOS period): "
            f"mean net={shuffle_nets.mean():.0f} sd={shuffle_nets.std():.0f} p5={np.percentile(shuffle_nets, 5):.0f} "
            f"p95={np.percentile(shuffle_nets, 95):.0f} mean n={np.mean(shuffle_ns):.0f}; actual OOS net={oos['net']:.0f} "
            f"-> P(shuffle >= actual)={pct:.3f}")
    print("\n" + line); md.append("\n- " + line)
    C.record_to_lab(STRAT, f"shuffle_randwindow_{vname(best)}", 'BTC', TF, dict(best, check='random_window'),
                    dict(C.empty_result(), n=int(np.mean(shuffle_ns)), net=float(shuffle_nets.mean()), folds=[0, 0, float(shuffle_nets.mean())]),
                    period=period, source=__file__, notes=f"mean of 300 random-window draws; p={pct:.3f}", trust='estimated')

    # ---------------- shuffle 2: side shuffle on the actual OOS trades (continuation arm only)
    if best['arm'] == 'cont' and len(oos):
        o = C.add_pnl(oos)
        gross = (o['side'] * (o['exit_px'] - o['entry_px']) * o['qty']).values
        fees = o['fee_usd'].abs().values
        act = float((gross - fees).sum())
        flips = np.array([((gross * RNG.choice([-1, 1], size=len(gross))) - fees).sum() for _ in range(2000)])
        p_side = float((flips >= act).mean())
        line = f"side shuffle (2000 draws, OOS trades, timing kept): mean={flips.mean():.0f} sd={flips.std():.0f}; actual={act:.0f} -> p={p_side:.3f}"
        print(line); md.append("- " + line)
    else:
        p_side = None

    # ---------------- HL BTC actual bars (last ~30 weekends) vs the spot proxy
    hl = load('HL')
    ev_hl = build_events(hl, end_dows=(6,))
    t_hl = simulate(hl, ev_hl, best, instrument='BTC')
    r_hl = C.evaluate(t_hl, 3, hl.index.min(), hl.index.max())
    t_px = simulate(btc, ev_we[ev_we.entry_time >= hl.index.min()], best)
    r_px = C.evaluate(t_px, 3, hl.index.min(), hl.index.max())
    print(f"\nHL BTC actual bars ({len(ev_hl)} weekends): {fmt(r_hl)}")
    print(f"spot proxy, same weekends:               {fmt(r_px)}")
    md.append("\n## Hyperliquid BTC actual bars (last 30 weekends) vs spot proxy\n")
    md.append(MD_HDR)
    md.append(md_row('HL_BTC_actual', r_hl, f"{len(ev_hl)} weekends, {hl.index.min().date()} -> {hl.index.max().date()}"))
    md.append(md_row('spot_proxy_same_weekends', r_px, ''))
    C.record_to_lab(STRAT, f"HL_actual_{vname(best)}", 'BTC', TF, dict(best, data='hl_BTC_1h'), r_hl,
                    period=(hl.index.min(), hl.index.max()), source=__file__, notes="selected rule on real HL perp bars")

    # ---------------- MBT=F execution (CME fee, 1 contract, CME hours only)
    mbt = load('MBT')
    ev_mbt = build_events(mbt, end_dows=(6,), sig_b=btc)          # signal from spot, levels/fills on MBT
    ev_mbt_own = build_events(mbt, end_dows=(6,))                 # gap from MBT's own Fri close -> Sun 18:00 open bar
    p_mbt = dict(best, exit_hour=min(best.get('exit_hour', 17), 16))   # MBT has no 17:00 ET bar
    t_mbt = simulate(mbt, ev_mbt, p_mbt, instrument='MBT', exec_kind='CME')
    mper = (mbt.index.min(), mbt.index.max())
    r_mbt = C.evaluate(t_mbt, 3, *mper)
    r_mbt_oos = C.oos_result(t_mbt[t_mbt.entry_time >= bounds[1][0]], period, 3)
    print(f"\nMBT=F 1 contract, spot signal ({len(ev_mbt)} weekends paired): {fmt(r_mbt)}")
    print(f"MBT=F OOS period (yf folds 2+3): {fmt(r_mbt_oos)}")
    md.append("\n## MBT=F execution (1 contract, cme_fee round trip, time-stop Mon 16:00 ET open)\n")
    md.append(f"Weekends paired Fri->Sun on MBT: {len(ev_mbt_own)} (own gap), {len(ev_mbt)} (spot-signal, MBT fills).\n")
    md.append(MD_HDR)
    md.append(md_row('MBT_full_period', r_mbt, f"{mper[0].date()} -> {mper[1].date()}, MBT folds"))
    md.append(md_row('MBT_OOS_period', r_mbt_oos, 'restricted to yf folds 2+3'))
    C.record_to_lab(STRAT, f"MBT_{vname(p_mbt)}", 'MBT', TF, dict(p_mbt, exec='cme', signal='spot'), r_mbt,
                    period=mper, source=__file__, notes="MBT=F 1 contract, spot-signal, CME fee model")
    # MBT-own-gap variant full grid summary for the selected arm
    t_mbt2 = simulate(mbt, ev_mbt_own, p_mbt, instrument='MBT', exec_kind='CME')
    r_mbt2 = C.evaluate(t_mbt2, 3, *mper)
    md.append(md_row('MBT_own_gap', r_mbt2, 'gap = MBT Sun 18:00 open vs MBT Fri close (signal==fill bar, optimistic)'))
    C.record_to_lab(STRAT, f"MBT_owngap_{vname(p_mbt)}", 'MBT', TF, dict(p_mbt, exec='cme', signal='mbt_open'), r_mbt2,
                    period=mper, source=__file__, notes="MBT own-gap variant (signal at the fill bar's open; optimistic)")

    # ---------------- ETH with the BTC-selected params (per-coin)
    eth = load('ETH')
    ev_eth = build_events(eth, end_dows=(6,))
    t_eth = simulate(eth, ev_eth, best, instrument='ETH')
    r_eth = C.evaluate(t_eth, 3, *period)
    r_eth_oos = C.oos_result(t_eth[t_eth.entry_time >= bounds[1][0]], period, 3)
    print(f"\nETH-USD, BTC-selected rule: full {fmt(r_eth)}\n   OOS {fmt(r_eth_oos)}")
    md.append("\n## Per-coin: ETH-USD with the BTC-selected rule (no re-selection)\n")
    md.append(MD_HDR)
    md.append(md_row('ETH_full', r_eth, ''))
    md.append(md_row('ETH_OOS23', r_eth_oos, ''))
    C.record_to_lab(STRAT, f"ETH_{vname(best)}", 'ETH', TF, dict(best, coin='ETH'), r_eth, period=period,
                    source=__file__, notes="ETH with BTC-selected params; full period")
    md.append("\nBoth BTC and ETH are top-2 liquidity names on Hyperliquid (>$1B/day); no illiquid-name concentration is possible here.\n")

    # ---------------- verdict
    oos_ok = oos['net'] > 0
    crit = dict(oos_net_pos=oos_ok, pf_ge_1_2=oos['pf'] >= 1.2, n_ge_60=oos['n'] >= 60,
                folds_pos=all(f > 0 for f in oos['folds'][1:]), shuffle_ok=pct < 0.05,
                neighbors_ok=(n_pos_same >= max(1, int(np.ceil(0.6 * len(same))))))
    if oos_ok and all(crit.values()):
        verdict = 'edge'
    elif oos_ok:
        verdict = 'weak'
    else:
        verdict = 'none'
    md.append("## Verdict\n")
    md.append(f"Criteria: {crit}  \n**Verdict: {verdict}**\n")
    print("\ncriteria:", crit, "\nverdict:", verdict)

    out = dict(best_params=best, oos=oos, oos_folds=oos['folds'][1:], insample=table.to_dict('records'),
               shuffle_p=pct, side_p=p_side, crit=crit, verdict=verdict, control=r_ctl, hl=r_hl,
               mbt=r_mbt, eth=r_eth_oos, other_arm=dict(params=other, oos=r_o),
               neigh=[(n, r['net'], r['pf'], r['n']) for n, r, s in neigh if s],
               period=[str(period[0]), str(period[1])], n_weekends=len(ev_we))
    Path(__file__).with_name('h_cme_weekend_gap_btc.json').write_text(json.dumps(out, default=str, indent=1))
    OUT_MD.write_text('\n'.join(md))
    print("wrote", OUT_MD)


def simulate_random(b: pd.DataFrame, ev: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Same as simulate() but exits at entry+23h (or +15h) bar position instead of
    the wall-clock Mon 17:00/09:00 (for random windows on any day/hour)."""
    hold = 23 if params.get('exit_hour', 17) == 17 else 15
    ev = ev.copy()
    # emulate lookup by giving each event its own exit position
    rows = []
    for e in ev.itertuples(index=False):
        rows.append(e._asdict())
    lkfake = {}
    for r in rows:
        lkfake[(r['date'] + pd.Timedelta(days=1), params.get('exit_hour', 17))] = None
    # simplest: temporarily re-key: build a per-event exit position and run a trimmed copy of simulate
    arm, thr, entry_mode = params['arm'], params['thr'], params.get('entry', 'taker')
    stop_mult = params.get('stop_mult', 2)
    trades = []
    for e in ev.itertuples(index=False):
        g = e.gap
        if abs(g) <= thr:
            continue
        p0, xp = e.entry_pos, e.entry_pos + hold
        if xp >= len(b) or (b.index[xp] - b.index[p0]) > pd.Timedelta(hours=hold + 1):
            continue
        side = int(-np.sign(g) if arm == 'fill' else np.sign(g))
        o, hi, lo = float(b['open'].iat[p0]), float(b['high'].iat[p0]), float(b['low'].iat[p0])
        entry_px = o
        if entry_mode == 'maker':
            if not ((lo < o) if side > 0 else (hi > o)):
                continue
            maker_entry, first_target_pos = True, p0 + 1
        else:
            maker_entry, first_target_pos = False, p0
        target = e.ref_close if arm == 'fill' else None
        stop_px = entry_px * (1 - side * stop_mult * abs(g)) if stop_mult else None
        exit_px, exit_pos, maker_exit, reason = None, None, False, 'time'
        for p in range(p0, xp):
            h, l = float(b['high'].iat[p]), float(b['low'].iat[p])
            if stop_px is not None and ((side > 0 and l <= stop_px) or (side < 0 and h >= stop_px)):
                exit_px, exit_pos, reason = stop_px, p, 'stop'; break
            if target is not None and p >= first_target_pos and ((side > 0 and h > target) or (side < 0 and l < target)):
                exit_px, exit_pos, maker_exit, reason = target, p, True, 'target'; break
        if exit_px is None:
            exit_px, exit_pos = float(b['open'].iat[xp]), xp
        qty = NOTIONAL / entry_px
        trades.append(C.crypto_trade(b.index[p0], b.index[exit_pos], side, entry_px, exit_px, qty, 'BTC',
                                     maker_entry=maker_entry, maker_exit=maker_exit))
    return pd.DataFrame(trades, columns=C.REQUIRED_TRADE_COLS + ['multiplier'])


if __name__ == '__main__':
    main()
