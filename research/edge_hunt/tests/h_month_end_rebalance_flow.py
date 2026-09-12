"""Hypothesis (round 3): month-end pension / target-weight rebalancing flow in
CME index futures.

Arms (all fills at the daily settlement close of the signal day, 1 contract,
taker; fee = common.cme_fee round trip):
  A  unconditional turn-of-month: long close T-1 -> close T+k
  B  conditional pressure: at close T-3 compute MTD = P[T-3]/P[T_prev]-1.
       MTD >= +thr : short T-3 -> T-1, then long T-1 -> T+k
       MTD <= -thr : long  T-3 -> T+k
       else flat
  C  'dash for cash': short T-8 -> T-2, long T-1 -> T+k
T = last SPY session of the calendar month (cash-equity calendar drives the
pension flow).  k in {2,3,4}, thr in {2,3,4}% -> 15-cell grid.

Data: yfinance daily continuous ES=F / NQ=F / MES=F / MNQ=F / GC=F plus SPY /
QQQ / GLD as roll-free cash cross-checks.  Yahoo's =F splice has a level jump
on the quarterly roll (3rd Friday of Mar/Jun/Sep/Dec and the following
session).  Those two days are flagged by calendar and their log-return is
replaced by the cash proxy's (SPY for ES/MES, QQQ for NQ/MNQ) in a
roll-adjusted return series; every trade's PnL uses the adjusted returns and
the number of windows that touched a roll day is reported.  GC has no clean
calendar roll rule (rolls near month-end), so GLD is the roll-free gold control.

Causality: every entry/exit is at the close of a session whose date is known
in advance (T-8, T-3, T-1, T+k are calendar facts); the only computed signal
(MTD) uses closes up to and including the fill bar's own close, which is the
same price the order is filled at (MOC/settlement).  No look-ahead.

Walk-forward: parameters selected on fold 1 (calendar third of 2016-08 ..
2026-08), OOS = folds 2+3.  Gates: (i) pro-rata buy-and-hold drift of the
same instrument over the same fold, (ii) 1,000 random same-length, same-side
windows in the same fold (this is also the 'shuffle the signal timing' test),
(iii) for arm B, 1,000 permutations of the MTD signal across months.
"""
from __future__ import annotations
import sys, json, itertools, math
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

ET = 'America/New_York'
STRAT = 'month_end_rebalance_flow'
OUT_MD = Path(__file__).with_suffix('.md')
OUT_JSON = Path(__file__).with_suffix('.json')
RNG = np.random.default_rng(11)
N_RAND = 1000
CUTOFF = pd.Timestamp('2026-08-26')          # last complete daily bar in cache
ETF_NOTIONAL = 100_000.0                    # $ per ETF cross-check trade
ETF_FEE_RT = 0.0001                         # 1 bp round trip for the ETF cross-check

INST = {
    'ES':  dict(sym='ES=F',  proxy='SPY', cme=True),
    'NQ':  dict(sym='NQ=F',  proxy='QQQ', cme=True),
    'MES': dict(sym='MES=F', proxy='SPY', cme=True),
    'MNQ': dict(sym='MNQ=F', proxy='QQQ', cme=True),
    'GC':  dict(sym='GC=F',  proxy=None,  cme=True),
    'SPY': dict(sym='SPY',   proxy=None,  cme=False),
    'QQQ': dict(sym='QQQ',   proxy=None,  cme=False),
    'GLD': dict(sym='GLD',   proxy=None,  cme=False),
}

# ---------------------------------------------------------------- calendar

def _daily(sym: str) -> pd.Series:
    s = C.yf_bars(sym, '1d')['close'].dropna()
    s.index = pd.DatetimeIndex(pd.to_datetime(s.index.date))
    s = s[~s.index.duplicated(keep='last')]
    return s[s.index <= CUTOFF]


CAL = _daily('SPY').index                                  # cash-equity sessions
CAL_POS = pd.Series(np.arange(len(CAL)), index=CAL)


def third_friday(y: int, m: int) -> pd.Timestamp:
    d = pd.Timestamp(year=y, month=m, day=15)
    return d + pd.Timedelta(days=(4 - d.dayofweek) % 7)


def roll_days() -> set:
    """Yahoo =F splice days for equity index futures: 3rd Friday of the quarter
    month and the following session."""
    out = set()
    for y in range(CAL[0].year, CAL[-1].year + 1):
        for m in (3, 6, 9, 12):
            f = third_friday(y, m)
            pos = CAL.searchsorted(f)
            for p in (pos, pos + 1):
                if 0 <= p < len(CAL):
                    out.add(CAL[p])
    return out


ROLL = roll_days()

_SER: dict[str, dict] = {}


def series(inst: str) -> dict:
    """close (raw, on CAL, ffilled), lr_raw, lr_adj (roll-adjusted), is_roll."""
    if inst in _SER:
        return _SER[inst]
    cfg = INST[inst]
    raw = _daily(cfg['sym'])
    first = raw.index[0]
    close = raw.reindex(CAL)
    close = close[close.index >= first]
    n_ff = int(close.isna().sum())
    close = close.ffill()
    lr = np.log(close).diff()
    is_roll = pd.Series([d in ROLL for d in close.index], index=close.index) if cfg['proxy'] else pd.Series(False, index=close.index)
    lr_adj = lr.copy()
    if cfg['proxy']:
        pr = np.log(_daily(cfg['proxy']).reindex(close.index).ffill()).diff()
        lr_adj[is_roll] = pr[is_roll]
    _SER[inst] = dict(close=close, lr_raw=lr, lr_adj=lr_adj, is_roll=is_roll, n_ffill=n_ff, first=first)
    return _SER[inst]


def month_ends(first: pd.Timestamp) -> list[int]:
    """CAL positions of T (last session of each complete calendar month)."""
    months = pd.Series(CAL).dt.to_period('M')
    last_pos = months.groupby(months).apply(lambda g: g.index[-1])
    out = []
    for per, pos in last_pos.items():
        if per == months.iloc[0] or per == months.iloc[-1]:
            continue                                  # partial edge months
        if CAL[pos] < first + pd.Timedelta(days=45):
            continue                                  # need a previous month-end for MTD
        out.append(int(pos))
    return out


# ---------------------------------------------------------------- trades

def _ts(d: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize(ET).tz_convert('UTC')


def _trade(inst: str, i0: int, i1: int, side: int, S: dict) -> dict | None:
    """Trade entered at close of CAL[i0], exited at close of CAL[i1] using the
    roll-adjusted return chain; entry_px is the raw close."""
    close, lr = S['close'], S['lr_adj']
    if i0 < 0 or i1 >= len(CAL) or CAL[i0] not in close.index or CAL[i1] not in close.index:
        return None
    seg = lr.loc[CAL[i0 + 1]:CAL[i1]]
    if seg.isna().any() or len(seg) != i1 - i0:
        return None
    e_px = float(close.loc[CAL[i0]])
    x_px = e_px * math.exp(float(seg.sum()))
    touched = int(S['is_roll'].loc[CAL[i0 + 1]:CAL[i1]].sum())
    if INST[inst]['cme']:
        row = C.cme_trade(_ts(CAL[i0]), _ts(CAL[i1]), side, e_px, x_px, 1, inst)
    else:
        qty = ETF_NOTIONAL / e_px
        row = dict(entry_time=_ts(CAL[i0]), exit_time=_ts(CAL[i1]), side=side, entry_px=e_px,
                   exit_px=x_px, qty=qty, notional_usd=ETF_NOTIONAL,
                   fee_usd=ETF_FEE_RT * ETF_NOTIONAL, instrument=inst, multiplier=1.0)
    row.update(sessions=i1 - i0, roll_touch=touched, month=str(CAL[i0 + 1].to_period('M')))
    return row


_CACHE: dict[tuple, pd.DataFrame] = {}


def build_trades(inst: str, params: dict, mtd_override: pd.Series | None = None) -> pd.DataFrame:
    key = (inst, json.dumps(params, sort_keys=True), mtd_override is None)
    if key in _CACHE and mtd_override is None:
        return _CACHE[key]
    S = series(inst)
    arm, k = params['arm'], int(params['k'])
    thr = float(params.get('thr', 0)) / 100.0
    rows = []
    mes = month_ends(S['first'])
    for j, iT in enumerate(mes):
        if iT + k >= len(CAL) or iT - 8 < 0:
            continue
        if arm == 'A':
            t = _trade(inst, iT - 1, iT + k, +1, S)
            rows += [t] if t else []
        elif arm == 'C':
            for (a, b, s) in ((iT - 8, iT - 2, -1), (iT - 1, iT + k, +1)):
                t = _trade(inst, a, b, s, S)
                rows += [t] if t else []
        elif arm == 'B':
            if j == 0:
                continue
            iP = mes[j - 1]
            close = S['close']
            if CAL[iP] not in close.index or CAL[iT - 3] not in close.index:
                continue
            mtd = float(close.loc[CAL[iT - 3]] / close.loc[CAL[iP]] - 1.0)
            if mtd_override is not None:
                mtd = float(mtd_override.loc[CAL[iT]])
            if mtd >= thr:
                legs = ((iT - 3, iT - 1, -1), (iT - 1, iT + k, +1))
            elif mtd <= -thr:
                legs = ((iT - 3, iT + k, +1),)
            else:
                legs = ()
            for (a, b, s) in legs:
                t = _trade(inst, a, b, s, S)
                if t:
                    t['mtd'] = mtd
                    rows.append(t)
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    if mtd_override is None:
        _CACHE[key] = df
    return df


def make_run(insts: list[str]):
    def run(params, start, end):
        parts = [build_trades(i, params) for i in insts]
        df = pd.concat([p for p in parts if len(p)], ignore_index=True) if any(len(p) for p in parts) else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
        if len(df):
            df = df[(df['entry_time'] >= start) & (df['entry_time'] < end)].reset_index(drop=True)
        return df
    return run


GRID = ([dict(arm='A', k=k) for k in (2, 3, 4)]
        + [dict(arm='B', thr=t, k=k) for t in (2, 3, 4) for k in (2, 3, 4)]
        + [dict(arm='C', k=k) for k in (2, 3, 4)])


def pname(p: dict) -> str:
    return p['arm'] + ('_thr%d' % p['thr'] if 'thr' in p else '') + '_k%d' % p['k']


# ---------------------------------------------------------------- gates

def drift_baseline(trades: pd.DataFrame, times) -> float:
    """Expected net if each trade only earned the instrument's pro-rata
    buy-and-hold drift (mean daily log return of that instrument over the
    trade's own fold) for the same number of sessions."""
    if not len(trades):
        return 0.0
    bounds = C.fold_bounds(times, 3)
    exp = 0.0
    for _, t in trades.iterrows():
        S = series(t['instrument'])
        lr = S['lr_adj']
        f = [b for b in bounds if b[0] <= t['entry_time'] < b[1]]
        s, e = f[0] if f else bounds[-1]
        mu = lr[(lr.index >= s.tz_convert(ET).tz_localize(None).normalize()) &
                (lr.index < e.tz_convert(ET).tz_localize(None).normalize())].mean()
        exp += t['side'] * t['notional_usd'] * (math.exp(mu * t['sessions']) - 1.0) - abs(t['fee_usd'])
    return float(exp)


def random_windows(trades: pd.DataFrame, times, n=N_RAND) -> dict:
    """Null: each trade replaced by a random same-length, same-side window of
    the same instrument inside the same fold.  Returns p-value etc."""
    if not len(trades):
        return dict(p=1.0, mean=0.0, sd=0.0, z=0.0, actual=0.0)
    bounds = C.fold_bounds(times, 3)
    tot = np.zeros(n)
    actual = 0.0
    for _, t in trades.iterrows():
        S = series(t['instrument'])
        lr = S['lr_adj'].dropna()
        f = [b for b in bounds if b[0] <= t['entry_time'] < b[1]]
        s, e = f[0] if f else bounds[-1]
        seg = lr[(lr.index >= s.tz_convert(ET).tz_localize(None).normalize()) &
                 (lr.index < e.tz_convert(ET).tz_localize(None).normalize())].values
        L = int(t['sessions'])
        cs = np.concatenate([[0.0], np.cumsum(seg)])
        starts = RNG.integers(0, len(seg) - L, size=n)
        r = np.exp(cs[starts + L] - cs[starts]) - 1.0
        tot += t['side'] * t['notional_usd'] * r - abs(t['fee_usd'])
        m = 1.0 if t['instrument'] in ('SPY', 'QQQ', 'GLD') else C.cme_multiplier(t['instrument'])
        actual += t['side'] * (t['exit_px'] - t['entry_px']) * t['qty'] * m - abs(t['fee_usd'])
    sd = tot.std(ddof=1)
    return dict(p=float((tot >= actual).mean()), mean=float(tot.mean()), sd=float(sd),
                z=float((actual - tot.mean()) / sd) if sd > 0 else 0.0, actual=float(actual))


def mtd_permutation(insts: list[str], params: dict, start, end, n=N_RAND) -> dict:
    """Arm B only: permute the MTD signal across months (keeps the calendar
    legs but scrambles which months get which condition)."""
    actual = 0.0
    real = {}
    for inst in insts:
        S = series(inst)
        mes = month_ends(S['first'])
        vals = {}
        for j in range(1, len(mes)):
            iT, iP = mes[j], mes[j - 1]
            close = S['close']
            if CAL[iP] in close.index and CAL[iT - 3] in close.index:
                vals[CAL[iT]] = float(close.loc[CAL[iT - 3]] / close.loc[CAL[iP]] - 1.0)
        real[inst] = pd.Series(vals)
        tr = build_trades(inst, params)
        tr = tr[(tr['entry_time'] >= start) & (tr['entry_time'] < end)]
        actual += C.evaluate(tr)['net'] if len(tr) else 0.0
    nets = np.zeros(n)
    for r in range(n):
        tot = 0.0
        for inst in insts:
            v = real[inst]
            perm = pd.Series(RNG.permutation(v.values), index=v.index)
            tr = build_trades(inst, params, mtd_override=perm)
            if len(tr):
                tr = tr[(tr['entry_time'] >= start) & (tr['entry_time'] < end)]
                tot += C.evaluate(tr)['net'] if len(tr) else 0.0
        nets[r] = tot
    sd = nets.std(ddof=1)
    return dict(p=float((nets >= actual).mean()), mean=float(nets.mean()), sd=float(sd),
                z=float((actual - nets.mean()) / sd) if sd > 0 else 0.0, actual=float(actual))


# ---------------------------------------------------------------- 1h tradability

def hourly_check(inst: str, params: dict) -> dict:
    """Re-run the selected rule for 2024-04..2026-08 with fills at the OPEN of
    the 16:00 ET hourly bar (the price at the cash close) instead of the daily
    settlement close; compare."""
    h = C.yf_bars(INST[inst]['sym'], '1h')
    h = h[~h.index.duplicated()]
    et = h.index.tz_convert(ET)
    b = h[et.hour == 16]
    p16 = pd.Series(b['open'].values, index=pd.DatetimeIndex(pd.to_datetime(et[et.hour == 16].date)))
    p16 = p16[~p16.index.duplicated(keep='first')]
    S = series(inst)
    dc = S['close'].reindex(p16.index).dropna()
    both = pd.concat([p16.rename('h16'), dc.rename('dc')], axis=1).dropna()
    diff_bps = (both['h16'] / both['dc'] - 1) * 1e4
    tr = build_trades(inst, params)
    tr = tr[tr['entry_time'] >= pd.Timestamp('2024-05-01', tz='UTC')].copy()
    rows = []
    for _, t in tr.iterrows():
        d0 = t['entry_time'].tz_convert(ET).normalize().tz_localize(None)
        d1 = t['exit_time'].tz_convert(ET).normalize().tz_localize(None)
        if d0 in p16.index and d1 in p16.index and not S['is_roll'].loc[d0:d1].any():
            rows.append(C.cme_trade(t['entry_time'], t['exit_time'], t['side'], float(p16[d0]), float(p16[d1]), 1, inst))
    tr_h = pd.DataFrame(rows)
    tr_d = tr[tr['roll_touch'] == 0]
    return dict(n_days=int(len(both)), med_abs_bps=float(diff_bps.abs().median()),
                p90_abs_bps=float(diff_bps.abs().quantile(0.9)), mean_bps=float(diff_bps.mean()),
                daily_close=C.evaluate(tr_d) if len(tr_d) else C.empty_result(),
                h16_fill=C.evaluate(tr_h) if len(tr_h) else C.empty_result())


# ---------------------------------------------------------------- main

def fmt(r: dict) -> str:
    return (f"n={r['n']} net=${r['net']:,.0f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:.2f} "
            f"bps={r['net_bps']:.1f} folds={[round(x) for x in r['folds']]} fold_n={r['fold_n']}")


def run_set(label: str, insts: list[str], grid: list[dict], times, md: list[str], results: dict,
            do_gates=True) -> dict:
    run = make_run(insts)
    best, oos, table = C.walk_forward(grid, run, times, n_folds=3, min_trades=10)
    res = C.oos_result(oos, times, 3)
    bounds = C.fold_bounds(times, 3)
    inst_label = '+'.join(insts)
    # in-sample grid rows -> lab + OOS-per-cell for sensitivity (NOT selected on)
    table['oos_net'] = np.nan
    table['oos_n'] = 0
    table['oos_pf'] = np.nan
    table['oos_folds'] = None
    for i, p in enumerate(grid):
        f1 = run(p, bounds[0][0], bounds[0][1])
        r1 = C.evaluate(f1, n_folds=1)
        C.record_to_lab(STRAT, f'IS_{label}_{pname(p)}', inst_label, '1d', p, r1,
                        period=bounds[0], source=__file__, notes='fold-1 in-sample grid cell')
        o = pd.concat([run(p, s, e) for (s, e) in bounds[1:]], ignore_index=True)
        ro = C.oos_result(o, times, 3) if len(o) else C.empty_result()
        table.loc[i, 'oos_net'] = ro['net']; table.loc[i, 'oos_n'] = ro['n']; table.loc[i, 'oos_pf'] = ro['pf']
        table.at[i, 'oos_folds'] = [round(x) for x in ro['folds'][1:]]
    gates = {}
    if do_gates and len(oos):
        gates['drift_baseline'] = drift_baseline(oos, times)
        gates['random'] = random_windows(oos, times)
        if best['arm'] == 'B':
            gates['mtd_perm'] = mtd_permutation(insts, best, bounds[1][0], bounds[2][1])
        gates['roll_touch'] = int(oos['roll_touch'].sum())
    C.record_to_lab(STRAT, f'OOS_{label}', inst_label, '1d', best, res,
                    period=(bounds[1][0], bounds[2][1]), source=__file__,
                    baseline_net=gates.get('random', {}).get('mean'),
                    notes=f"walk-forward OOS folds 2+3; selected on fold 1; gates={json.dumps(gates, default=float)}")
    print(f"\n=== {label} [{inst_label}] best={pname(best)}")
    print("  OOS:", fmt(res))
    if gates:
        print("  gates:", json.dumps(gates, default=lambda o: round(float(o), 3)))
    md.append(f"\n### {label} — {inst_label}\n")
    md.append(f"Selected on fold 1: **{pname(best)}**  \nOOS (folds 2+3): {fmt(res)}\n")
    if gates:
        g = gates
        md.append(f"Gates: pro-rata drift baseline = ${g['drift_baseline']:,.0f} (excess = ${res['net']-g['drift_baseline']:,.0f}); "
                  f"random same-length windows: mean ${g['random']['mean']:,.0f}, sd ${g['random']['sd']:,.0f}, z={g['random']['z']:.2f}, p={g['random']['p']:.3f}; "
                  + (f"MTD permutation: mean ${g['mtd_perm']['mean']:,.0f}, z={g['mtd_perm']['z']:.2f}, p={g['mtd_perm']['p']:.3f}; " if 'mtd_perm' in g else '')
                  + f"OOS windows touching a roll day: {g['roll_touch']}\n")
    md.append("\n| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |\n|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|")
    for _, r in table.iterrows():
        p = grid[int(r['idx'])]
        md.append(f"| {pname(p)} | {r['is_n']} | {r['is_net']:,.0f} | {r['is_pf']:.2f} | {r['is_net_bps']:.1f} | {'*' if r['selected'] else ''} | "
                  f"{r['oos_n']} | {r['oos_net']:,.0f} | {r['oos_pf']:.2f} | {r['oos_folds']} |")
    results[label] = dict(insts=insts, best=best, oos=res, gates=gates,
                          table=table.drop(columns=['params']).to_dict('records'))
    return dict(best=best, oos=res, oos_trades=oos, table=table, gates=gates, bounds=bounds)


def main():
    md = [f"# {STRAT} — results\n", "Round 3. Month-end rebalancing flow in CME index futures, daily settlement fills, 1 contract, cme_fee round trip.\n"]
    results = {}
    # ---- data facts
    md.append("## Data / roll verification\n")
    md.append(f"Session calendar = SPY sessions {CAL[0].date()} .. {CAL[-1].date()} ({len(CAL)} days). "
              f"Roll days flagged by calendar (3rd Friday of Mar/Jun/Sep/Dec + next session): {len(ROLL)}.\n")
    for inst in ('ES', 'NQ', 'MES', 'MNQ', 'GC', 'SPY', 'QQQ', 'GLD'):
        S = series(inst)
        r = S['lr_raw'] - S['lr_adj']
        big = (S['lr_raw'].abs() > 0.005)
        pr = INST[inst]['proxy']
        if pr:
            pl = np.log(_daily(pr).reindex(S['close'].index).ffill()).diff()
            resid = (S['lr_raw'] - pl)
            n_roll_big = int((resid.abs() > 0.005)[S['is_roll']].sum())
            n_other_big = int((resid.abs() > 0.005)[~S['is_roll']].sum())
            md.append(f"- {inst}: first {S['first'].date()}, ffilled {S['n_ffill']} sessions; |{inst}-{pr}| residual >50bps on {n_roll_big}/{int(S['is_roll'].sum())} flagged roll days and {n_other_big} other days (17:00 vs 16:00 timing + real basis moves); roll adjustment changes {int((r.abs()>1e-9).sum())} daily returns.")
        else:
            md.append(f"- {inst}: first {S['first'].date()}, ffilled {S['n_ffill']} sessions; no roll adjustment applied.")
    # do any A/B windows touch a roll day?
    touch = {}
    for inst in ('ES', 'NQ'):
        for p in GRID:
            t = build_trades(inst, p)
            touch[(inst, pname(p))] = int(t['roll_touch'].sum()) if len(t) else 0
    ab_touch = sum(v for (i, n), v in touch.items() if not n.startswith('C'))
    c_touch = {k: v for k, v in touch.items() if k[1].startswith('C')}
    md.append(f"- Windows of arms A/B (T-3..T+4) touching a roll day on ES/NQ: **{ab_touch}** (expected 0: quarterly rolls are mid-month). Arm C (T-8..T-2) windows touching a roll day: {c_touch}.\n")
    print("roll touch A/B:", ab_touch, "C:", c_touch)

    T_MAIN = (pd.Timestamp(CAL[0], tz='UTC'), pd.Timestamp(CAL[-1], tz='UTC'))
    S_MICRO = series('MES')['first']
    T_MICRO = (pd.Timestamp(S_MICRO, tz='UTC'), pd.Timestamp(CAL[-1], tz='UTC'))
    md.append(f"Folds (main): {[(s.date().isoformat(), e.date().isoformat()) for s, e in C.fold_bounds(T_MAIN, 3)]}  \n"
              f"Folds (micros): {[(s.date().isoformat(), e.date().isoformat()) for s, e in C.fold_bounds(T_MICRO, 3)]}\n")

    md.append("\n## Headline: pooled ES+NQ, 15-cell grid, select on fold 1\n")
    head = run_set('headline_ESNQ_grid15', ['ES', 'NQ'], GRID, T_MAIN, md, results)

    md.append("\n## Per-arm walk-forward (ES+NQ pooled)\n")
    arms = {}
    for arm in ('A', 'B', 'C'):
        g = [p for p in GRID if p['arm'] == arm]
        arms[arm] = run_set(f'arm{arm}_ESNQ', ['ES', 'NQ'], g, T_MAIN, md, results)

    md.append("\n## Per-instrument (15-cell grid each)\n")
    per = {}
    for inst in ('ES', 'NQ', 'GC', 'SPY', 'QQQ', 'GLD'):
        per[inst] = run_set(f'inst_{inst}', [inst], GRID, T_MAIN, md, results)
    for inst in ('MES', 'MNQ'):
        per[inst] = run_set(f'inst_{inst}', [inst], GRID, T_MICRO, md, results)

    # ---- fixed-rule (no selection) summary: arm B thr3 k3 and arm A k3 on everything, full period, for transparency
    md.append("\n## Fixed-rule cross-section (no selection; full period; arm B thr=3% k=3 and arm A k=3)\n")
    md.append("| inst | rule | n | net | pf | wr | bps | folds | random-window z | p |\n|---|---|---:|---:|---:|---:|---:|---|---:|---:|")
    fixed = {}
    for inst in ('ES', 'NQ', 'MES', 'MNQ', 'GC', 'SPY', 'QQQ', 'GLD'):
        times = T_MICRO if inst in ('MES', 'MNQ') else T_MAIN
        for p in (dict(arm='B', thr=3, k=3), dict(arm='A', k=3), dict(arm='C', k=3)):
            t = build_trades(inst, p)
            r = C.evaluate(t, 3, start=times[0], end=times[1]) if len(t) else C.empty_result()
            rw = random_windows(t, times, n=300) if len(t) else dict(z=0.0, p=1.0, mean=0.0)
            C.record_to_lab(STRAT, f'FULL_{pname(p)}', inst, '1d', p, r, period=times, source=__file__,
                            baseline_net=rw['mean'], notes=f'full-period fixed rule (in-sample, not selected); random-window z={rw["z"]:.2f} p={rw["p"]:.3f}')
            md.append(f"| {inst} | {pname(p)} | {r['n']} | {r['net']:,.0f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['net_bps']:.1f} | {[round(x) for x in r['folds']]} | {rw['z']:.2f} | {rw['p']:.3f} |")
            fixed[f'{inst}_{pname(p)}'] = dict(r=r, rw=rw)

    # ---- arm B leg decomposition on ES+NQ full period
    md.append("\n## Arm B leg decomposition (ES+NQ, thr=3%, k=3, full period, in-sample)\n")
    tB = pd.concat([build_trades(i, dict(arm='B', thr=3, k=3)) for i in ('ES', 'NQ')], ignore_index=True)
    tB = C.add_pnl(tB)
    tB['leg'] = np.where(tB['side'] < 0, 'short_T-3_T-1 (MTD>=+thr)',
                         np.where(tB['mtd'] >= 0.03, 'long_T-1_T+k after up-month', 'long_T-3_T+k (MTD<=-thr)'))
    md.append("| leg | n | net | avg bps | wr |\n|---|---:|---:|---:|---:|")
    for leg, g in tB.groupby('leg'):
        md.append(f"| {leg} | {len(g)} | {g['net_pnl'].sum():,.0f} | {(g['net_pnl']/g['notional_usd']).mean()*1e4:.1f} | {(g['net_pnl']>0).mean():.2f} |")
    print(tB.groupby('leg')['net_pnl'].agg(['count', 'sum', 'mean']))

    # ---- MTD bucket diagnostic: what does T-3..T-1 and T-1..T+3 do as a function of MTD (ES, full period, in-sample)
    md.append("\n## Diagnostic: ES return of T-3..T-1 and T-1..T+3 by MTD bucket (full period, in-sample, bps)\n")
    S = series('ES'); mes = month_ends(S['first']); rows = []
    for j in range(1, len(mes)):
        iT, iP = mes[j], mes[j - 1]
        if iT + 4 >= len(CAL):
            continue
        cl = S['close']; lr = S['lr_adj']
        mtd = cl.loc[CAL[iT - 3]] / cl.loc[CAL[iP]] - 1
        pre = lr.loc[CAL[iT - 2]:CAL[iT - 1]].sum()
        post = lr.loc[CAL[iT]:CAL[iT + 3]].sum()
        rows.append(dict(month=str(CAL[iT].to_period('M')), mtd=mtd, pre=pre * 1e4, post=post * 1e4))
    dg = pd.DataFrame(rows)
    dg['bucket'] = pd.cut(dg['mtd'], [-1, -0.04, -0.02, 0, 0.02, 0.04, 1], labels=['<-4%', '-4..-2%', '-2..0%', '0..2%', '2..4%', '>4%'])
    md.append("| MTD bucket | months | mean T-3..T-1 | mean T-1..T+3 | t(post) |\n|---|---:|---:|---:|---:|")
    for b, g in dg.groupby('bucket', observed=True):
        tstat = g['post'].mean() / (g['post'].std(ddof=1) / math.sqrt(len(g))) if len(g) > 2 else float('nan')
        md.append(f"| {b} | {len(g)} | {g['pre'].mean():.1f} | {g['post'].mean():.1f} | {tstat:.2f} |")
    print(dg.groupby('bucket', observed=True)[['pre', 'post']].agg(['count', 'mean']))
    corr = dg[['mtd', 'pre', 'post']].corr()
    md.append(f"\nSpearman corr(MTD, pre) = {dg[['mtd','pre']].corr(method='spearman').iloc[0,1]:.3f}; corr(MTD, post) = {dg[['mtd','post']].corr(method='spearman').iloc[0,1]:.3f}\n")

    # ---- is the down-month rebound specific to month-end?  Compare the 7-session
    # return after ANY 15-session trailing return <= -3% (any day) with the same
    # at T-3 (ES and NQ, full period, in-sample diagnostic)
    md.append("\n## Diagnostic: is the post-down-month rebound month-end specific? (7-session fwd return after trailing-15-session return <= -3%, bps)\n")
    md.append("| inst | at T-3: n | mean | t | any day: n | mean | t | diff t |\n|---|---:|---:|---:|---:|---:|---:|---:|")
    for inst in ('ES', 'NQ', 'SPY', 'GLD'):
        S = series(inst); lr = S['lr_adj'].dropna(); cl = S['close']
        pos = pd.Series(np.arange(len(cl)), index=cl.index)
        mes = month_ends(S['first'])
        t3 = set(CAL[iT - 3] for iT in mes if iT - 3 >= 0)
        rows = []
        vals = cl.values; idx = cl.index
        for i in range(15, len(cl) - 7):
            trail = vals[i] / vals[i - 15] - 1
            if trail <= -0.03:
                rows.append(dict(date=idx[i], fwd=(vals[i + 7] / vals[i] - 1) * 1e4, t3=idx[i] in t3))
        d = pd.DataFrame(rows)
        a, b = d[d.t3], d[~d.t3]
        ta = a.fwd.mean() / (a.fwd.std(ddof=1) / math.sqrt(len(a))) if len(a) > 2 else float('nan')
        tb = b.fwd.mean() / (b.fwd.std(ddof=1) / math.sqrt(len(b))) if len(b) > 2 else float('nan')
        se = math.sqrt(a.fwd.var(ddof=1) / len(a) + b.fwd.var(ddof=1) / len(b)) if len(a) > 2 and len(b) > 2 else float('nan')
        md.append(f"| {inst} | {len(a)} | {a.fwd.mean():.0f} | {ta:.2f} | {len(b)} | {b.fwd.mean():.0f} | {tb:.2f} | {(a.fwd.mean()-b.fwd.mean())/se:.2f} |")
        print(inst, 'T-3 dd:', len(a), round(a.fwd.mean()), 'any-day dd:', len(b), round(b.fwd.mean()))

    # ---- 1h tradability
    md.append("\n## 1h tradability check (2024-05 .. 2026-08, fills at the 16:00 ET hourly-bar open vs daily settlement)\n")
    hc = {}
    for inst in ('ES', 'NQ'):
        for p in (head['best'], dict(arm='A', k=3)):
            h = hourly_check(inst, p)
            hc[f'{inst}_{pname(p)}'] = h
            md.append(f"- {inst} {pname(p)}: |16:00ET − daily close| median {h['med_abs_bps']:.1f} bps, p90 {h['p90_abs_bps']:.1f} bps over {h['n_days']} days; "
                      f"daily-close fills: {fmt(h['daily_close'])}; 16:00 fills: {fmt(h['h16_fill'])}")
            print(inst, pname(p), 'h16 med bps', round(h['med_abs_bps'], 2), 'daily', round(h['daily_close']['net']), '16:00', round(h['h16_fill']['net']))

    # ---- verdict
    res = head['oos']; g = head['gates']
    crit = dict(oos_net_pos=res['net'] > 0, pf_ge_1_2=res['pf'] >= 1.2, n_ge_60=res['n'] >= 60,
                folds_pos=all(f > 0 for f in res['folds'][1:]),
                random_p_lt_05=g.get('random', {}).get('p', 1.0) < 0.05,
                beats_drift=res['net'] > g.get('drift_baseline', 0.0))
    # neighbour check: OOS net of the neighbouring cells of the selected cell
    tab = head['table']
    b = head['best']
    neigh = []
    for _, r in tab.iterrows():
        p = GRID[int(r['idx'])]
        if p['arm'] == b['arm'] and abs(p['k'] - b['k']) <= 1 and abs(p.get('thr', 0) - b.get('thr', 0)) <= 1 and pname(p) != pname(b):
            neigh.append((pname(p), float(r['oos_net'])))
    crit['neighbours_pos'] = bool(neigh) and all(v > 0 for _, v in neigh)
    n_fail = sum(1 for v in crit.values() if not v)
    verdict = 'edge' if n_fail == 0 else ('weak' if res['net'] > 0 and n_fail <= 1 else 'none')
    md.append("\n## Verdict\n")
    md.append(f"Criteria: {json.dumps(crit)}; neighbours (OOS net): {neigh}  \n**Verdict: {verdict}**\n")
    print("criteria", crit, "neigh", neigh, "verdict", verdict)

    OUT_MD.write_text('\n'.join(md))
    out = dict(headline=dict(best=head['best'], oos=head['oos'], gates=head['gates'], neigh=neigh, criteria=crit, verdict=verdict),
               arms={k: dict(best=v['best'], oos=v['oos'], gates=v['gates']) for k, v in arms.items()},
               per_inst={k: dict(best=v['best'], oos=v['oos'], gates=v['gates']) for k, v in per.items()},
               fixed=fixed, hourly=hc, results=results)
    OUT_JSON.write_text(json.dumps(out, default=lambda o: o.item() if hasattr(o, 'item') else str(o), indent=1))
    print("wrote", OUT_MD, OUT_JSON)


if __name__ == '__main__':
    main()
