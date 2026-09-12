"""Adversarial statistical verification of h_overnight_drift (lens: statistics).

Re-uses the author's trade construction (import h_overnight_drift) so the OOS
trade list is identical, then asks:
  1. bootstrap p(net>0) on OOS trade PnLs: per-trade iid (10k), clustered by
     entry night (the 4 micros are one correlated bet), and per instrument;
  2. concentration: drop top-3 / top-10 trades, top week, top month;
  3. per-fold and per-month sign;
  4. effective n and cross-instrument correlation of nightly PnL;
  5. THE actual hypothesis (time-of-day effect, not beta): Welch t-test of
     hourly open->open returns inside the held window vs outside it, and the
     overnight-vs-pro-rata-buy-and-hold excess with a date-block bootstrap;
  6. parameter-neighbour stability over a wider (entry,exit) grid, OOS only;
  7. multiple-comparison accounting for the 24-cell x 5-universe grid.
Everything net of fees via common.cme_trade / common.evaluate.  Records to
quant-lab as strategy 'overnight_drift', variants 'verify_stats_*'.
"""
from __future__ import annotations
import sys, json
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt/tests')
import common as C
import h_overnight_drift as H

ET = H.ET
INSTS = H.INSTS
STRAT = 'overnight_drift'
RNG = np.random.default_rng(12345)
NB = 10_000
out = {}

starts = [H.bars(i).index.min() for i in INSTS]
ends = [H.bars(i).index.max() for i in INSTS]
span = (max(starts), min(ends))
bounds = C.fold_bounds(span, 3)
oos_s, oos_e = bounds[1][0], bounds[2][1]
print('span', span, 'folds', bounds)

best = dict(session='on_16_9', side=1, filt='all')
run_fn = H.run_fn_factory(INSTS)
oos = C.add_pnl(run_fn(best, oos_s, oos_e))
res = C.evaluate(oos, 3, start=span[0], end=span[1])
print('OOS reproduced:', H.fmt(res))
assert abs(res['net'] - 38367.93) < 1.0, res['net']
net = oos['net_pnl'].values
n = len(net)

# ---------------------------------------------------------------- 1. bootstrap
def boot_p(x, nb=NB):
    idx = RNG.integers(0, len(x), size=(nb, len(x)))
    sums = x[idx].sum(axis=1)
    return float((sums <= 0).mean()), sums

p_iid, sums = boot_p(net)
ci = np.percentile(sums, [2.5, 97.5])
print(f'\n[1] per-trade iid bootstrap: p(net<=0)={p_iid:.4f}  95% CI [{ci[0]:.0f},{ci[1]:.0f}]  n={n}')
out['boot_iid_p'] = p_iid; out['boot_iid_ci'] = ci.tolist()

# cluster by entry night (all 4 instruments entered at the same 16:00 ET bar)
oos['night'] = pd.to_datetime(oos['entry_time']).dt.tz_convert(ET).dt.date
nightly = oos.groupby('night')['net_pnl'].sum()
p_cl, sums_cl = boot_p(nightly.values)
ci_cl = np.percentile(sums_cl, [2.5, 97.5])
print(f'    cluster-by-night bootstrap: nights={len(nightly)} p(net<=0)={p_cl:.4f}  95% CI [{ci_cl[0]:.0f},{ci_cl[1]:.0f}]')
out['boot_night_p'] = p_cl; out['n_nights'] = int(len(nightly))

# stationary block bootstrap on nightly series (block ~ 10 nights) for autocorrelation
def block_boot(x, nb=NB, L=10):
    N = len(x); res = np.empty(nb)
    for b in range(nb):
        pos = []
        while len(pos) < N:
            s = RNG.integers(0, N); ln = RNG.geometric(1 / L)
            pos.extend(((s + np.arange(ln)) % N).tolist())
        res[b] = x[np.array(pos[:N])].sum()
    return float((res <= 0).mean()), res
p_bb, _ = block_boot(nightly.values, nb=5000)
print(f'    block bootstrap (mean block 10 nights, 5k): p(net<=0)={p_bb:.4f}')
out['boot_block_p'] = p_bb

# per instrument
per_inst = {}
for inst in INSTS:
    x = oos.loc[oos['instrument'] == inst, 'net_pnl'].values
    p, s = boot_p(x)
    t, pt = stats.ttest_1samp(x, 0)
    per_inst[inst] = dict(n=int(len(x)), net=float(x.sum()), boot_p=p, t=float(t), p_t=float(pt))
    print(f'    {inst}: n={len(x)} net={x.sum():.0f} boot p={p:.4f} t={t:.2f} p_t={pt:.3f}')
out['per_inst'] = per_inst

# ---------------------------------------------------------------- 2. concentration
srt = np.sort(net)[::-1]
print(f'\n[2] top-3 trades sum={srt[:3].sum():.0f} -> net w/o top3={net.sum()-srt[:3].sum():.0f}; '
      f'w/o top10={net.sum()-srt[:10].sum():.0f}; top3 share={srt[:3].sum()/net.sum():.1%}')
out['net_wo_top3'] = float(net.sum() - srt[:3].sum())
out['net_wo_top10'] = float(net.sum() - srt[:10].sum())
# bottom-3 removed (symmetry)
print(f'    w/o bottom3={net.sum()-np.sort(net)[:3].sum():.0f}')
oos['week'] = pd.to_datetime(oos['entry_time']).dt.tz_convert(ET).dt.to_period('W').astype(str)
oos['month'] = pd.to_datetime(oos['entry_time']).dt.tz_convert(ET).dt.to_period('M').astype(str)
wk = oos.groupby('week')['net_pnl'].sum().sort_values(ascending=False)
mo = oos.groupby('month')['net_pnl'].sum()
print(f'    best week {wk.index[0]} = {wk.iloc[0]:.0f} ({wk.iloc[0]/net.sum():.1%}); net w/o best week={net.sum()-wk.iloc[0]:.0f}; '
      f'w/o top3 weeks={net.sum()-wk.iloc[:3].sum():.0f}')
print(f'    best month {mo.idxmax()} = {mo.max():.0f}; net w/o best month={net.sum()-mo.max():.0f}')
out['net_wo_best_week'] = float(net.sum() - wk.iloc[0]); out['net_wo_top3_weeks'] = float(net.sum() - wk.iloc[:3].sum())
out['net_wo_best_month'] = float(net.sum() - mo.max())

# ---------------------------------------------------------------- 3. per-fold / per-month sign
print(f'\n[3] OOS folds: {[round(f) for f in res["folds"]]}  fold_n={res["fold_n"]}')
pos_m = int((mo > 0).sum()); print(f'    months: {pos_m}/{len(mo)} positive; binomial p(one-sided)={stats.binomtest(pos_m, len(mo), 0.5, alternative="greater").pvalue:.3f}')
print('    ' + ', '.join(f'{k}:{v:.0f}' for k, v in mo.items()))
out['months_pos'] = pos_m; out['months_n'] = int(len(mo)); out['month_pnl'] = {k: round(float(v)) for k, v in mo.items()}
# per-quarter
oos['q'] = pd.to_datetime(oos['entry_time']).dt.tz_convert(ET).dt.to_period('Q').astype(str)
qq = oos.groupby('q')['net_pnl'].sum(); print('    quarters: ' + ', '.join(f'{k}:{v:.0f}' for k, v in qq.items()))
out['quarter_pnl'] = {k: round(float(v)) for k, v in qq.items()}

# ---------------------------------------------------------------- 4. effective n
piv = oos.pivot_table(index='night', columns='instrument', values='net_pnl')
corr = piv.corr(); print('\n[4] nightly PnL correlation:\n' + corr.round(2).to_string())
avg_r = corr.values[np.triu_indices(4, 1)].mean()
n_eff = n / (1 + 3 * avg_r)
print(f'    avg pairwise corr={avg_r:.2f} -> effective n ~ {n_eff:.0f} (vs claimed 1592; nights={len(nightly)})')
out['avg_pair_corr'] = float(avg_r); out['n_eff'] = float(n_eff)
# nightly t-stat / sharpe
tn, pn = stats.ttest_1samp(nightly.values, 0)
print(f'    nightly basket: mean={nightly.mean():.1f} sd={nightly.std():.0f} t={tn:.2f} p={pn:.4f} ann.Sharpe~{nightly.mean()/nightly.std()*np.sqrt(252):.2f}')
out['nightly_t'] = float(tn); out['nightly_p'] = float(pn)

# ---------------------------------------------------------------- 5. time-of-day vs beta
print('\n[5] Is it time-of-day or beta?')
tod = {}
for inst in INSTS:
    b = H.bars(inst); b = b[(b.index >= oos_s) & (b.index < oos_e)].copy()
    m = C.cme_multiplier(inst)
    # open->next open hourly return (matches execution at bar opens)
    b['r'] = (b['open'].shift(-1) - b['open']) * m
    b = b.dropna(subset=['r'])
    inwin = (b['hour'] >= 16) | (b['hour'] < 9)      # held window (incl. weekend hours)
    r_in, r_out = b.loc[inwin, 'r'].values, b.loc[~inwin, 'r'].values
    t, p = stats.ttest_ind(r_in, r_out, equal_var=False)
    tot = b['r'].sum(); share_pnl = r_in.sum() / tot if tot else np.nan
    share_time = inwin.mean()
    # mean per-hour drift in vs out
    tod[inst] = dict(bars_in=int(inwin.sum()), bars_out=int((~inwin).sum()), mean_in=float(r_in.mean()), mean_out=float(r_out.mean()),
                     welch_t=float(t), welch_p=float(p), pnl_share_in=float(share_pnl), time_share_in=float(share_time),
                     buyhold=float(tot), in_sum=float(r_in.sum()))
    print(f'    {inst}: bars in/out={inwin.sum()}/{(~inwin).sum()} mean/hr in={r_in.mean():.2f} out={r_out.mean():.2f} '
          f'Welch t={t:.2f} p={p:.3f} | in-window gross={r_in.sum():.0f} = {share_pnl:.0%} of B&H {tot:.0f} (time share {share_time:.0%})')
out['tod'] = tod

# excess over pro-rata B&H, date-block bootstrap: per night, on_pnl - time_share * (on+id next day)
print('    excess of overnight leg over pro-rata (time-weighted) share of full-cycle return, block bootstrap by date:')
excess = {}
for inst in INSTS:
    m = C.cme_multiplier(inst)
    on = H.legs(inst, 16, 9, True); idd = H.legs(inst, 9, 16, False)
    on = on[(on.entry_time >= oos_s) & (on.entry_time < oos_e)]; idd = idd[(idd.entry_time >= oos_s) & (idd.entry_time < oos_e)]
    on_d = pd.Series(((on.exit_px - on.entry_px) * m).values, index=pd.to_datetime(on.exit_time).dt.tz_convert(ET).dt.date)
    on_h = pd.Series(((pd.to_datetime(on.exit_time) - pd.to_datetime(on.entry_time)).dt.total_seconds() / 3600).values, index=on_d.index)
    id_d = pd.Series(((idd.exit_px - idd.entry_px) * m).values, index=idd.entry_date.values)
    pair = pd.concat([on_d.rename('on'), on_h.rename('h'), id_d.rename('id')], axis=1).dropna()
    w = pair['h'] / (pair['h'] + 7.0)
    ex = pair['on'] - w * (pair['on'] + pair['id'])           # overnight minus its time-share of the cycle
    p_ex, _ = block_boot(ex.values, nb=5000)
    t, pt = stats.ttest_1samp(ex, 0)
    excess[inst] = dict(n=int(len(ex)), excess_sum=float(ex.sum()), t=float(t), p_t=float(pt), block_p=float(p_ex))
    print(f'    {inst}: pairs={len(ex)} excess sum={ex.sum():.0f} (vs on gross {pair["on"].sum():.0f}) t={t:.2f} p={pt:.3f} block-boot p={p_ex:.3f}')
    C.record_to_lab(STRAT, 'verify_stats_excess_over_prorata_bh', inst, '1h', dict(on='16->9', id='9->16', weight='hours/(hours+7)'),
                    dict(C.empty_result(), n=int(len(ex)), net=float(ex.sum()), wr=float((ex > 0).mean())),
                    period=(oos_s, oos_e), source=__file__, trust='estimated',
                    notes=f'overnight gross minus time-share of full cycle, OOS; t={t:.2f} p={pt:.3f} block_p={p_ex:.3f}')
out['excess'] = excess

# Same test, in-sample fold 1 (was the asymmetry even there when selected?)
print('    same excess test on fold 1 (selection set):')
f1s, f1e = bounds[0]
for inst in INSTS:
    m = C.cme_multiplier(inst)
    on = H.legs(inst, 16, 9, True); idd = H.legs(inst, 9, 16, False)
    on = on[(on.entry_time >= f1s) & (on.entry_time < f1e)]; idd = idd[(idd.entry_time >= f1s) & (idd.entry_time < f1e)]
    on_d = pd.Series(((on.exit_px - on.entry_px) * m).values, index=pd.to_datetime(on.exit_time).dt.tz_convert(ET).dt.date)
    on_h = pd.Series(((pd.to_datetime(on.exit_time) - pd.to_datetime(on.entry_time)).dt.total_seconds() / 3600).values, index=on_d.index)
    id_d = pd.Series(((idd.exit_px - idd.entry_px) * m).values, index=idd.entry_date.values)
    pair = pd.concat([on_d.rename('on'), on_h.rename('h'), id_d.rename('id')], axis=1).dropna()
    w = pair['h'] / (pair['h'] + 7.0); ex = pair['on'] - w * (pair['on'] + pair['id'])
    t, pt = stats.ttest_1samp(ex, 0)
    print(f'    {inst}: fold1 pairs={len(ex)} excess={ex.sum():.0f} t={t:.2f} p={pt:.3f}')

# ---------------------------------------------------------------- 6. wider neighbour grid (OOS only, long, all)
print('\n[6] neighbour grid OOS (entry hour x exit hour), long, no filter, basket net:')
grid = {}
for ei in (14, 15, 16, 18, 19, 20):
    for eo in (7, 8, 9, 10, 11):
        H.SESSIONS['_v'] = (ei, eo, True)
        tr = run_fn(dict(best, session='_v'), oos_s, oos_e)
        r = C.evaluate(tr, 3, start=span[0], end=span[1])
        grid[(ei, eo)] = r['net']
        C.record_to_lab(STRAT, f'verify_stats_nb_in{ei}_out{eo}_L_all', 'BASKET', '1h', dict(best, e_in=ei, e_out=eo, universe=INSTS), r,
                        period=(oos_s, oos_e), source=__file__, notes='verifier neighbour grid, OOS only')
        del H.SESSIONS['_v']
g = pd.Series(grid).unstack(); print(g.round(0).to_string())
out['nb_grid'] = {f'{k[0]}->{k[1]}': round(v) for k, v in grid.items()}
# intraday-window complement over same OOS: long 9->16
tr = run_fn(dict(session='id_9_16', side=1, filt='all'), oos_s, oos_e); rid = C.evaluate(tr, 3, start=span[0], end=span[1])
tr = run_fn(dict(session='id_9_16', side=-1, filt='all'), oos_s, oos_e); rids = C.evaluate(tr, 3, start=span[0], end=span[1])
print(f'    intraday 9->16 long OOS net={rid["net"]:.0f} folds={[round(f) for f in rid["folds"]]}; short={rids["net"]:.0f} folds={[round(f) for f in rids["folds"]]}')
out['id_long_oos'] = rid['net']; out['id_short_oos'] = rids['net']
# 24h hold (16->16) = pure buy&hold daily, to compare with overnight leg
H.SESSIONS['_bh'] = (16, 16, True)
tr = run_fn(dict(best, session='_bh'), oos_s, oos_e); rbh = C.evaluate(tr, 3, start=span[0], end=span[1])
del H.SESSIONS['_bh']
print(f'    16->16 (daily buy&hold w/ fees) OOS net={rbh["net"]:.0f} pf={rbh["pf"]:.2f} folds={[round(f) for f in rbh["folds"]]}  vs overnight {res["net"]:.0f}')
out['bh_16_16_oos'] = rbh['net']
C.record_to_lab(STRAT, 'verify_stats_bh_16_16_L_all', 'BASKET', '1h', dict(e_in=16, e_out=16, side=1, universe=INSTS), rbh,
                period=(oos_s, oos_e), source=__file__, notes='daily buy-and-hold benchmark at same execution, OOS only')

# ---------------------------------------------------------------- 7. multiple comparisons
# 24 cells; 12 are sign-mirrors, so 12 independent-ish hypotheses x 5 universes. The fold-1 winner is the
# obvious 'long overnight' cell; question is whether OOS survives Bonferroni-ish shrinkage.
# White-style reality check: bootstrap the OOS max over the 12 long/short-symmetric cells under recentred nulls.
cells = [dict(session=s, side=sd, filt=f) for s in ('on_16_9', 'on_18_9', 'id_9_16') for sd in (1, -1) for f in ('all', 'no_fri', 'vix_lt', 'vix_ge')]
cell_pnl = []
for p in cells:
    t = C.add_pnl(run_fn(p, oos_s, oos_e)); cell_pnl.append(t.groupby(pd.to_datetime(t['entry_time']).dt.tz_convert(ET).dt.date)['net_pnl'].sum())
M = pd.concat(cell_pnl, axis=1).fillna(0.0); M.columns = [H.vname(p) for p in cells]
actual = M.sum(); centred = M - M.mean()
N = len(M); mx = np.empty(2000)
for b in range(2000):
    idx = RNG.integers(0, N, size=N); mx[b] = centred.values[idx].sum(axis=0).max()
rc_p = float((mx >= actual.max()).mean())
print(f'\n[7] reality check over 24 OOS cells (night-clustered, recentred): max actual={actual.max():.0f} ({actual.idxmax()}), p={rc_p:.3f}')
out['reality_check_p'] = rc_p
# But the selected cell was chosen on fold 1, so the OOS is a single pre-specified test: report its plain p.
print(f'    selected cell OOS: iid boot p={p_iid:.4f}, night-cluster p={p_cl:.4f}, block p={p_bb:.4f}')

# record headline verification
C.record_to_lab(STRAT, 'verify_stats_WF_OOS_on_16_9_L_all', 'BASKET', '1h', dict(best, universe=INSTS), res,
                period=(oos_s, oos_e), source=__file__, trust='measured',
                notes=(f'verifier reproduction of OOS; boot_iid_p={p_iid:.4f} night_cluster_p={p_cl:.4f} block_p={p_bb:.4f} '
                       f'n_eff~{n_eff:.0f} wo_top3={out["net_wo_top3"]:.0f} wo_best_week={out["net_wo_best_week"]:.0f} months_pos={pos_m}/{len(mo)} '
                       f'bh_16_16={rbh["net"]:.0f} reality_check_p={rc_p:.3f}'))
json.dump(out, open('/Users/molt_bot/latpfn-trading/research/edge_hunt/tests/verify_overnight_drift_statistics.json', 'w'), indent=1, default=str)
print('done')
