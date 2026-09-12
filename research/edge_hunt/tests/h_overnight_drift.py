"""Hypothesis: overnight vs intraday return asymmetry in CME micros (MNQ, MES,
MYM, MGC).  Hold long 16:00 ET (cash close) -> 09:00/10:00 ET next session, or
18:00 ET (Globex reopen) -> 09:00 ET, flat intraday; compare with intraday
(09:00 -> 16:00) and with the reverse side.  Filters: day-of-week, VIX regime.

Execution: 1 contract, market at the bar OPEN of the scheduled entry/exit hour
(time-based schedule, no bar-close signal, so no look-ahead).  Fee = CME
round-trip from common.FEES (commission + 1 tick slippage each side).
Data: yfinance 1h (874 days, 2024-04-05 -> 2026-08-27), Yahoo timestamps are
bar OPEN times in UTC -> converted to America/New_York.  The 17:00 ET
maintenance hour is absent (a handful of stray 1-lot 17:00 bars are dropped).
Walk-forward: parameters selected on fold 1 (calendar third), OOS = folds 2+3.
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

ET = 'America/New_York'
INSTS = ['MNQ', 'MES', 'MYM', 'MGC']
STRAT = 'overnight_drift'
OUT_MD = Path(__file__).with_suffix('.md')
RNG = np.random.default_rng(7)

# ---------------------------------------------------------------- data
_BARS: dict[str, pd.DataFrame] = {}


def bars(inst: str) -> pd.DataFrame:
    if inst not in _BARS:
        b = C.yf_bars(f'{inst}=F', '1h').copy()
        b = b[~b.index.duplicated()]
        et = b.index.tz_convert(ET)
        b['hour'] = et.hour
        b['date'] = et.date
        b['dow'] = et.dayofweek
        b = b[b['hour'] != 17]                     # stray maintenance-hour prints
        b = b[b['open'].notna() & (b['open'] > 0)]
        _BARS[inst] = b
    return _BARS[inst]


def vix_asof() -> pd.Series:
    """VIX daily close indexed by the time it becomes KNOWN (16:15 ET of its
    date), so an entry at 16:00 ET on day D only sees D-1's close."""
    v = C.yf_bars('^VIX', '1d')['close'].dropna()
    known = pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize(ET) + pd.Timedelta(hours=16, minutes=15)
                              for d in v.index]).tz_convert('UTC')
    return pd.Series(v.values, index=known).sort_index()


_VIX = None


def vix_at(times: pd.DatetimeIndex) -> np.ndarray:
    global _VIX
    if _VIX is None:
        _VIX = vix_asof()
    pos = _VIX.index.searchsorted(times, side='right') - 1
    out = np.full(len(times), np.nan)
    ok = pos >= 0
    out[ok] = _VIX.values[pos[ok]]
    return out


# ---------------------------------------------------------------- sessions
SESSIONS = {
    # name: (entry ET hour, exit ET hour, overnight?)
    'on_16_9':  (16, 9, True),
    'on_18_9':  (18, 9, True),
    'id_9_16':  (9, 16, False),
}


def session_legs(inst: str, e_in: int, e_out: int, overnight: bool) -> pd.DataFrame:
    """One row per scheduled leg: entry at open of first bar with hour==e_in on
    date D, exit at open of first bar with hour==e_out on the next session
    date (overnight) or the same date (intraday).  Legs with no matching exit
    bar within 4 calendar days (holidays) are dropped."""
    b = bars(inst)
    ent = b[b['hour'] == e_in]
    ex = b[b['hour'] == e_out]
    ex_times = ex.index.values
    ex_dates = np.array(ex['date'].tolist())
    rows = []
    for t, r in ent.iterrows():
        j = ex.index.searchsorted(t, side='right')
        if j >= len(ex):
            continue
        xt = ex.index[j]
        xd = ex_dates[j]
        if overnight:
            if xd <= r['date'] or (xt - t) > pd.Timedelta(days=4):
                continue
        else:
            if xd != r['date']:
                continue
        rows.append(dict(entry_time=t, exit_time=xt, entry_px=float(r['open']),
                         exit_px=float(ex['open'].iloc[j]), dow=int(r['dow']),
                         entry_date=r['date']))
    df = pd.DataFrame(rows)
    df['vix'] = vix_at(pd.DatetimeIndex(df['entry_time']))
    return df


_LEGS: dict[tuple, pd.DataFrame] = {}


def legs(inst, e_in, e_out, overnight):
    k = (inst, e_in, e_out, overnight)
    if k not in _LEGS:
        _LEGS[k] = session_legs(inst, e_in, e_out, overnight)
    return _LEGS[k]


def apply_filter(df: pd.DataFrame, filt: str, vix_thr: float = 20.0) -> pd.DataFrame:
    if filt == 'all':
        return df
    if filt == 'no_fri':          # no weekend holds (overnight) / skip Fridays (intraday)
        return df[df['dow'] != 4]
    if filt == 'vix_lt':
        return df[df['vix'] < vix_thr]
    if filt == 'vix_ge':
        return df[df['vix'] >= vix_thr]
    if filt == 'mon_only':
        return df[df['dow'] == 0]
    if filt == 'tue_thu':
        return df[df['dow'].isin([1, 2, 3])]
    raise ValueError(filt)


def make_trades(inst: str, session: str, side: int, filt: str, vix_thr: float = 20.0,
                e_in=None, e_out=None) -> pd.DataFrame:
    si, so, on = SESSIONS[session]
    if e_in is not None:
        si = e_in
    if e_out is not None:
        so = e_out
    df = apply_filter(legs(inst, si, so, on), filt, vix_thr)
    if len(df) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    rows = [C.cme_trade(r.entry_time, r.exit_time, side, r.entry_px, r.exit_px, 1, inst)
            for r in df.itertuples()]
    return pd.DataFrame(rows)


def run_fn_factory(insts):
    def run_fn(p, start, end):
        parts = []
        for inst in insts:
            t = make_trades(inst, p['session'], p['side'], p['filt'], p.get('vix_thr', 20.0),
                            p.get('e_in'), p.get('e_out'))
            if len(t):
                t = t[(t['entry_time'] >= start) & (t['entry_time'] < end)]
                parts.append(t)
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return run_fn


GRID = [dict(session=s, side=sd, filt=f)
        for s in SESSIONS for sd in (1, -1) for f in ('all', 'no_fri', 'vix_lt', 'vix_ge')]
assert len(GRID) == 24


def vname(p):
    return f"{p['session']}_{'L' if p['side'] > 0 else 'S'}_{p['filt']}"


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.0f} folds={[round(f) for f in r['folds']]}")


def asymmetry_check(span, bounds, lines):
    """Paired test of the actual hypothesis: overnight (D 16:00 -> D+1 09:00)
    minus intraday (D+1 09:00 -> 16:00) per date, OOS period only, plus the
    share of buy-and-hold captured by the overnight leg and the hour-of-day
    gross decomposition."""
    from scipy import stats
    oos_s, oos_e = bounds[1][0], bounds[2][1]
    hod = []
    lines += ["## Asymmetry test (OOS period): overnight minus intraday, paired by date", "",
              "| inst | pairs | on_gross | id_gross | buy&hold gross | on/bh | on mean | id mean | t(on-id) | p |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for inst in INSTS:
        m = C.cme_multiplier(inst)
        on = legs(inst, 16, 9, True); idd = legs(inst, 9, 16, False)
        on = on[(on.entry_time >= oos_s) & (on.entry_time < oos_e)]
        idd = idd[(idd.entry_time >= oos_s) & (idd.entry_time < oos_e)]
        on_r = (on.exit_px - on.entry_px) * m; id_r = (idd.exit_px - idd.entry_px) * m
        on_d = pd.Series(on_r.values, index=pd.to_datetime(on.exit_time).dt.tz_convert(ET).dt.date)
        id_d = pd.Series(id_r.values, index=idd.entry_date.values)
        pair = pd.concat([on_d.rename('on'), id_d.rename('id')], axis=1).dropna()
        diff = pair['on'] - pair['id']
        t, p = stats.ttest_1samp(diff, 0)
        b = bars(inst); bo = b[(b.index >= oos_s) & (b.index < oos_e)]
        bh = float((bo['close'].iloc[-1] - bo['open'].iloc[0]) * m)
        hb = bo.assign(ret=(bo['close'] - bo['open']) * m).groupby('hour')['ret'].sum()
        lines.append(f"| {inst} | {len(pair)} | {on_r.sum():.0f} | {id_r.sum():.0f} | {bh:.0f} | {on_r.sum()/bh:.2f} | "
                     f"{on_r.mean():.1f} | {id_r.mean():.1f} | {t:.2f} | {p:.3f} |")
        C.record_to_lab(STRAT, 'asym_paired_on_minus_id', inst, '1h', dict(on='16->9', id='9->16'),
                        dict(C.empty_result(), n=int(len(pair)), net=float(diff.sum()), wr=float((diff > 0).mean())),
                        period=(oos_s, oos_e), source=__file__, trust='estimated',
                        notes=f"paired overnight-minus-intraday gross USD/contract, OOS; t={t:.2f} p={p:.3f}; on_gross={on_r.sum():.0f} id_gross={id_r.sum():.0f} buyhold={bh:.0f}")
        hod.append(f"- {inst} hour-of-day gross sum (ET bar-open hour, OOS): " +
                   ", ".join(f"{h}:{v:.0f}" for h, v in hb.items()))
    lines += [""] + hod + [""]


INTERPRETATION = """## Interpretation

- Walk-forward picks long overnight 16:00->09:00 ET on fold 1 for every universe. OOS (2025-01-21 -> 2026-08-27)
  basket net +38.4k USD on 1 contract each (PF 1.23, WR 0.56, both OOS folds positive); MNQ +13.4k, MGC +11.1k,
  MES +3.3k, MYM +0.6k (MYM fold 2 negative).
- **It does not survive the shuffle test.** Random 17-hour windows with the same hold length earn comparable or
  larger OOS net (basket: the overnight window beats only 67% of 21 random-hour windows; MES/MYM only 24%).
  The PnL is market beta from a strongly up-trending sample, not a time-of-day effect.
- The direct paired test of the hypothesis (overnight minus intraday gross, same date, OOS) is insignificant
  for the equity micros: MNQ t=0.94 p=0.35, MES t=0.27 p=0.79, MYM t=-0.24 p=0.81. Overnight captured 91% /
  58% / 31% of buy-and-hold for MNQ / MES / MYM, i.e. roughly pro-rata to time held. Only MGC shows a real
  asymmetry (t=2.15 p=0.03; overnight = 119% of buy-and-hold, intraday ~0) - one significant result out of four
  instruments, borderline after multiple comparisons, and MGC's gross is concentrated in Asia/London hours
  (02, 07, 18, 20 ET), not at the US cash-close/open transition.
- Short-intraday (the tradable "reverse") loses money OOS on the basket (id_9_16_S_all folds -11.8k / +1.0k).
  VIX>=20 intraday-long / VIX<20 intraday-short look good in-sample but are opposite-signed regime bets with
  n=100-500 and were not selected; treat as noise.
- Neighbours (+-1h entry/exit) are stable, as expected for a beta exposure; the no_fri filter (drop weekend
  holds) *hurts* on equities, meaning the weekend carry was a large part of the OOS PnL.
- The 5m exact 16:00->09:30 check on the last 70 days agrees in sign (overnight positive, intraday negative for
  the equity micros) but is 49 trades and descriptive only.

Verdict: weak (positive, fold-consistent OOS net but fails the shuffle check; the effect is beta, not timing).
Do not deploy as a standalone strategy.
"""

def main():
    lines = ["# Overnight drift - CME micros (MNQ/MES/MYM/MGC)", "",
             "Execution: 1 contract, market at bar open of the scheduled hour (yfinance 1h, ET), "
             "CME round-trip fee from common.FEES. Walk-forward: params picked on fold 1 (calendar third), "
             "OOS = folds 2+3.", ""]
    # common time span across instruments
    starts = [bars(i).index.min() for i in INSTS]
    ends = [bars(i).index.max() for i in INSTS]
    span = (max(starts), min(ends))
    bounds = C.fold_bounds(span, 3)
    lines.append(f"Data span {span[0]:%Y-%m-%d} -> {span[1]:%Y-%m-%d}; folds: " +
                 ", ".join(f"[{s:%Y-%m-%d},{e:%Y-%m-%d})" for s, e in bounds))
    lines.append("")
    period = (span[0], span[1])

    results = {}
    universes = {i: [i] for i in INSTS}
    universes['BASKET'] = INSTS
    for uname, insts in universes.items():
        run_fn = run_fn_factory(insts)
        rep = C.full_report(GRID, run_fn, span, n_folds=3, min_trades=10)
        best, oos, table = rep['best_params'], rep['oos'], rep['insample']
        results[uname] = rep
        print(f"\n=== {uname} === best on fold1: {best}")
        print("OOS(2+3):", fmt(oos))
        # in-sample grid + full-period 3-fold eval of every cell -> lab
        full_rows = []
        for i, p in enumerate(GRID):
            tr = run_fn(p, span[0], span[1] + pd.Timedelta(hours=1))
            r = C.evaluate(tr, 3, start=span[0], end=span[1])
            full_rows.append(dict(variant=vname(p), n=r['n'], net=r['net'], pf=r['pf'], wr=r['wr'],
                                  sharpe=r['sharpe'], f1=r['folds'][0], f2=r['folds'][1], f3=r['folds'][2],
                                  is_net=table.loc[i, 'is_net'], is_n=table.loc[i, 'is_n'],
                                  is_pf=table.loc[i, 'is_pf'], sel=bool(table.loc[i, 'selected'])))
            C.record_to_lab(STRAT, f"grid_{vname(p)}", uname, '1h', dict(p, universe=insts), r,
                            period=period, source=__file__,
                            notes=f"grid cell; fold1 is in-sample selection set; is_net={table.loc[i,'is_net']:.2f}")
        ft = pd.DataFrame(full_rows)
        print(ft.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        C.record_to_lab(STRAT, 'WF_OOS_' + vname(best), uname, '1h', dict(best, universe=insts), oos,
                        period=period, source=__file__,
                        notes=f"walk-forward OOS (folds 2+3), selected on fold 1")
        lines += [f"## {uname}", "", f"Selected on fold 1: `{best}`  ",
                  f"**OOS folds 2+3**: {fmt(oos)}", "",
                  "In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):", "",
                  "| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in full_rows:
            lines.append(f"| {r['variant']} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} | {r['wr']:.2f} | "
                         f"{r['sharpe']:.2f} | {r['f1']:.0f} | {r['f2']:.0f} | {r['f3']:.0f} | {r['is_net']:.0f} | "
                         f"{'*' if r['sel'] else ''} |")
        lines.append("")

    # ------------------------------------------------------------ sanity checks
    lines += ["## Sanity checks", ""]
    for uname in ['BASKET'] + INSTS:
        rep = results[uname]
        best = rep['best_params']
        insts = universes[uname]
        run_fn = run_fn_factory(insts)
        oos = rep['oos']
        oos_start, oos_end = bounds[1][0], bounds[2][1]
        si, so, on = SESSIONS[best['session']]

        # (a) shuffle: same hold length / same side / same filter, random entry hour
        hold = (so - si) % 24
        shuf = []
        for h in range(24):
            if h == si or h == 17 or (h + hold) % 24 == 17:
                continue
            e_out = (h + hold) % 24
            on_ = e_out <= h              # exit on the next calendar/session date
            for inst in insts:
                pass
            # build legs by hand using make_trades with overridden hours; overnight flag from SESSIONS
            # -> use direct session_legs via temporary session entry
            SESSIONS['_shuf'] = (h, e_out, on_)
            p = dict(best, session='_shuf')
            tr = run_fn(p, oos_start, oos_end)
            r = C.evaluate(tr, 3, start=span[0], end=span[1])
            shuf.append(dict(e_in=h, e_out=e_out, n=r['n'], net=r['net'], pf=r['pf']))
            del SESSIONS['_shuf']
        sdf = pd.DataFrame(shuf)
        pct = float((sdf['net'] < oos['net']).mean())
        # (a2) random day-subset / sign permutation of OOS trades: permute the entry_time <-> pnl pairing
        tr = C.add_pnl(rep['oos_trades'])
        perm_nets = []
        for _ in range(500):
            sgn = RNG.choice([1, -1], size=len(tr))
            perm_nets.append(float((tr['gross_pnl'].values * sgn - tr['fee_usd'].abs().values).sum()))
        perm_p = float(np.mean(np.array(perm_nets) >= oos['net']))
        C.record_to_lab(STRAT, 'shuffle_randhour_' + vname(best), uname, '1h', dict(best, check='shuffle'),
                        dict(C.empty_result(), n=int(sdf['n'].sum()), net=float(sdf['net'].mean())),
                        period=(oos_start, oos_end), source=__file__,
                        notes=f"mean OOS net over {len(sdf)} random entry hours (same hold); actual={oos['net']:.2f} pctile={pct:.2f}; sign-perm p={perm_p:.3f}",
                        trust='estimated')

        # (c) neighbours: +-1h on entry / exit, vix thr +-5
        nb = []
        for de, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ei, eo = si + de, so + dx
            if ei == 17 or eo == 17:
                continue
            SESSIONS['_nb'] = (ei, eo, on)
            p = dict(best, session='_nb')
            tr = run_fn(p, oos_start, oos_end)
            r = C.evaluate(tr, 3, start=span[0], end=span[1])
            nb.append(dict(what=f"e_in={ei} e_out={eo}", n=r['n'], net=r['net'], pf=r['pf'], folds=[round(f) for f in r['folds'][1:]]))
            C.record_to_lab(STRAT, f"nb_{vname(best)}_in{ei}_out{eo}", uname, '1h', dict(best, e_in=ei, e_out=eo), r,
                            period=(oos_start, oos_end), source=__file__, notes='neighbour check, OOS period only')
            del SESSIONS['_nb']
        if best['filt'].startswith('vix'):
            for thr in (15.0, 25.0):
                p = dict(best, vix_thr=thr)
                tr = run_fn(p, oos_start, oos_end)
                r = C.evaluate(tr, 3, start=span[0], end=span[1])
                nb.append(dict(what=f"vix_thr={thr}", n=r['n'], net=r['net'], pf=r['pf'], folds=[round(f) for f in r['folds'][1:]]))
                C.record_to_lab(STRAT, f"nb_{vname(best)}_thr{int(thr)}", uname, '1h', p, r,
                                period=(oos_start, oos_end), source=__file__, notes='neighbour check, OOS period only')
        # neighbouring filters
        for f in ('all', 'no_fri', 'vix_lt', 'vix_ge'):
            if f == best['filt']:
                continue
            p = dict(best, filt=f)
            tr = run_fn(p, oos_start, oos_end)
            r = C.evaluate(tr, 3, start=span[0], end=span[1])
            nb.append(dict(what=f"filt={f}", n=r['n'], net=r['net'], pf=r['pf'], folds=[round(f) for f in r['folds'][1:]]))
        ndf = pd.DataFrame(nb)
        print(f"\n[{uname}] shuffle: actual OOS net {oos['net']:.2f} beats {pct:.0%} of {len(sdf)} random-hour windows; "
              f"sign-perm p={perm_p:.3f}")
        print(sdf.sort_values('net', ascending=False).head(6).to_string(index=False))
        print(ndf.to_string(index=False))
        lines += [f"### {uname}: `{vname(best)}`", "",
                  f"- Shuffle (a): actual OOS net **{oos['net']:.0f}** beats {pct:.0%} of {len(sdf)} random-hour windows "
                  f"(same hold length, same side/filter); random-hour mean {sdf['net'].mean():.0f}, "
                  f"best {sdf['net'].max():.0f} @ e_in={int(sdf.loc[sdf['net'].idxmax(),'e_in'])}. "
                  f"Sign-permutation p={perm_p:.3f} (500 draws).",
                  f"- Sub-period (b): OOS folds = {[round(f) for f in oos['folds'][1:]]}, n per fold {oos['fold_n'][1:]}",
                  "- Neighbours (c), OOS period only:", "",
                  "| variant | n | net | pf | folds2,3 |", "|---|---:|---:|---:|---|"]
        for r in nb:
            lines.append(f"| {r['what']} | {r['n']} | {r['net']:.0f} | {r['pf']:.2f} | {r['folds']} |")
        lines.append("")

    # ------------------------------------------------------------ 5m exact-timing check (60d, descriptive only)
    lines += ["## 5m exact 16:00->09:30 check (last ~70 days, descriptive, no folds)", "",
              "| inst | n | on_16:00->09:30 net | pf | id_09:30->16:00 net | pf |", "|---|---:|---:|---:|---:|---:|"]
    for inst in INSTS:
        b5 = C.yf_bars(f'{inst}=F', '5m')
        et = b5.index.tz_convert(ET)
        hm = et.hour * 100 + et.minute
        dates = pd.Series(et.date, index=b5.index)
        e16 = b5[hm == 1600]; o930 = b5[hm == 930]
        rows_on, rows_id = [], []
        for t, r in e16.iterrows():
            j = o930.index.searchsorted(t, side='right')
            if j < len(o930) and (o930.index[j] - t) <= pd.Timedelta(days=4):
                rows_on.append(C.cme_trade(t, o930.index[j], 1, float(r['open']), float(o930['open'].iloc[j]), 1, inst))
        for t, r in o930.iterrows():
            j = e16.index.searchsorted(t, side='right')
            if j < len(e16) and dates[e16.index[j]] == dates[t]:
                rows_id.append(C.cme_trade(t, e16.index[j], 1, float(r['open']), float(e16['open'].iloc[j]), 1, inst))
        ron = C.evaluate(pd.DataFrame(rows_on)); rid = C.evaluate(pd.DataFrame(rows_id))
        C.record_to_lab(STRAT, 'chk5m_on_1600_0930_L_all', inst, '5m', dict(session='on_1600_0930', side=1), ron,
                        period=(b5.index.min(), b5.index.max()), source=__file__, notes='5m exact timing, 60d, descriptive')
        C.record_to_lab(STRAT, 'chk5m_id_0930_1600_L_all', inst, '5m', dict(session='id_0930_1600', side=1), rid,
                        period=(b5.index.min(), b5.index.max()), source=__file__, notes='5m exact timing, 60d, descriptive')
        lines.append(f"| {inst} | {ron['n']} | {ron['net']:.0f} | {ron['pf']:.2f} | {rid['net']:.0f} | {rid['pf']:.2f} |")
        print(f"5m {inst}: overnight {fmt(ron)} | intraday {fmt(rid)}")
    lines.append("")

    asymmetry_check(span, bounds, lines)

    # summary
    lines += ["## OOS summary", "", "| universe | selected | OOS n | OOS net | pf | wr | sharpe | fold2 | fold3 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for u, rep in results.items():
        o = rep['oos']
        lines.append(f"| {u} | {vname(rep['best_params'])} | {o['n']} | {o['net']:.0f} | {o['pf']:.2f} | {o['wr']:.2f} | "
                     f"{o['sharpe']:.2f} | {o['folds'][1]:.0f} | {o['folds'][2]:.0f} |")
    lines.append("")
    lines.append(INTERPRETATION)
    OUT_MD.write_text("\n".join(lines))
    json.dump({u: dict(best=rep['best_params'], oos={k: v for k, v in rep['oos'].items()})
               for u, rep in results.items()}, open(OUT_MD.with_suffix('.json'), 'w'), default=str, indent=1)
    print("wrote", OUT_MD)


if __name__ == '__main__':
    main()
