"""Adversarial verification (lens: leakage / data artifacts) of
tests/h_overnight_drift.py.

Finding: the yfinance continuous front-month series (MNQ=F, MES=F, MYM=F,
MGC=F) is NOT roll-adjusted.  Yahoo rolls the series *inside* a single hourly
bar (open on the expiring contract, close on the next one), usually the 03:00
or 04:00 ET bar of expiry week, and in several expiry weeks it flip-flops
between contracts for 1-3 days.  Verified against the individual contract
tickers that Yahoo still serves (MNQU26, MESU26, MGCZ25, MGCQ26, MGCV26):
e.g. MNQ 2026-06-15 03:00 ET open 30252 -> close 30545 (+0.97%) while the
MNQ=F/MNQU26 ratio steps from -0.98% to 0.00%; MNQ 2026-03-17 03:00 ET
+0.94% (ratio -1.84% -> -1.03%).  MGC=F rolled 8 times in the OOS window
(+0.65% .. +1.65% each, contango), on 2025-03-26 (a month of contract mixing),
2025-05-11 (Sunday), 2025-07-01 08:00 (zero-volume +1.8% bar), 2025-11-25
(mixing), 2026-01-28 (then the Feb-26 dead-contract mess incl. an -8% bar),
2026-03-27 03:00, 2026-05-27 03:00, 2026-07-29 03:00.

Because these roll jumps sit inside the 16:00 -> 09:00 window and never inside
09:00 -> 16:00, a long-overnight / flat-intraday strategy on this data
harvests non-tradable contango as "overnight drift".

This script reproduces the author's headline, then recomputes the OOS net
(a) dropping every leg that overlaps a contamination window and
(b) subtracting the reference-verified roll jumps from the legs that contain
them (and dropping only the multi-day contract-mixing windows).
It also re-runs the author's paired overnight-minus-intraday test on cleaned
legs.  Nothing in the author's script is modified.
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt/tests')
import common as C
import h_overnight_drift as H

ET = 'America/New_York'
INSTS = H.INSTS
STRAT = 'overnight_drift'
BEST = dict(session='on_16_9', side=1, filt='all')   # author's fold-1 selection (basket)


def ts(s):
    return pd.Timestamp(s, tz=ET)


# --------------------------------------------------------------------------
# Contamination windows [start, end] in ET.  A leg is contaminated if
# [entry_time, exit_time] overlaps a window.
# Equity: Friday 16:00 before expiry week -> Monday 09:00 after expiry
# (covers the in-bar roll, the multi-day contract flip-flops and the
# post-expiry Sunday reopen).
EQ_EXPIRY = ['2025-03-21', '2025-06-20', '2025-09-19', '2025-12-19', '2026-03-20', '2026-06-19']
EQ_WINDOWS = []
for e in EQ_EXPIRY:
    e = ts(e)
    EQ_WINDOWS.append((e - pd.Timedelta(days=7, hours=8), e + pd.Timedelta(days=3, hours=9)))  # Fri 16:00 .. Mon 09:00

# MGC: windows around each verified Yahoo roll / mixing episode
MGC_MIX = [  # multi-day contract mixing -> can only drop
    (ts('2025-03-01 00:00'), ts('2025-03-31 09:00')),
    (ts('2025-11-21 16:00'), ts('2025-11-27 09:00')),
    (ts('2026-01-27 00:00'), ts('2026-02-06 23:00')),
]
# single-bar rolls: (bar open time ET, roll jump in % of price, verified via ratio step)
MGC_ROLLS = [
    (ts('2025-05-11 18:00'), 0.94),   # Sunday reopen, ratio vs Z25 -2.53 -> -1.60
    (ts('2025-07-01 08:00'), 1.65),   # zero-volume bar, ratio vs Z25 -1.63 -> 0.00
    (ts('2026-03-27 03:00'), 0.77),   # ratio vs Q26 -1.535 -> -0.761
    (ts('2026-05-27 03:00'), 0.72),   # ratio vs Q26 -0.719 -> 0.00
    (ts('2026-07-29 03:00'), 1.49),   # ratio vs Q26 0.00 -> +1.487
]
EQ_ROLLS = {  # reference-verified single-bar rolls (MNQU26 / MESU26); MYM co-moved on the same bars
    'MNQ': [(ts('2025-09-16 04:00'), 1.146), (ts('2026-03-17 03:00'), 0.94), (ts('2026-06-15 03:00'), 0.97)],
    'MES': [(ts('2026-03-17 03:00'), 0.83), (ts('2026-06-15 03:00'), 0.81)],
    'MYM': [(ts('2026-06-15 03:00'), 0.74)],
}
EQ_MIX = [  # contract flip-flop weeks (bar-boundary gaps alternating +-1%) -> drop
    (ts('2025-03-14 16:00'), ts('2025-03-24 09:00')),
    (ts('2025-06-13 16:00'), ts('2025-06-23 09:00')),
    (ts('2025-12-12 16:00'), ts('2025-12-22 09:00')),
]


def overlaps(entry, exit_, windows):
    for s, e in windows:
        if entry <= e and exit_ >= s:
            return True
    return False


def main():
    starts = [H.bars(i).index.min() for i in INSTS]
    ends = [H.bars(i).index.max() for i in INSTS]
    span = (max(starts), min(ends))
    bounds = C.fold_bounds(span, 3)
    oos_s, oos_e = bounds[1][0], bounds[2][1]
    print(f'span {span[0]:%Y-%m-%d} -> {span[1]:%Y-%m-%d}; OOS {oos_s:%Y-%m-%d} -> {oos_e:%Y-%m-%d}')

    run = H.run_fn_factory(INSTS)
    base = run(BEST, oos_s, oos_e)
    r0 = C.evaluate(base, 3, start=span[0], end=span[1])
    print('BASELINE (author, reproduced):', H.fmt(r0))
    base = C.add_pnl(base)
    base['ent_et'] = base['entry_time'].dt.tz_convert(ET)
    base['ex_et'] = base['exit_time'].dt.tz_convert(ET)

    # ---- (a) DROP contaminated legs
    def contaminated(row):
        if row.instrument == 'MGC':
            win = MGC_MIX + [(t, t + pd.Timedelta(hours=1)) for t, _ in MGC_ROLLS]
        else:
            win = EQ_WINDOWS
        return overlaps(row.ent_et, row.ex_et, win)
    base['contam'] = [contaminated(r) for r in base.itertuples()]
    drop = base[~base['contam']]
    r_drop = C.evaluate(drop, 3, start=span[0], end=span[1])
    print(f'\n(a) DROP legs overlapping contamination windows: removed {int(base.contam.sum())} of {len(base)} legs, '
          f'their net = {base.loc[base.contam, "net_pnl"].sum():.2f}')
    print('    corrected OOS:', H.fmt(r_drop))
    for inst in INSTS:
        b_i = base[base.instrument == inst]; d_i = drop[drop.instrument == inst]
        print(f'    {inst}: base net {b_i.net_pnl.sum():9.2f} (n={len(b_i)}) -> drop net {d_i.net_pnl.sum():9.2f} (n={len(d_i)}); '
              f'removed legs net {b_i.loc[b_i.contam, "net_pnl"].sum():8.2f}')

    # ---- (b) SUBTRACT verified roll jumps; drop only multi-day mixing windows
    sub = base.copy()
    sub['roll_usd'] = 0.0
    for r in sub.itertuples():
        rolls = MGC_ROLLS if r.instrument == 'MGC' else EQ_ROLLS[r.instrument]
        adj = 0.0
        for t, pct in rolls:
            if r.ent_et <= t < r.ex_et:
                adj += pct / 100.0 * r.entry_px * C.cme_multiplier(r.instrument)
        sub.loc[r.Index, 'roll_usd'] = adj
    mixwin = {i: (MGC_MIX if i == 'MGC' else EQ_MIX) for i in INSTS}
    sub['mix'] = [overlaps(r.ent_et, r.ex_et, mixwin[r.instrument]) for r in sub.itertuples()]
    sub2 = sub[~sub['mix']].copy()
    # apply the subtraction by shifting exit_px (keeps evaluate() fee model intact)
    sub2['exit_px'] = sub2['exit_px'] - sub2['roll_usd'] / (sub2['multiplier'] * sub2['qty'])
    r_sub = C.evaluate(sub2, 3, start=span[0], end=span[1])
    print(f'\n(b) SUBTRACT verified roll jumps (total {sub.roll_usd.sum():.2f} USD over {int((sub.roll_usd != 0).sum())} legs) '
          f'and drop {int(sub.mix.sum())} legs in multi-day contract-mixing windows (their net {sub.loc[sub.mix, "net_pnl"].sum():.2f}):')
    print('    corrected OOS:', H.fmt(r_sub))
    for inst in INSTS:
        s_i = sub[sub.instrument == inst]
        print(f'    {inst}: roll USD subtracted {s_i.roll_usd.sum():8.2f}; mixing legs dropped {int(s_i.mix.sum())} (net {s_i.loc[s_i.mix, "net_pnl"].sum():.2f})')

    # ---- paired overnight-minus-intraday test on cleaned legs (drop rule), OOS
    print('\nPaired test overnight(16->9) minus intraday(9->16), OOS, contamination legs dropped:')
    for inst in INSTS:
        m = C.cme_multiplier(inst)
        on = H.legs(inst, 16, 9, True); idd = H.legs(inst, 9, 16, False)
        on = on[(on.entry_time >= oos_s) & (on.entry_time < oos_e)].copy()
        idd = idd[(idd.entry_time >= oos_s) & (idd.entry_time < oos_e)].copy()
        win = (MGC_MIX + [(t, t + pd.Timedelta(hours=1)) for t, _ in MGC_ROLLS]) if inst == 'MGC' else EQ_WINDOWS
        for df in (on, idd):
            df['ent_et'] = pd.to_datetime(df.entry_time).dt.tz_convert(ET)
            df['ex_et'] = pd.to_datetime(df.exit_time).dt.tz_convert(ET)
            df['contam'] = [overlaps(r.ent_et, r.ex_et, win) for r in df.itertuples()]
        on_r = pd.Series(((on.exit_px - on.entry_px) * m).values, index=on.ex_et.dt.date)
        id_r = pd.Series(((idd.exit_px - idd.entry_px) * m).values, index=idd.entry_date.values)
        pair_all = pd.concat([on_r.rename('on'), id_r.rename('id')], axis=1).dropna()
        onc = on[~on.contam]; idc = idd[~idd.contam]
        on_c = pd.Series(((onc.exit_px - onc.entry_px) * m).values, index=onc.ex_et.dt.date)
        id_c = pd.Series(((idc.exit_px - idc.entry_px) * m).values, index=idc.entry_date.values)
        pair = pd.concat([on_c.rename('on'), id_c.rename('id')], axis=1).dropna()
        t0, p0 = stats.ttest_1samp(pair_all['on'] - pair_all['id'], 0)
        t1, p1 = stats.ttest_1samp(pair['on'] - pair['id'], 0)
        print(f'  {inst}: raw pairs={len(pair_all)} on={pair_all.on.sum():.0f} id={pair_all.id.sum():.0f} t={t0:.2f} p={p0:.3f} | '
              f'clean pairs={len(pair)} on={pair.on.sum():.0f} id={pair.id.sum():.0f} t={t1:.2f} p={p1:.3f}')
        C.record_to_lab(STRAT, 'verify_leak_asym_clean', inst, '1h', dict(on='16->9', id='9->16', rule='drop_roll_windows'),
                        dict(C.empty_result(), n=int(len(pair)), net=float((pair.on - pair.id).sum()), wr=float(((pair.on - pair.id) > 0).mean())),
                        period=(oos_s, oos_e), source=__file__, trust='estimated',
                        notes=f'adversarial verify: paired on-minus-id gross, roll/mixing legs dropped; t={t1:.2f} p={p1:.3f}; raw t={t0:.2f} p={p0:.3f}')

    # ---- record corrected OOS
    period = (span[0], span[1])
    C.record_to_lab(STRAT, 'verify_leak_baseline_' + H.vname(BEST), 'BASKET', '1h', dict(BEST, universe=INSTS), r0,
                    period=period, source=__file__, notes='adversarial verify: reproduced author OOS (folds 2+3), unadjusted yfinance front-month')
    C.record_to_lab(STRAT, 'verify_leak_drop_rollwin_' + H.vname(BEST), 'BASKET', '1h', dict(BEST, universe=INSTS, rule='drop_roll_windows'), r_drop,
                    period=period, source=__file__, baseline_net=r0['net'],
                    notes=f'adversarial verify: legs overlapping Yahoo roll / contract-mixing windows dropped ({int(base.contam.sum())} legs)')
    C.record_to_lab(STRAT, 'verify_leak_subtract_roll_' + H.vname(BEST), 'BASKET', '1h', dict(BEST, universe=INSTS, rule='subtract_verified_rolls'), r_sub,
                    period=period, source=__file__, baseline_net=r0['net'],
                    notes=f'adversarial verify: verified roll jumps subtracted ({sub.roll_usd.sum():.0f} USD), mixing windows dropped ({int(sub.mix.sum())} legs)')
    for inst in INSTS:
        d_i = drop[drop.instrument == inst]
        C.record_to_lab(STRAT, 'verify_leak_drop_rollwin_' + H.vname(BEST), inst, '1h', dict(BEST, rule='drop_roll_windows'),
                        C.evaluate(d_i, 3, start=span[0], end=span[1]), period=period, source=__file__,
                        baseline_net=float(base.loc[base.instrument == inst, 'net_pnl'].sum()),
                        notes='adversarial verify: per-instrument, roll/mixing legs dropped')
    print('\nrecorded to quant-lab')


if __name__ == '__main__':
    main()
