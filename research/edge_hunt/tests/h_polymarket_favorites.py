"""Hypothesis key=polymarket_favorites : favorite-longshot bias on Polymarket.

Data (data/poly/, built by fetch_poly_markets.py + fetch_poly_trades.py):
  every CLOSED Gamma market with endDate 2024-01-01..2026-08-21 and final volume
  >= $1k (sub-daily crypto up/down series excluded), a seeded random sample of
  <= 800 markets/month, and EVERY print of those markets from data-api /trades.
  Point-in-time: closed markets include every loser; nothing is filtered on the
  outcome.  (Residual look-ahead: the $1k FINAL-volume crawl filter; the
  liquidity split below uses PIT volume only.)
Calibration: at t = endDate - h (h = 1, 7, 30 d; endDate is known in advance
  so t is causal), YES-prob = last print at/before t (within a staleness window),
  bucketed 0.80-0.85 ... 0.95-0.99: fraction that resolved to that side.
Strategy: at t = endDate - D buy the FAVORITE side (max(p, 1-p) >= thr, <= 0.99)
  as a TAKER at the last print (+ slippage stress), hold to resolution
  (closedTime); payout 1 or 0.  $100 cost per decision, ONE decision per event.
Costs: Polymarket taker fee = rate * p * (1-p) per share, rate by category from
  the CURRENT schedule (docs.polymarket.com, verified 2026-08-28: crypto 0.07,
  politics/finance/tech/mentions 0.04, geopolitics 0, everything else 0.05;
  makers pay 0; no redemption / winner fee exists) applied to all history, plus
  a 5%/yr capital charge on the $100 for the actual lock (t -> closedTime).
  Both are booked in fee_usd so evaluate() is net of fees AND capital cost.
Folds: calendar quarters of the entry time. In-sample = 2024 (thr x D grid,
  pick by net with n >= 30), OOS = 2025Q1..2026Q3, every OOS fold reported.
Sanity: Bernoulli(p) simulation null (outcomes drawn at the fill price),
  sub-period signs, category / PIT-liquidity splits, top-3 removal, neighbours,
  slippage / fee / capital-charge / 2%-winner-fee stresses, concentration.
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import common as C

STRAT = 'polymarket_favorites'
D = C.DATA / 'poly'
OUT_JSON = Path(__file__).with_suffix('.json')
OUT_TAB = Path(__file__).with_name('h_polymarket_favorites_tables.md')
COST = 100.0            # USD cost basis per decision
RF = 0.05
PMAX = 0.99
HORIZONS = [1, 7, 30]
STALE = {1: 1.0, 7: 3.0, 30: 5.0}   # max age (days) of the last print used as the fill
SUBDAILY = re.compile(r"updown-|-up-or-down-\d+m|hourly|-1h-")
IS_END = pd.Timestamp('2025-01-01', tz='UTC')
FEE_RATE = {'crypto': 0.07, 'politics': 0.04, 'finance': 0.04, 'tech': 0.04, 'mentions': 0.04,
            'geopolitics': 0.0, 'sports': 0.05, 'economics': 0.05, 'culture': 0.05, 'weather': 0.05, 'other': 0.05}
RNG = np.random.default_rng(11)


# ---------------------------------------------------------------- data
def categorize(tags: str, slug: str, question: str) -> str:
    t = set((tags or '').split('|')); s = (slug or '') + ' ' + (question or '').lower()
    if t & {'sports', 'nba', 'nfl', 'mlb', 'nhl', 'soccer', 'football', 'basketball', 'tennis', 'ufc', 'mma', 'esports',
            'golf', 'f1', 'boxing', 'cricket', 'baseball', 'hockey', 'epl', 'la-liga', 'champions-league', 'ncaa'} or ' vs. ' in s or ' vs ' in s:
        return 'sports'
    if t & {'crypto', 'cryptocurrency', 'bitcoin', 'ethereum', 'solana', 'memecoins', 'xrp', 'defi'} or re.search(r'bitcoin|ethereum|solana|\bbtc\b|\beth\b|xrp|dogecoin', s):
        return 'crypto'
    if t & {'geopolitics', 'international-relations', 'middle-east', 'israel', 'gaza', 'ukraine', 'russia', 'iran', 'china', 'war', 'military', 'hamas', 'nato'}:
        return 'geopolitics'
    if t & {'politics', 'elections', 'trump', 'us-politics', '2024-election', 'trump-presidency', 'congress', 'senate', 'polls', 'polling', 'approval', 'white-house'}:
        return 'politics'
    if t & {'finance', 'business', 'stocks', 'economy', 'economy1', 'fed', 'inflation', 'interest-rates', 'earnings', 'ipo'}:
        return 'finance'
    if t & {'economics', 'macro', 'gdp', 'jobs', 'cpi'}:
        return 'economics'
    if t & {'tech', 'technology', 'ai', 'science', 'openai', 'spacex'}:
        return 'tech'
    if t & {'mentions', 'mention-markets', 'tweet-markets', 'tweets'}:
        return 'mentions'
    if t & {'weather', 'climate', 'temperature', 'hurricane'}:
        return 'weather'
    if t & {'pop-culture', 'culture', 'entertainment', 'movies', 'music', 'tv', 'awards', 'celebrities', 'oscars', 'grammys'}:
        return 'culture'
    return 'other'


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    months = sorted(p.name[len('trades_'):-len('.parquet')] for p in D.glob('trades_*.parquet'))
    mk, tr, tg, sm = [], [], [], []
    for m in months:
        mk.append(pd.read_parquet(D / f'markets_{m}.parquet')); tr.append(pd.read_parquet(D / f'trades_{m}.parquet'))
        tg.append(pd.read_parquet(D / f'tags_{m}.parquet'))
        if (D / f'sample_{m}.parquet').exists():
            sm.append(pd.read_parquet(D / f'sample_{m}.parquet'))
    mk = pd.concat(mk, ignore_index=True).drop_duplicates('conditionId'); tr = pd.concat(tr, ignore_index=True)
    tg = pd.concat(tg, ignore_index=True).drop_duplicates('event_id'); sm = pd.concat(sm, ignore_index=True) if sm else None
    mk = mk[~mk['slug'].fillna('').str.contains(SUBDAILY)].copy()
    if sm is not None:
        mk = mk[mk['conditionId'].isin(sm.loc[sm['fetched'], 'conditionId'])]
    op = mk['outcomePrices'].map(lambda s: json.loads(s) if s else [])
    mk['res_yes'] = op.map(lambda v: 1.0 if v[:2] == ['1', '0'] else (0.0 if v[:2] == ['0', '1'] else np.nan))
    mk = mk[mk['res_yes'].notna()].copy()
    mk['end'] = pd.to_datetime(mk['endDate'], utc=True, format='mixed')
    mk['closed'] = pd.to_datetime(mk['closedTime'].str.replace(' ', 'T').str.replace('+00', 'Z'), utc=True, format='mixed')
    mk['start'] = pd.to_datetime(mk['startDate'], utc=True, format='mixed', errors='coerce')
    n_noclose = int(mk['closed'].isna().sum()); mk = mk[mk['closed'].notna() & mk['end'].notna()].copy()
    mk.attrs['n_no_closedtime_dropped'] = n_noclose
    mk = mk.merge(tg[['event_id', 'tags', 'n_markets_in_event']], on='event_id', how='left')
    mk['cat'] = [categorize(a, b, c) for a, b, c in zip(mk['tags'].fillna(''), mk['slug'], mk['question'])]
    mk['fee_rate'] = mk['cat'].map(FEE_RATE).fillna(0.05)
    tr = tr[tr['cid'].isin(mk['conditionId'])].copy()
    tr['p_yes'] = np.where(tr['oi'] == 0, tr['price'], 1.0 - tr['price']).astype('float64')
    tr['usd'] = (tr['price'] * tr['size']).astype('float64')
    tr = tr.sort_values(['cid', 't']).reset_index(drop=True)
    return mk.reset_index(drop=True), tr


def snapshots(mk: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """One row per (market, horizon): price / staleness / PIT volume at t = end - h."""
    grp = {cid: (g['t'].values, g['p_yes'].values, np.cumsum(g['usd'].values), g['usd'].values) for cid, g in tr.groupby('cid', sort=False)}
    rows = []
    for r in mk.itertuples(index=False):
        g = grp.get(r.conditionId)
        if g is None:
            continue
        ts, py, cum, usd = g
        end_s = r.end.timestamp(); closed_s = r.closed.timestamp()
        for h in HORIZONS:
            t = end_s - h * 86400
            if t >= closed_s:          # already resolved / closed before the horizon time
                continue
            i = np.searchsorted(ts, t, side='right') - 1
            if i < 0:
                continue
            age = (t - ts[i]) / 86400.0
            if age > STALE[h]:
                continue
            fwd = usd[(ts > t) & (ts <= closed_s)].sum()
            rows.append(dict(cid=r.conditionId, event_id=r.event_id, h=h, t=pd.Timestamp(t, unit='s', tz='UTC'),
                             p_yes=float(py[i]), age_d=age, pit_vol=float(cum[i]), fwd_vol=float(fwd),
                             res_yes=r.res_yes, closed=r.closed, end=r.end, cat=r.cat, fee_rate=r.fee_rate,
                             lock_d=max((closed_s - t) / 86400.0, 0.0) + 1.0 / 24,  # + ~1h redemption lag
                             final_vol=float(r.volumeNum), question=r.question))
    s = pd.DataFrame(rows)
    s['p_fav'] = np.maximum(s['p_yes'], 1 - s['p_yes'])
    s['fav_is_yes'] = s['p_yes'] >= 0.5
    s['fav_won'] = np.where(s['fav_is_yes'], s['res_yes'] == 1, s['res_yes'] == 0).astype(float)
    return s


# ---------------------------------------------------------------- trades
def build_trades(s: pd.DataFrame, thr: float, h: int, slip: float = 0.0, fee_on: bool = True, rf_on: bool = True,
                 winner_fee: float = 0.0, one_per_event: bool = True, side: str = 'fav') -> pd.DataFrame:
    x = s[(s['h'] == h)].copy()
    if side == 'fav':
        x = x[(x['p_fav'] >= thr) & (x['p_fav'] <= PMAX)]
        px = x['p_fav'].values + slip; won = x['fav_won'].values
    else:   # buy the longshot (the other side) at 1-p_fav: for the 'avoid/short longshot' reading
        x = x[(x['p_fav'] >= thr) & (x['p_fav'] <= PMAX)]
        px = (1 - x['p_fav'].values) + slip; won = 1 - x['fav_won'].values
    x = x.assign(px=px, won=won)
    x = x[x['px'] < 1.0]
    if one_per_event:
        x = x.sort_values(['p_fav', 'pit_vol'], ascending=False).drop_duplicates('event_id', keep='first')
    if len(x) == 0:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    qty = COST / x['px'].values
    fee = qty * x['fee_rate'].values * x['px'].values * (1 - x['px'].values) if fee_on else 0.0
    rfc = COST * RF * x['lock_d'].values / 365.0 if rf_on else 0.0
    wfee = winner_fee * qty * (1 - x['px'].values) * x['won'].values
    return pd.DataFrame(dict(entry_time=pd.to_datetime(x['t'].values, utc=True), exit_time=pd.to_datetime(x['closed'].values, utc=True), side=1.0, entry_px=x['px'].values,
                             exit_px=x['won'].values.astype(float), qty=qty, notional_usd=COST, fee_usd=fee + rfc + wfee,
                             instrument='POLY_' + x['cat'].values, cat=x['cat'].values, pit_vol=x['pit_vol'].values,
                             fwd_vol=x['fwd_vol'].values, lock_d=x['lock_d'].values, cid=x['cid'].values,
                             question=x['question'].values)).sort_values('entry_time').reset_index(drop=True)


def quarter_folds(trades: pd.DataFrame, quarters: list[str]) -> dict:
    """evaluate() plus per-quarter nets for the given quarter labels (chronological)."""
    r = C.evaluate(trades, n_folds=1)
    if len(trades):
        t = C.add_pnl(trades); q = t['entry_time'].dt.tz_convert(None).dt.to_period('Q').astype(str)
        r['folds'] = [float(t.loc[q == k, 'net_pnl'].sum()) for k in quarters]
        r['fold_n'] = [int((q == k).sum()) for k in quarters]
    else:
        r['folds'] = [0.0] * len(quarters); r['fold_n'] = [0] * len(quarters)
    r['fold_consistent'] = bool(all(f > 0 for f in r['folds']))
    return r


def bern_null(trades: pd.DataFrame, n_sim: int = 2000) -> dict:
    """Null: outcomes ~ Bernoulli(fill price) (i.e. prices are calibrated). p = P(sim net >= observed)."""
    if len(trades) == 0:
        return dict(p=1.0, obs=0.0, null_mean=0.0)
    t = C.add_pnl(trades); px = t['entry_px'].values; qty = t['qty'].values; cost = t['fee_usd'].values
    obs = t['net_pnl'].sum()
    win_pnl = qty * (1 - px) - cost; lose_pnl = -COST - cost
    sims = np.empty(n_sim)
    for k in range(n_sim):
        w = RNG.random(len(px)) < px
        sims[k] = np.where(w, win_pnl, lose_pnl).sum()
    return dict(p=float((sims >= obs).mean()), obs=float(obs), null_mean=float(sims.mean()), null_sd=float(sims.std()))


def annualized(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return dict(ann_net=0.0, avg_lock_d=0.0, ret_per_trade=0.0)
    t = C.add_pnl(trades)
    ret = t['net_pnl'] / COST; lock = t['lock_d']
    return dict(ret_per_trade=float(ret.mean()), avg_lock_d=float(lock.mean()),
                ann_net=float(ret.sum() / (lock.sum() / 365.0)))   # capital-weighted annualized net (excess over 5% already booked)


def main():
    mk, tr = load()
    s = snapshots(mk, tr)
    quarters = [str(q) for q in pd.period_range('2024Q1', '2026Q3', freq='Q')]
    oos_q = [q for q in quarters if q >= '2025Q1']
    out = dict(key=STRAT, n_markets=int(len(mk)), n_prints=int(len(tr)), n_snapshots=int(len(s)), n_no_closedtime_dropped=mk.attrs.get('n_no_closedtime_dropped'),
               markets_by_cat=mk['cat'].value_counts().to_dict(),
               markets_by_quarter=mk['end'].dt.tz_convert(None).dt.to_period('Q').astype(str).value_counts().sort_index().to_dict())
    lines = [f"# {STRAT} tables (auto-generated)\n", f"markets={len(mk)} prints={len(tr)} snapshots={len(s)}\n"]

    # ---- calibration table (one row per market-horizon, NOT deduped by event; reported both ways)
    bins = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0001]
    labels = ['0.50-0.60', '0.60-0.70', '0.70-0.80', '0.80-0.85', '0.85-0.90', '0.90-0.95', '0.95-0.99', '0.99+']
    s['bucket'] = pd.cut(s['p_fav'], bins, labels=labels, right=False)
    cal = {}
    lines.append("\n## Calibration of the favorite side (all markets; is = 2024, oos = 2025Q1-2026Q3)\n")
    lines.append("| horizon | bucket | n | mean price | realized win rate | diff (pp) | n_oos | wr_oos | diff_oos (pp) |\n|---|---|---|---|---|---|---|---|---|")
    for h in HORIZONS:
        for b in labels:
            x = s[(s['h'] == h) & (s['bucket'] == b)]
            xo = x[x['t'] >= IS_END]
            if len(x) == 0:
                continue
            row = dict(n=int(len(x)), price=float(x['p_fav'].mean()), wr=float(x['fav_won'].mean()),
                       n_oos=int(len(xo)), wr_oos=float(xo['fav_won'].mean()) if len(xo) else np.nan,
                       price_oos=float(xo['p_fav'].mean()) if len(xo) else np.nan)
            cal[f'{h}d_{b}'] = row
            lines.append(f"| {h}d | {b} | {row['n']} | {row['price']:.3f} | {row['wr']:.3f} | {(row['wr']-row['price'])*100:+.1f} | {row['n_oos']} | {row['wr_oos']:.3f} | {(row['wr_oos']-row['price_oos'])*100:+.1f} |")
    out['calibration'] = cal
    # by category at 7d, favorites >= 0.80
    lines.append("\n## Calibration by category, favorite >= 0.80 (per horizon: n / mean price / realized)\n")
    lines.append("| category | " + " | ".join(f"{h}d" for h in HORIZONS) + " |\n|---|" + "---|" * len(HORIZONS))
    calc = {}
    for c in sorted(s['cat'].unique()):
        cells = []
        for h in HORIZONS:
            x = s[(s['cat'] == c) & (s['h'] == h) & (s['p_fav'] >= 0.8) & (s['p_fav'] <= PMAX)]
            cells.append(f"{len(x)} / {x['p_fav'].mean():.3f} / {x['fav_won'].mean():.3f}" if len(x) else "-")
            calc[f'{c}_{h}d'] = dict(n=int(len(x)), price=float(x['p_fav'].mean()) if len(x) else None, wr=float(x['fav_won'].mean()) if len(x) else None)
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    out['calibration_by_cat'] = calc

    # ---- grid: in-sample (2024) selection
    grid = [dict(thr=thr, h=h) for h in HORIZONS for thr in [0.80, 0.85, 0.90, 0.95, 0.97]]
    is_rows = []
    for p in grid:
        tr_all = build_trades(s, p['thr'], p['h'])
        tis = tr_all[tr_all['entry_time'] < IS_END]; too = tr_all[tr_all['entry_time'] >= IS_END]
        ris = C.evaluate(tis, n_folds=1); roo = quarter_folds(too, oos_q)
        is_rows.append(dict(**p, is_n=ris['n'], is_net=ris['net'], is_pf=ris['pf'], is_wr=ris['wr'],
                            oos_n=roo['n'], oos_net=roo['net'], oos_pf=roo['pf'], oos_wr=roo['wr'], oos_folds=roo['folds'], oos_fold_n=roo['fold_n']))
        C.record_to_lab(STRAT, f"grid_thr{p['thr']}_D{p['h']}_IS2024", 'POLY', f"{p['h']}d", p, ris, period=(tis['entry_time'].min() if len(tis) else None, IS_END),
                        source='tests/h_polymarket_favorites.py', notes='in-sample 2024; fee=current taker schedule + 5% capital charge; $100/decision')
        C.record_to_lab(STRAT, f"grid_thr{p['thr']}_D{p['h']}_OOS", 'POLY', f"{p['h']}d", p, roo, period=(IS_END, too['entry_time'].max() if len(too) else None),
                        source='tests/h_polymarket_favorites.py', notes='OOS 2025Q1-2026Q3 quarterly folds; fee=current taker schedule + 5% capital charge; $100/decision')
    tab = pd.DataFrame(is_rows)
    elig = tab[tab['is_n'] >= 30]
    best = (elig if len(elig) else tab).sort_values('is_net', ascending=False).iloc[0]
    bp = dict(thr=float(best['thr']), h=int(best['h']))
    out['grid'] = tab.to_dict('records'); out['best_params'] = bp
    lines.append("\n## In-sample grid (2024) and the OOS of every cell (selection = max IS net, n>=30)\n")
    lines.append("| thr | D | IS n | IS net | IS PF | IS WR | OOS n | OOS net | OOS PF | OOS WR | OOS quarters |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for r in is_rows:
        mark = ' **<- selected**' if (r['thr'] == bp['thr'] and r['h'] == bp['h']) else ''
        lines.append(f"| {r['thr']} | {r['h']} | {r['is_n']} | {r['is_net']:+.0f} | {r['is_pf']:.2f} | {r['is_wr']:.3f} | {r['oos_n']} | {r['oos_net']:+.0f} | {r['oos_pf']:.2f} | {r['oos_wr']:.3f} | " + ", ".join(f"{v:+.0f}" for v in r['oos_folds']) + f"{mark} |")

    # ---- headline OOS
    tr_all = build_trades(s, bp['thr'], bp['h'])
    oos = tr_all[tr_all['entry_time'] >= IS_END].reset_index(drop=True)
    res = quarter_folds(oos, oos_q); res.update(annualized(oos)); res['null'] = bern_null(oos)
    out['oos'] = res
    lines.append(f"\n## Headline OOS (thr={bp['thr']}, D={bp['h']}d): n={res['n']} net={res['net']:+.0f} PF={res['pf']:.2f} WR={res['wr']:.3f} "
                 f"ann={res['ann_net']*100:+.1f}%/yr (excess of 5%) avg lock={res['avg_lock_d']:.1f}d; Bernoulli null p={res['null']['p']:.3f} (null mean {res['null']['null_mean']:+.0f})\n")
    lines.append("| quarter | n | net |\n|---|---|---|")
    for q, n, f in zip(oos_q, res['fold_n'], res['folds']):
        lines.append(f"| {q} | {n} | {f:+.0f} |")

    # ---- sanity / stress on the selected cell (OOS)
    san = {}
    def rec(name, trades, note=''):
        r = quarter_folds(trades, oos_q); r.update(annualized(trades)); san[name] = r
        C.record_to_lab(STRAT, f"oos_{name}", 'POLY', f"{bp['h']}d", dict(bp, variant=name), r, period=(IS_END, None),
                        source='tests/h_polymarket_favorites.py', notes=note or name)
        return r
    rec('selected', oos, 'headline')
    # top-3 removal (largest net_pnl trades)
    t = C.add_pnl(oos)
    if len(t) > 3:
        keep = t.sort_values('net_pnl', ascending=False).iloc[3:]
        rec('ex_top3', oos.loc[keep.index])
    # stresses
    rec('slip_0.5c', build_trades(s, bp['thr'], bp['h'], slip=0.005).query('entry_time >= @IS_END'))
    rec('slip_1c', build_trades(s, bp['thr'], bp['h'], slip=0.01).query('entry_time >= @IS_END'))
    rec('no_fee', build_trades(s, bp['thr'], bp['h'], fee_on=False).query('entry_time >= @IS_END'))
    rec('no_fee_no_rf', build_trades(s, bp['thr'], bp['h'], fee_on=False, rf_on=False).query('entry_time >= @IS_END'))
    rec('winner_fee_2pct', build_trades(s, bp['thr'], bp['h'], winner_fee=0.02).query('entry_time >= @IS_END'))
    rec('all_markets_not_deduped', build_trades(s, bp['thr'], bp['h'], one_per_event=False).query('entry_time >= @IS_END'))
    rec('longshot_long_same_cell', build_trades(s, bp['thr'], bp['h'], side='long').query('entry_time >= @IS_END'), 'buy the longshot side instead (mirror)')
    # neighbours
    for thr in [bp['thr'] - 0.05, bp['thr'] + 0.02]:
        if 0.5 <= thr <= 0.98:
            rec(f'nb_thr{thr:.2f}', build_trades(s, thr, bp['h']).query('entry_time >= @IS_END'))
    for h in HORIZONS:
        if h != bp['h']:
            rec(f'nb_D{h}', build_trades(s, bp['thr'], h).query('entry_time >= @IS_END'))
    # splits
    for c in sorted(oos['cat'].unique()):
        rec(f'cat_{c}', oos[oos['cat'] == c])
    if len(oos):
        q3 = oos['pit_vol'].quantile([1 / 3, 2 / 3]).values
        rec('liq_low', oos[oos['pit_vol'] < q3[0]]); rec('liq_mid', oos[(oos['pit_vol'] >= q3[0]) & (oos['pit_vol'] < q3[1])]); rec('liq_high', oos[oos['pit_vol'] >= q3[1]])
        big = oos['pit_vol'] >= oos['pit_vol'].quantile(0.9)
        san['concentration_top10pct_liq_share_of_net'] = float(C.add_pnl(oos[big])['net_pnl'].sum() / t['net_pnl'].sum()) if t['net_pnl'].sum() != 0 else None
    # sub-period: half-years
    if len(oos):
        hy = oos['entry_time'].dt.year.astype(str) + 'H' + ((oos['entry_time'].dt.month > 6).astype(int) + 1).astype(str)
        san['half_year_nets'] = {k: float(v) for k, v in t.groupby(hy.values)['net_pnl'].sum().items()}
    out['sanity'] = san
    lines.append("\n## Sanity / stress on the selected cell (OOS 2025Q1-2026Q3)\n")
    lines.append("| variant | n | net | PF | WR | ann % | quarters |\n|---|---|---|---|---|---|---|")
    for k, r in san.items():
        if isinstance(r, dict) and 'n' in r:
            lines.append(f"| {k} | {r['n']} | {r['net']:+.0f} | {r['pf']:.2f} | {r['wr']:.3f} | {r['ann_net']*100:+.1f} | " + ", ".join(f"{v:+.0f}" for v in r['folds']) + " |")
    lines.append(f"\nconcentration: top-10% PIT-liquidity markets' share of OOS net = {san.get('concentration_top10pct_liq_share_of_net')}; half-years = {san.get('half_year_nets')}\n")

    # ---- best OOS cell (for transparency: post-hoc, NOT the headline)
    tab2 = tab.sort_values('oos_net', ascending=False).iloc[0]
    out['best_oos_cell_posthoc'] = dict(thr=float(tab2['thr']), h=int(tab2['h']), oos_net=float(tab2['oos_net']), oos_n=int(tab2['oos_n']), oos_pf=float(tab2['oos_pf']))

    # ---- capacity: dollar prints on the favorite side after t, per year, selected cell
    if len(oos):
        yrs = (oos['entry_time'].max() - oos['entry_time'].min()).days / 365.25
        fwd = oos['fwd_vol'].sum() / max(yrs, 0.25)
        out['capacity'] = dict(fwd_print_usd_per_year=float(fwd), assumed_participation=0.05, capacity_usd=float(fwd * 0.05),
                               median_fwd_vol_per_market=float(oos['fwd_vol'].median()))
    OUT_TAB.write_text("\n".join(lines) + "\n")
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    print("\n".join(lines))


if __name__ == '__main__':
    main()
