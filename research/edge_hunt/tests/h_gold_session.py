"""Hypothesis (gold_session): gold micro (MGC=F; GC=F as a check) has
tradeable intraday SESSION patterns:
  * Asian-session drift       (Globex reopen 18:00 ET -> London open ~03:00 ET)
  * London AM / PM fix hours  (10:30 and 15:00 London: pre-fix / post-fix windows)
  * COMEX pit hours           (08:20-13:30 ET) reversal, and post-pit drift.

Rule family: hold ONE contract long or short from the OPEN of the bar whose
local-hour == e_in to the OPEN of the first later bar whose local-hour == e_out
(same or next session, must be within 26h; holiday/weekend-broken legs are
dropped).  Time-based schedule, no bar-close signal -> fills at bar opens are
strictly causal.  Fees: common.cme_fee (commission + 1 tick slippage / side).
Data: yfinance 1h (874d, 2024-04-05 -> 2026-08-27, bar OPEN timestamps aligned
to ET whole hours; 17:00 ET maintenance hour absent).  5m (71d) only used for a
descriptive +-30min-around-the-fix check (too short for walk-forward).
Walk-forward: 20-cell grid, select on fold 1 (calendar third), OOS = folds 2+3.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

ET, LON = 'America/New_York', 'Europe/London'
STRAT = 'gold_session'
OUT_MD = Path(__file__).with_suffix('.md')
OUT_JSON = Path(__file__).with_name('h_gold_session_result.json')
RNG = np.random.default_rng(11)
TZ = {'ET': ET, 'LON': LON}

# ---------------------------------------------------------------- data
_BARS: dict[str, pd.DataFrame] = {}


def bars(inst: str, interval: str = '1h') -> pd.DataFrame:
    k = (inst, interval)
    if k not in _BARS:
        b = C.yf_bars(f'{inst}=F', interval).copy()
        b = b[~b.index.duplicated()]
        b = b[b['open'].notna() & (b['open'] > 0)]
        b['h_ET'] = b.index.tz_convert(ET).hour
        b['h_LON'] = b.index.tz_convert(LON).hour
        b['m_LON'] = b.index.tz_convert(LON).minute
        b['dow'] = b.index.tz_convert(ET).dayofweek
        if interval == '1h':
            b = b[(b['h_ET'] != 17) & (b.index.minute == 0)]   # maintenance hour + stray :30 prints
        _BARS[k] = b
    return _BARS[k]


# ---------------------------------------------------------------- legs
SESSIONS = {
    # name: (tz, e_in, e_out)  hours are LOCAL to tz; entry/exit at bar OPEN
    'asia_18_3':   ('ET', 18, 3),    # Globex reopen -> London open
    'asia_19_3':   ('ET', 19, 3),
    'asia_20_2':   ('ET', 20, 2),    # Tokyo/Shanghai core
    'lon_pre_am':  ('LON', 8, 10),   # London open -> into the 10:30 AM fix bar
    'lon_post_am': ('LON', 11, 13),  # after the AM fix bar
    'lon_pre_pm':  ('LON', 13, 15),  # into the 15:00 PM fix
    'lon_post_pm': ('LON', 15, 17),  # PM fix -> London close
    'us_pit_8_13': ('ET', 8, 13),    # COMEX pit 08:20-13:30 ET (hourly proxy)
    'us_pit_9_13': ('ET', 9, 13),
    'us_post_pit': ('ET', 13, 16),   # pit close -> cash close
}
_LEGS: dict[tuple, pd.DataFrame] = {}


def legs(inst: str, tz: str, e_in: int, e_out: int) -> pd.DataFrame:
    """One row per scheduled leg (entry bar open -> first later bar open with
    local hour e_out, within 26h)."""
    k = (inst, tz, e_in, e_out)
    if k in _LEGS:
        return _LEGS[k]
    b = bars(inst)
    hcol = f'h_{tz}'
    ent = b[b[hcol] == e_in]
    ex = b[b[hcol] == e_out]
    rows = []
    for t, r in ent.iterrows():
        j = ex.index.searchsorted(t, side='right')
        if j >= len(ex):
            continue
        xt = ex.index[j]
        if (xt - t) > pd.Timedelta(hours=26):
            continue
        rows.append(dict(entry_time=t, exit_time=xt, entry_px=float(r['open']),
                         exit_px=float(ex['open'].iloc[j]), dow=int(r['dow'])))
    df = pd.DataFrame(rows, columns=['entry_time', 'exit_time', 'entry_px', 'exit_px', 'dow'])
    _LEGS[k] = df
    return df


def make_trades(inst: str, tz: str, e_in: int, e_out: int, side: int) -> pd.DataFrame:
    df = legs(inst, tz, e_in, e_out)
    if len(df) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    rows = [C.cme_trade(r.entry_time, r.exit_time, side, r.entry_px, r.exit_px, 1, inst)
            for r in df.itertuples()]
    return pd.DataFrame(rows)


def trades_for(p: dict, inst: str) -> pd.DataFrame:
    if 'session' in p:
        tz, ei, eo = SESSIONS[p['session']]
    else:
        tz, ei, eo = p['tz'], p['e_in'], p['e_out']
    return make_trades(inst, tz, ei, eo, p['side'])


def run_fn_factory(inst: str):
    def run_fn(p, start, end):
        t = trades_for(p, inst)
        if len(t):
            t = t[(t['entry_time'] >= start) & (t['entry_time'] < end)]
        return t
    return run_fn


GRID = [dict(session=s, side=sd) for s in SESSIONS for sd in (1, -1)]
assert len(GRID) == 20


def vname(p):
    if 'session' in p:
        return f"{p['session']}_{'L' if p['side'] > 0 else 'S'}"
    return f"{p['tz']}_{p['e_in']}_{p['e_out']}_{'L' if p['side'] > 0 else 'S'}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.0f} folds={[round(f) for f in r['folds']]}")


def sub(t, s, e):
    return t[(t['entry_time'] >= s) & (t['entry_time'] < e)] if len(t) else t


# ---------------------------------------------------------------- main
def main():
    lines = ['# gold_session - MGC=F intraday session windows (GC=F check)', '',
             'Rule: 1 contract, long/short from bar OPEN at local hour e_in to bar OPEN at the first later '
             'local hour e_out (<=26h). Time schedule -> causal. Fees = common.cme_fee (round trip, incl. 1 tick '
             'slippage/side). Data yfinance 1h, 2024-04-05 -> 2026-08-27. Walk-forward: select on fold 1, '
             'OOS = folds 2+3. Headline = OOS net.', '']
    inst = 'MGC'
    b = bars(inst)
    span = (b.index.min(), b.index.max())
    bounds = C.fold_bounds(span, 3)
    period = (span[0], span[1])
    lines += ['Fold edges: ' + ', '.join(f'[{s.date()} -> {e.date()})' for s, e in bounds), '']
    src = str(Path(__file__))
    result = {}

    # --- context: hour-of-day gross return heat map per fold (bar open->next bar open, $ per MGC)
    lines += ['## Context: mean gross $/bar by ET hour (MGC, open->next open, 1 contract) per fold', '',
              '| hour ET | fold1 mean | fold2 mean | fold3 mean | all mean | t(all) |', '|---|---:|---:|---:|---:|---:|']
    m = C.cme_multiplier(inst)
    nxt = b['open'].shift(-1)
    gap_ok = (b.index.to_series().shift(-1) - b.index.to_series()) <= pd.Timedelta(hours=2)
    ret = ((nxt - b['open']) * m).where(gap_ok)
    lab = C.fold_labels(b.index.to_series(), 3, *span)
    hod = {}
    for h in range(24):
        if h == 17:
            continue
        msk = (b['h_ET'] == h).values
        r = ret[msk]
        per = [r[lab[msk] == k].mean() for k in range(3)]
        tstat = r.mean() / r.std() * np.sqrt(r.notna().sum()) if r.std() > 0 else 0
        hod[h] = dict(f=[float(x) for x in per], all=float(r.mean()), t=float(tstat))
        lines.append(f'| {h:02d} | {per[0]:.1f} | {per[1]:.1f} | {per[2]:.1f} | {r.mean():.1f} | {tstat:.2f} |')
    lines.append('')
    result['hour_of_day'] = hod

    # --- walk-forward on the 20-cell grid
    run_fn = run_fn_factory(inst)
    best, oos, table = C.walk_forward(GRID, run_fn, span, n_folds=3, select_by='net', min_trades=10)
    res_oos = C.oos_result(oos, span, 3)
    print('BEST', best, fmt(res_oos))
    lines += [f'## Walk-forward (MGC): selected on fold 1 = `{vname(best)}`', '',
              f'OOS (folds 2+3): {fmt(res_oos)}', '',
              f'OOS fold2 = {res_oos["folds"][1]:.2f} (n={res_oos["fold_n"][1]}), '
              f'fold3 = {res_oos["folds"][2]:.2f} (n={res_oos["fold_n"][2]})', '']
    C.record_to_lab(STRAT, f'{vname(best)}_wf_oos', inst, '1h', best, res_oos, period, src,
                    notes='walk-forward OOS folds 2+3 (fold1 selection)')

    # --- in-sample grid table + full-period folds for every cell
    lines += ['## In-sample grid (fold 1 selection metrics) + full-period per-fold net (for sensitivity)', '',
              '| variant | is_n | is_net | is_pf | is_wr | is_sharpe | full_n | full_net | full_pf | f1 | f2 | f3 | oos(f2+f3) | sel |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    grid_rows = []
    for _, row in table.iterrows():
        p = GRID[int(row['idx'])]
        t_all = trades_for(p, inst)
        r_full = C.evaluate(t_all, 3, *span)
        r_is = C.evaluate(sub(t_all, *bounds[0]), 1)
        C.record_to_lab(STRAT, f'{vname(p)}_is_fold1', inst, '1h', p, r_is, bounds[0], src, notes='in-sample fold1 grid cell')
        C.record_to_lab(STRAT, f'{vname(p)}_full', inst, '1h', p, r_full, period, src, notes='full period, all 3 folds (not OOS)')
        f = r_full['folds']
        grid_rows.append(dict(variant=vname(p), is_n=r_is['n'], is_net=r_is['net'], is_pf=r_is['pf'],
                              full_n=r_full['n'], full_net=r_full['net'], full_pf=r_full['pf'],
                              f1=f[0], f2=f[1], f3=f[2], oos=f[1] + f[2], sel=bool(row['selected'])))
        lines.append(f"| {vname(p)} | {r_is['n']} | {r_is['net']:.0f} | {r_is['pf']:.2f} | {r_is['wr']:.2f} | "
                     f"{r_is['sharpe']:.2f} | {r_full['n']} | {r_full['net']:.0f} | {r_full['pf']:.2f} | "
                     f"{f[0]:.0f} | {f[1]:.0f} | {f[2]:.0f} | {f[1]+f[2]:.0f} | {'**X**' if row['selected'] else ''} |")
    lines.append('')
    result['grid'] = grid_rows

    # --- per-group walk-forward (best Asian / London / US on fold 1)
    lines += ['## Per-group walk-forward (best cell of each session group on fold 1 -> OOS)', '',
              '| group | selected | oos_n | oos_net | oos_pf | oos_wr | f2 | f3 |', '|---|---|---:|---:|---:|---:|---:|---:|']
    groups = {'asia': [g for g in GRID if g['session'].startswith('asia')],
              'london': [g for g in GRID if g['session'].startswith('lon')],
              'us': [g for g in GRID if g['session'].startswith('us')]}
    result['groups'] = {}
    for gname, gg in groups.items():
        gb, go, _ = C.walk_forward(gg, run_fn, span, 3, 'net', 10)
        gr = C.oos_result(go, span, 3)
        C.record_to_lab(STRAT, f'group_{gname}_{vname(gb)}_wf_oos', inst, '1h', gb, gr, period, src,
                        notes=f'per-group ({gname}) walk-forward OOS')
        result['groups'][gname] = dict(selected=vname(gb), **{k: gr[k] for k in ('n', 'net', 'pf', 'wr', 'folds')})
        lines.append(f"| {gname} | {vname(gb)} | {gr['n']} | {gr['net']:.0f} | {gr['pf']:.2f} | {gr['wr']:.2f} | "
                     f"{gr['folds'][1]:.0f} | {gr['folds'][2]:.0f} |")
    lines.append('')

    # --- sanity (a): timing shuffle. Same side + same duration, every other entry hour.
    tz, ei, eo = SESSIONS[best['session']]
    dur = (eo - ei) % 24
    oos_s, oos_e = bounds[1][0], bounds[2][1]
    shift_rows = []
    for h in range(24):
        p2 = dict(tz=tz, e_in=h, e_out=(h + dur) % 24, side=best['side'])
        t = sub(trades_for(p2, inst), oos_s, oos_e)
        r = C.oos_result(t, span, 3)
        shift_rows.append(dict(e_in=h, e_out=(h + dur) % 24, n=r['n'], net=r['net'], pf=r['pf']))
    sh = pd.DataFrame(shift_rows)
    actual = float(sh.loc[sh.e_in == ei, 'net'].iloc[0])
    rank = int((sh['net'] > actual).sum()) + 1
    lines += [f'## Sanity (a1): timing shuffle - same side/duration ({dur}h), every entry hour ({tz}), OOS net', '',
              '| e_in | e_out | n | net | pf |', '|---:|---:|---:|---:|---:|']
    for r in shift_rows:
        mark = ' **<- selected**' if r['e_in'] == ei else ''
        lines.append(f"| {r['e_in']} | {r['e_out']} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} |{mark}")
    lines += ['', f'Selected window ranks {rank}/{len(sh)} by OOS net among all same-duration windows; '
              f'mean of others = {sh.loc[sh.e_in != ei, "net"].mean():.0f}, '
              f'share of windows with net>0 = {(sh.net > 0).mean():.2f}.', '']
    result['timing_shuffle'] = dict(rank=rank, n_windows=len(sh), actual=actual,
                                    others_mean=float(sh.loc[sh.e_in != ei, 'net'].mean()),
                                    frac_positive=float((sh.net > 0).mean()))
    # (a2) random sign flips of the OOS trades (null: no directional information in the schedule)
    t = C.add_pnl(oos)
    g = t['gross_pnl'].values
    fee = t['fee_usd'].abs().values
    sims = np.array([(g * RNG.choice([-1, 1], size=len(g))).sum() - fee.sum() for _ in range(2000)])
    p_sign = float((sims >= res_oos['net']).mean())
    # (a3) random day-shuffle: same number of trades, random calendar legs of same window but shuffled side
    lines += [f'Sanity (a2): random sign-flip of OOS trades (2000 draws): actual net {res_oos["net"]:.0f}, '
              f'null mean {sims.mean():.0f}, sd {sims.std():.0f}, p(>=actual) = {p_sign:.3f}', '']
    result['sign_flip_p'] = p_sign

    # --- sanity (c): neighbours (entry +-1h, exit +-1h) OOS
    lines += ['## Sanity (c): neighbouring windows (entry +-1h, exit +-1h), OOS folds 2+3', '',
              '| e_in | e_out | n | net | pf | f2 | f3 |', '|---:|---:|---:|---:|---:|---:|---:|']
    neigh = []
    for di in (-1, 0, 1):
        for do in (-1, 0, 1):
            p2 = dict(tz=tz, e_in=(ei + di) % 24, e_out=(eo + do) % 24, side=best['side'])
            if p2['e_in'] == p2['e_out']:
                continue
            t = sub(trades_for(p2, inst), oos_s, oos_e)
            r = C.oos_result(t, span, 3)
            C.record_to_lab(STRAT, f'neighbour_{vname(p2)}_oos', inst, '1h', p2, r, period, src, notes='neighbour of selected, OOS')
            neigh.append(dict(e_in=p2['e_in'], e_out=p2['e_out'], n=r['n'], net=r['net'], pf=r['pf'], f2=r['folds'][1], f3=r['folds'][2]))
            mark = ' **<- selected**' if (di == 0 and do == 0) else ''
            lines.append(f"| {p2['e_in']} | {p2['e_out']} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} | {r['folds'][1]:.0f} | {r['folds'][2]:.0f} |{mark}")
    nd = pd.DataFrame(neigh)
    lines += ['', f'Neighbours with OOS net>0: {(nd.net > 0).sum()}/{len(nd)}; with PF>=1.2: {(nd.pf >= 1.2).sum()}/{len(nd)}.', '']
    result['neighbours'] = neigh

    # --- sanity (d'): GC=F check with GC fees, same selected window
    lines += ['## Check: same selected window on GC=F (GC fees $14 RT, x100)', '']
    tg = sub(trades_for(best, 'GC'), oos_s, oos_e)
    rg = C.oos_result(tg, span, 3)
    C.record_to_lab(STRAT, f'{vname(best)}_wf_oos', 'GC', '1h', best, rg, period, src, notes='GC check of MGC-selected window, OOS')
    lines += [f'GC OOS: {fmt(rg)}', '']
    result['gc_check'] = {k: rg[k] for k in ('n', 'net', 'pf', 'wr', 'folds')}

    # --- drift adjustment: is the window just capturing gold's bull-run drift pro-rata?
    bo = b[(b.index >= oos_s) & (b.index < oos_e)]
    tot_drift = float((bo['open'].iloc[-1] - bo['open'].iloc[0]) * m)
    n_days = (oos_e - oos_s).days
    # simpler: expected gross under uniform drift = total drift * (hours held / total hours in period)
    total_hours = len(bo)
    hours_held = dur * res_oos['n']
    exp_gross = tot_drift * hours_held / total_hours * best['side']
    lines += ['## Drift adjustment (OOS)', '',
              f'Gold moved {tot_drift:.0f} $/contract over the OOS period ({total_hours} bars). The selected window held '
              f'{hours_held} bar-hours ({hours_held/total_hours:.1%} of the time). Uniform-drift expectation for this side = '
              f'{exp_gross:.0f} gross; actual gross = {res_oos["gross"]:.0f}; excess over drift = {res_oos["gross"]-exp_gross:.0f}; '
              f'fees = {res_oos["fees"]:.0f}.', '']
    result['drift'] = dict(tot_drift=tot_drift, exp_gross=float(exp_gross), actual_gross=res_oos['gross'],
                           excess=float(res_oos['gross'] - exp_gross))

    # --- 5m descriptive check around the fixes (71 days only; NOT walk-forward)
    lines += ['## Descriptive 5m check (71d, 2026-06-17 -> 2026-08-27): +-30min around London fixes and pit open (gross $/MGC, mean per day)', '',
              '| window (London local) | n days | mean gross | t | sum |', '|---|---:|---:|---:|---:|']
    b5 = bars(inst, '5m')
    lon = b5.index.tz_convert(LON)
    b5 = b5.assign(mm=lon.hour * 60 + lon.minute, d=lon.date)
    def win5(m0, m1, label):
        rows = []
        for d, g in b5.groupby('d'):
            a = g[g['mm'] == m0]; z = g[g['mm'] == m1]
            if len(a) and len(z):
                rows.append((z['open'].iloc[0] - a['open'].iloc[0]) * m)
        s = pd.Series(rows)
        tt = s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 1 and s.std() > 0 else 0
        lines.append(f'| {label} | {len(s)} | {s.mean():.1f} | {tt:.2f} | {s.sum():.0f} |')
        return dict(n=len(s), mean=float(s.mean()) if len(s) else 0, t=float(tt))
    result['fix_5m'] = {
        'am_pre': win5(10*60, 10*60+30, '10:00 -> 10:30 (into AM fix)'),
        'am_post': win5(10*60+30, 11*60, '10:30 -> 11:00 (out of AM fix)'),
        'pm_pre': win5(14*60+30, 15*60, '14:30 -> 15:00 (into PM fix)'),
        'pm_post': win5(15*60, 15*60+30, '15:00 -> 15:30 (out of PM fix)'),
        'pm_pre60': win5(14*60, 15*60, '14:00 -> 15:00 (into PM fix, 1h)'),
        'pm_post60': win5(15*60, 16*60, '15:00 -> 16:00 (out of PM fix, 1h)'),
    }
    lines.append('')

    # --- verdict
    r = res_oos
    crit = dict(net_pos=r['net'] > 0, pf=r['pf'] >= 1.2, n=r['n'] >= 60,
                folds=all(f > 0 for f in r['folds'][1:]),
                shuffle=(rank <= 3 and p_sign < 0.05),
                neighbours=bool((nd.net > 0).mean() >= 0.75))
    if all(crit.values()):
        verdict = 'edge'
    elif r['net'] > 0:
        verdict = 'weak'
    else:
        verdict = 'none'
    lines += ['## Verdict', '', f'`{verdict}` - criteria: ' + ', '.join(f'{k}={v}' for k, v in crit.items()), '']
    result.update(best=best, best_name=vname(best), oos={k: r[k] for k in ('n', 'net', 'gross', 'fees', 'pf', 'wr', 'sharpe', 'max_dd', 'folds', 'fold_n', 'net_bps')},
                  criteria=crit, verdict=verdict, fold_edges=[(str(s), str(e)) for s, e in bounds])
    OUT_MD.write_text('\n'.join(lines))
    OUT_JSON.write_text(json.dumps(result, indent=1, default=str))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
