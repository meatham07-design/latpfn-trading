"""Execution-lens verification of h_overnight_drift (adversarial re-run).

Checks:
 1. Reproduce the author's OOS basket number (on_16_9, long, all, 1 ct each).
 2. Continuous-contract roll artifact: yfinance `MNQ=F` etc. are un-adjusted
    front-month splices.  When Yahoo switches to the next contract (roll week)
    the series jumps UP by the calendar basis (~1.0% MNQ, ~0.9% MES, ~0.75% MYM,
    ~0.7-0.9% MGC per roll - verified against live contract spreads
    MNQZ26-MNQU26 etc.).  A real long holder does NOT earn that jump (he sells
    the expiring contract and buys the deferred one at the premium).  The
    switch happens between sessions, i.e. inside the 16:00->09:00 hold, so the
    long-overnight strategy books every roll premium as PnL.  Detected here by
    comparing each overnight leg's futures return with the matching ETF proxy
    close->open return (QQQ/SPY/DIA/GLD), inside scheduled roll windows.
 3. Slippage stress: +1 and +2 extra ticks per side on top of common.FEES.
 4. Zero-volume fill bars (Yahoo prints with no trades).
 5. Paired overnight-minus-intraday test (the actual hypothesis) on the
    roll-adjusted legs.
Everything recorded to quant-lab under strategy 'overnight_drift' with
variant prefix 'verify_exec_'.
"""
from __future__ import annotations
import sys, calendar, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt/tests')
import common as C
import h_overnight_drift as H

ET = 'America/New_York'
SP = Path('/private/tmp/claude-501/-Users-molt-bot/78c80aee-b9a8-40f2-986e-38cb35c978c8/scratchpad')
PROXY = {'MNQ': 'QQQ', 'MES': 'SPY', 'MYM': 'DIA', 'MGC': 'GLD'}
TICK_USD = {'MNQ': 0.50, 'MES': 1.25, 'MYM': 0.50, 'MGC': 1.00}   # 1 tick, USD per contract
STRAT = 'overnight_drift'
BEST = dict(session='on_16_9', side=1, filt='all')


def etf_daily() -> dict[str, pd.DataFrame]:
    p = SP / 'etf_daily.pkl'
    if p.exists():
        d = pd.read_pickle(p)
    else:
        import yfinance as yf
        d = yf.download(list(PROXY.values()), start='2024-04-01', interval='1d',
                        auto_adjust=False, progress=False, group_by='ticker')
        d.to_pickle(p)
    out = {}
    for s in PROXY.values():
        e = d[s][['Open', 'Close']].copy(); e.index = e.index.date; out[s] = e
    return out


def third_friday(y, m):
    c = calendar.monthcalendar(y, m)
    fr = [w[calendar.FRIDAY] for w in c if w[calendar.FRIDAY]]
    return dt.date(y, m, fr[2])


def roll_windows(inst: str, years=(2024, 2025, 2026)):
    """Calendar windows in which Yahoo may switch the front month."""
    w = []
    if inst == 'MGC':
        for y in years:
            for m in (2, 4, 6, 8, 10, 12):          # delivery months
                # Yahoo's GC/MGC switch lands either just before first-notice
                # (last days of M-1) or at the front month's expiry (last days
                # of M); cover both conventions.
                first = dt.date(y, m, 1)
                last = dt.date(y, m, calendar.monthrange(y, m)[1])
                w.append((first - dt.timedelta(days=9), first + dt.timedelta(days=3)))
                w.append((last - dt.timedelta(days=8), last + dt.timedelta(days=4)))
    else:
        for y in years:
            for m in (3, 6, 9, 12):
                f = third_friday(y, m)
                w.append((f - dt.timedelta(days=9), f + dt.timedelta(days=1)))
    return w


def in_window(d, wins):
    return any(a <= d <= b for a, b in wins)


def overnight_legs_with_proxy(inst: str, etf) -> pd.DataFrame:
    L = H.legs(inst, 16, 9, True).copy()
    L['d_in'] = pd.to_datetime(L.entry_time).dt.tz_convert(ET).dt.date
    L['d_out'] = pd.to_datetime(L.exit_time).dt.tz_convert(ET).dt.date
    L['fut_r'] = np.log(L.exit_px / L.entry_px)
    e = etf[PROXY[inst]]
    L['etf_r'] = [np.log(e.Open.get(o, np.nan) / e.Close.get(i, np.nan)) for i, o in zip(L.d_in, L.d_out)]
    L['diff'] = L.fut_r - L.etf_r
    wins = roll_windows(inst)
    L['in_win'] = [in_window(d, wins) for d in L.d_out]
    base = L.loc[~L.in_win, 'diff'].median()
    L['jump'] = 0.0
    # one roll per window: the largest positive diff inside the window, if > 0.45%
    for a, b in wins:
        m = L.in_win & (L.d_out >= a) & (L.d_out <= b) & (L['diff'] > 0.0045)
        if m.any():
            k = L.loc[m, 'diff'].idxmax()
            L.loc[k, 'jump'] = L.loc[k, 'diff'] - base
    return L


def build_trades(inst, L, extra_ticks_per_side=0, roll_adjust=False, drop_zero_vol=False, start=None, end=None):
    b = H.bars(inst)
    rows = []
    for r in L.itertuples():
        if start is not None and not (start <= r.entry_time < end):
            continue
        if drop_zero_vol and (b['volume'].get(r.entry_time, 1) == 0 or b['volume'].get(r.exit_time, 1) == 0):
            continue
        xp = r.exit_px * np.exp(-r.jump) if roll_adjust else r.exit_px
        t = C.cme_trade(r.entry_time, r.exit_time, 1, r.entry_px, xp, 1, inst)
        t['fee_usd'] += 2 * extra_ticks_per_side * TICK_USD[inst]
        rows.append(t)
    return pd.DataFrame(rows, columns=C.REQUIRED_TRADE_COLS + ['multiplier'])


def main():
    etf = etf_daily()
    starts = [H.bars(i).index.min() for i in H.INSTS]; ends = [H.bars(i).index.max() for i in H.INSTS]
    span = (max(starts), min(ends)); bounds = C.fold_bounds(span, 3)
    oos_s, oos_e = bounds[1][0], bounds[2][1]
    print('span', span, 'OOS', oos_s, '->', oos_e)

    # 1. reproduce
    run = H.run_fn_factory(H.INSTS)
    base = C.evaluate(run(BEST, oos_s, oos_e), 3, start=span[0], end=span[1])
    print(f"\n[1] reproduced author OOS: n={base['n']} net={base['net']:.2f} folds={[round(f) for f in base['folds']]} pf={base['pf']:.3f}")

    # 2. roll artifact per instrument
    legs = {i: overnight_legs_with_proxy(i, etf) for i in H.INSTS}
    print("\n[2] detected roll jumps inside OOS overnight legs (futures vs ETF-proxy overnight return):")
    roll_usd = {}
    for inst, L in legs.items():
        m = C.cme_multiplier(inst)
        Lo = L[(L.entry_time >= oos_s) & (L.entry_time < oos_e)]
        R = Lo[Lo.jump > 0]
        usd = float((R.jump * R.entry_px * m).sum())
        roll_usd[inst] = usd
        print(f"  {inst}: {len(R)} rolls, jump median {R.jump.median()*100:.2f}%  -> {usd:.0f} USD of OOS gross; "
              f"non-roll diff median {L.loc[~L.in_win,'diff'].median()*100:.3f}%; "
              f"sum diff OOS {Lo['diff'].sum()*100:.2f}%  (fut {Lo.fut_r.sum()*100:.2f}% vs etf {Lo.etf_r.sum()*100:.2f}%)")
        for r in R.itertuples():
            print(f"      {r.d_in} -> {r.d_out}: fut {r.fut_r*100:+.2f}%  {PROXY[inst]} {r.etf_r*100:+.2f}%  jump {r.jump*100:.2f}%  = {r.jump*r.entry_px*m:.0f} USD")

    # 3./4. variants
    variants = {
        'A_author_baseline':        dict(extra_ticks_per_side=0, roll_adjust=False),
        'B_roll_adjusted':          dict(extra_ticks_per_side=0, roll_adjust=True),
        'C_plus1tick_side':         dict(extra_ticks_per_side=1, roll_adjust=False),
        'D_roll_adj_plus1tick':     dict(extra_ticks_per_side=1, roll_adjust=True),
        'E_roll_adj_plus2tick':     dict(extra_ticks_per_side=2, roll_adjust=True),
        'F_roll_adj_plus1_nozero':  dict(extra_ticks_per_side=1, roll_adjust=True, drop_zero_vol=True),
    }
    print("\n[3] OOS (folds 2+3) basket and per-instrument net under execution corrections:")
    summary = {}
    for vn, kw in variants.items():
        parts = {i: build_trades(i, legs[i], start=oos_s, end=oos_e, **kw) for i in H.INSTS}
        allt = pd.concat(parts.values(), ignore_index=True)
        r = C.evaluate(allt, 3, start=span[0], end=span[1])
        per = {i: C.evaluate(parts[i], 3, start=span[0], end=span[1]) for i in H.INSTS}
        summary[vn] = r
        print(f"  {vn:26s} n={r['n']} net={r['net']:9.2f} pf={r['pf']:.3f} folds2,3={[round(f) for f in r['folds'][1:]]}  "
              + "  ".join(f"{i}={per[i]['net']:.0f}" for i in H.INSTS))
        C.record_to_lab(STRAT, f'verify_exec_{vn}', 'BASKET', '1h', dict(BEST, universe=H.INSTS, **kw), r,
                        period=(oos_s, oos_e), source=__file__,
                        notes=f"execution-lens verification, OOS folds 2+3; roll_usd_removed={sum(roll_usd.values()):.0f}")
        for i in H.INSTS:
            C.record_to_lab(STRAT, f'verify_exec_{vn}', i, '1h', dict(BEST, **kw), per[i],
                            period=(oos_s, oos_e), source=__file__, notes='execution-lens verification, OOS folds 2+3')

    # 5. paired overnight-minus-intraday on roll-adjusted legs (OOS)
    print("\n[5] paired overnight-minus-intraday (gross USD/ct, OOS), raw vs roll-adjusted:")
    for inst in H.INSTS:
        m = C.cme_multiplier(inst)
        L = legs[inst]; L = L[(L.entry_time >= oos_s) & (L.entry_time < oos_e)]
        idd = H.legs(inst, 9, 16, False); idd = idd[(idd.entry_time >= oos_s) & (idd.entry_time < oos_e)]
        on_raw = pd.Series(((L.exit_px - L.entry_px) * m).values, index=L.d_out.values)
        on_adj = pd.Series(((L.exit_px * np.exp(-L.jump) - L.entry_px) * m).values, index=L.d_out.values)
        id_s = pd.Series(((idd.exit_px - idd.entry_px) * m).values, index=idd.entry_date.values)
        for lab, on in (('raw', on_raw), ('roll_adj', on_adj)):
            pair = pd.concat([on.rename('on'), id_s.rename('id')], axis=1).dropna()
            dif = pair['on'] - pair['id']; t, p = stats.ttest_1samp(dif, 0)
            print(f"  {inst} {lab:8s} pairs={len(pair)} on_sum={pair['on'].sum():.0f} id_sum={pair['id'].sum():.0f} t={t:.2f} p={p:.3f}")
            C.record_to_lab(STRAT, f'verify_exec_asym_{lab}', inst, '1h', dict(on='16->9', id='9->16', roll_adj=lab == 'roll_adj'),
                            dict(C.empty_result(), n=int(len(pair)), net=float(dif.sum()), wr=float((dif > 0).mean())),
                            period=(oos_s, oos_e), source=__file__, trust='estimated',
                            notes=f"paired on-minus-id gross USD/ct OOS; t={t:.2f} p={p:.3f}")

    # zero-volume bars
    print("\n[4] zero-volume entry/exit bars among OOS legs:",
          {i: int(sum((H.bars(i)['volume'].get(t, 1) == 0) for t in list(legs[i][(legs[i].entry_time >= oos_s)].entry_time) + list(legs[i][(legs[i].entry_time >= oos_s)].exit_time))) for i in H.INSTS})
    print("\nCORRECTED OOS NET (roll-adjusted + 1 extra tick/side):", round(summary['D_roll_adj_plus1tick']['net'], 2))
    return summary


if __name__ == '__main__':
    main()
