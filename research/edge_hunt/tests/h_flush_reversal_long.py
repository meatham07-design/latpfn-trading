"""flush_reversal_long -- long-only fade of coin-specific liquidation flushes on
Hyperliquid, executed with a resting MAKER bid inside the wick of the flush bar.

Signal (bar t closes):  range_t > Y x ATR14 (ATR over bars t-14..t-1),
  USD volume_t > V x trailing-100-bar median (bars t-100..t-1),
  1h: close/open-1 < -2%;  15m/5m: lower wick >= 0.4 x range,
  coin-specific: < 3 OTHER coins flush in the same bar (market-wide reported separately),
  coin in the point-in-time top-50 by trailing-30d USD volume (membership known at day start).
Entry: at open of t+1 post a bid at min(close_t - bid_off x range_t, open_{t+1});
  fill only if low_{t+1} <= bid x (1 - 5bps); entry px = bid (maker fee).
Exits: arm A = maker limit at entry + 0.5 x range_t (needs high >= target x (1+5bps));
  arm B = none; both: stop at entry - 1.5 x range_t (taker), time-stop at open of
  bar t+1+H (taker).  In the fill bar only the stop (low <= stop) and a target that is
  verifiably crossed AFTER the fill (close >= target) are honoured; stop has precedence.
Funding: hourly funding paid while long, added to fee_usd (clipped at 0 -> conservative).
$1,000 notional per trade, one open position per coin.
"""
import sys, json, itertools, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
EDGE = '/Users/molt_bot/latpfn-trading/research/edge_hunt'
sys.path.insert(0, EDGE)
import common as C

OUT_MD = Path(EDGE) / 'tests' / 'h_flush_reversal_long.md'
OUT_JSON = Path(EDGE) / 'tests' / 'h_flush_reversal_long.json'
EXT = C.DATA / 'hl_ext'
NOTIONAL = 1000.0
TICK = 5e-4                     # 5 bps trade-through requirement for a maker fill
FEE_M, FEE_T = C.FEES['hl_maker'], C.FEES['hl_taker']
TOP_N = 50
STRAT = 'flush_reversal_long'
SRC = str(Path(__file__).resolve()) if '__file__' in globals() else None
RNG = np.random.default_rng(7)
BAR = {'1h': pd.Timedelta('1h'), '15m': pd.Timedelta('15min'), '5m': pd.Timedelta('5min')}
MD = []
def log(s=''):
    print(s, flush=True); MD.append(s)

# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_1h_all():
    d = {}
    for c in C.list_hl_coins():
        d[c] = C.hl_candles(c, '1h')
    for p in sorted(EXT.glob('hl_*_1h.parquet')):
        c = p.name[3:-len('_1h.parquet')]
        if c not in d:
            df = pd.read_parquet(p); df.index = pd.to_datetime(df.index, utc=True); df.index.name = 'time'
            d[c] = df.sort_index()
    return d

def usd_vol(df):
    return df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0

def pit_universe(d1h):
    """Daily membership (index=day, columns=coin, bool): top-N by trailing-30d USD
    volume computed through the PREVIOUS day (min 7 days of history)."""
    daily = pd.DataFrame({c: usd_vol(df).resample('D').sum(min_count=1) for c, df in d1h.items()})
    roll = daily.rolling(30, min_periods=7).sum()
    rank = roll.rank(axis=1, ascending=False)
    member = (rank <= TOP_N).shift(1).fillna(False).astype(bool)
    return member

def load_funding(coins):
    f = {}
    for c in coins:
        p = C.DATA / f'hl_funding_{c}.parquet'
        if not p.exists():
            p = EXT / f'hl_funding_{c}.parquet'
        if not p.exists():
            continue
        s = pd.read_parquet(p)['fundingRate']
        s.index = pd.to_datetime(s.index, utc=True).floor('h')
        f[c] = s[~s.index.duplicated(keep='last')].sort_index()
    return f

def fetch_funding_ext(coins):
    """Public read-only fundingHistory for ext coins that enter the PIT universe."""
    import requests
    S = requests.Session()
    for coin in coins:
        p = EXT / f'hl_funding_{coin}.parquet'
        if p.exists(): continue
        now = int(time.time() * 1000); start = now - 210 * 86400000; parts = []
        try:
            while True:
                r = S.post(C.HL_INFO_URL, json={"type": "fundingHistory", "coin": coin, "startTime": start, "endTime": now}, timeout=60)
                if r.status_code == 429: time.sleep(3); continue
                r.raise_for_status(); chunk = r.json()
                if not chunk: break
                parts.extend(chunk); last = int(chunk[-1]['time'])
                if len(chunk) < 500 or last >= now: break
                start = last + 1; time.sleep(0.15)
            if parts:
                df = pd.DataFrame(parts)
                out = pd.DataFrame({'fundingRate': df['fundingRate'].astype(float).values,
                                    'premium': df['premium'].astype(float).values},
                                   index=pd.DatetimeIndex(pd.to_datetime(df['time'].astype('int64'), unit='ms', utc=True)))
                out.index.name = 'time'; out[~out.index.duplicated(keep='last')].sort_index().to_parquet(p)
                print('funding', coin, len(out), flush=True)
        except Exception as e:
            print('funding ERR', coin, e, flush=True)
        time.sleep(0.2)

# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------
def features(df):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    rng = h - l
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().shift(1)
    usd = usd_vol(df)
    medv = usd.rolling(100).median().shift(1)
    ret = c / o - 1
    lw = (np.minimum(o, c) - l) / rng.replace(0, np.nan)
    uw = (h - np.maximum(o, c)) / rng.replace(0, np.nan)
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, rng=rng, atr=atr, usd=usd, medv=medv,
                             ret=ret, lw=lw, uw=uw))

def flush_mask(F, Y, V, tf, mirror=False):
    base = (F['rng'] > Y * F['atr']) & (F['usd'] > V * F['medv']) & (F['rng'] > 0)
    if tf == '1h':
        dirn = (F['ret'] > 0.02) if mirror else (F['ret'] < -0.02)
    else:
        dirn = (F['uw'] >= 0.4) if mirror else (F['lw'] >= 0.4)
    return base & dirn

class Panel:
    """All per-coin features for a timeframe + concurrent-flush counts per (Y,V)."""
    def __init__(self, tf, data, member, funding, btc):
        self.tf = tf; self.F = {c: features(df) for c, df in data.items()}
        self.member = member; self.funding = funding; self.btc = btc
        self.bar = BAR[tf]
        self._cnt = {}
        idx = sorted(set().union(*[set(F.index) for F in self.F.values()]))
        self.index = pd.DatetimeIndex(idx)
        self.start, self.end = self.index[0], self.index[-1]
    def n_other(self, Y, V, mirror=False):
        key = (Y, V, mirror)
        if key not in self._cnt:
            m = pd.DataFrame({c: flush_mask(F, Y, V, self.tf, mirror) for c, F in self.F.items()}).reindex(self.index).fillna(False)
            self._cnt[key] = m.sum(axis=1)
        return self._cnt[key]
    def in_universe(self, coin, times):
        if coin not in self.member.columns:
            return pd.Series(False, index=times)
        days = times.floor('D')
        return pd.Series(self.member[coin].reindex(days).fillna(False).values, index=times)

def funding_cost(fund, entry_time, exit_time):
    """USD funding PAID by a $NOTIONAL long between entry and exit (hours h with
    entry < h <= exit). Positive = paid."""
    if fund is None: return 0.0
    s = fund.loc[(fund.index > entry_time) & (fund.index <= exit_time)]
    return float(s.sum()) * NOTIONAL

# ---------------------------------------------------------------------------
# simulation
# ---------------------------------------------------------------------------
def simulate(P, params, start, end, arm='A', mirror=False, market_wide=False, sig_override=None,
             taker_unconditional=False, hedged=False):
    """Return trades with entry_time in [start, end)."""
    Y, V, bid, H = params['Y'], params['V'], params['bid'], params['H']
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    rows = []
    cnt = P.n_other(Y, V, mirror)
    btc = P.btc
    for coin, F in P.F.items():
        if sig_override is not None:
            if coin not in sig_override: continue
            sig_idx = np.array(sorted(sig_override[coin]), dtype=int)
        else:
            m = flush_mask(F, Y, V, P.tf, mirror) & P.in_universe(coin, F.index)
            other = cnt.reindex(F.index).fillna(0).values - m.values.astype(int)
            spec = (other < 3)
            m = m & (~spec if market_wide else spec)
            sig_idx = np.flatnonzero(m.values)
        if len(sig_idx) == 0: continue
        o, h, l, c, rng = (F[k].values for k in ('open', 'high', 'low', 'close', 'rng'))
        tidx = F.index; n = len(F)
        fund = P.funding.get(coin)
        busy_until = -1
        for i in sig_idx:
            e = i + 1
            if e >= n or e + H >= n or e < busy_until: continue
            et = tidx[e]
            if not (start <= et < end): continue
            R = rng[i]
            if taker_unconditional:
                px = o[e]; entry_maker = False
            else:
                lim = min(c[i] - bid * R, o[e])
                if not (l[e] <= lim * (1 - TICK)): continue
                px = lim; entry_maker = True
            stop = px - 1.5 * R; tgt = px + 0.5 * R
            reason = None; xpx = None; xbar = None; xmaker = False; xt = None
            # fill bar
            if l[e] <= stop:
                reason, xpx, xbar, xt = 'stop', stop, e, tidx[e] + P.bar
            elif arm == 'A' and c[e] >= tgt * (1 + TICK) and not taker_unconditional:
                reason, xpx, xbar, xmaker, xt = 'target', tgt, e, True, tidx[e] + P.bar
            if reason is None:
                for j in range(e + 1, e + H):
                    if l[j] <= stop:
                        reason, xpx, xbar, xt = 'stop', stop, j, tidx[j] + P.bar; break
                    if arm == 'A' and h[j] >= tgt * (1 + TICK):
                        reason, xpx, xbar, xmaker, xt = 'target', tgt, j, True, tidx[j] + P.bar; break
            if reason is None:
                reason, xpx, xbar, xt = 'time', o[e + H], e + H, tidx[e + H]
            busy_until = xbar + 1
            qty = NOTIONAL / px
            fees = C.hl_fee(NOTIONAL, entry_maker) + C.hl_fee(qty * xpx, xmaker)
            fpaid = funding_cost(fund, et, xt)
            row = dict(entry_time=et, exit_time=xt, side=1, entry_px=px, exit_px=xpx, qty=qty,
                       notional_usd=NOTIONAL, fee_usd=max(fees + fpaid, 0.0), instrument=coin, multiplier=1.0,
                       reason=reason, signal_time=tidx[i], rng_pct=R / c[i], n_other=int(cnt.get(tidx[i], 0)) - (0 if sig_override is not None else 1),
                       funding_usd=fpaid, fees_only=fees, alt_ret=(xpx / px - 1))
            if hedged:
                # short equal notional BTC (taker both sides) from entry-bar close (proxy for the
                # intra-bar fill time) to exit-bar open (time exit) / close (intra-bar exit)
                be = btc['close'].get(tidx[e], np.nan)
                bx = btc['open'].get(tidx[xbar], np.nan) if reason == 'time' else btc['close'].get(tidx[xbar], np.nan)
                if np.isnan(be) or np.isnan(bx): continue
                bfund = P.funding.get('BTC')
                brecv = funding_cost(bfund, et, xt)      # short RECEIVES positive funding
                hedge_ret = -(bx / be - 1)
                hfee = 2 * C.hl_fee(NOTIONAL, False)
                tot = row['alt_ret'] + hedge_ret
                row.update(entry_px=1000.0, exit_px=1000.0 * (1 + tot), qty=1.0,
                           fee_usd=max(fees + fpaid + hfee - brecv, 0.0), hedge_ret=hedge_ret, btc_entry=be, btc_exit=bx)
            rows.append(row)
    cols = C.REQUIRED_TRADE_COLS + ['multiplier', 'reason', 'signal_time', 'rng_pct', 'n_other', 'funding_usd', 'fees_only', 'alt_ret']
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)

def fmt(r, tag=''):
    return (f"{tag}n={r['n']:4d} net={r['net']:8.1f} pf={r['pf']:.2f} wr={r['wr']:.2f} sharpe={r['sharpe']:5.2f} "
            f"bps={r['net_bps']:6.1f} folds={[round(x,1) for x in r['folds']]} fold_n={r['fold_n']}")

def rec(variant, tf, params, res, period, notes=None, instrument='HL_TOP50_PIT'):
    try:
        C.record_to_lab(STRAT, variant, instrument, tf, params, res, period=period, source=SRC, notes=notes)
    except Exception as e:
        print('lab record failed', variant, e)

# ---------------------------------------------------------------------------
GRID = [dict(Y=Y, V=V, bid=b, H=H) for Y in (3, 4, 5) for V in (4, 8) for b in (0.0, 0.25) for H in (12, 24)]

def run_timeframe(P, arm, tf, grid=GRID, label=''):
    times = (P.start, P.end)
    bounds = C.fold_bounds(times, 3)
    period = (P.start, P.end)
    log(f"\n## {tf} arm {arm}{label}  (data {P.start:%Y-%m-%d} -> {P.end:%Y-%m-%d}; fold starts {[b[0].strftime('%Y-%m-%d') for b in bounds]})\n")
    # full in-sample grid over the whole period (for the reviewer) + lab records
    rows = []
    for p in grid:
        tr = simulate(P, p, P.start, P.end + pd.Timedelta('1D'), arm=arm)
        r = C.evaluate(tr, 3, start=P.start, end=P.end)
        r1 = C.evaluate(tr[tr.entry_time < bounds[0][1]], 1)
        rows.append(dict(**p, is_n=r1['n'], is_net=r1['net'], is_pf=r1['pf'], is_wr=r1['wr'], is_bps=r1['net_bps'],
                         n_full=r['n'], f1=r['folds'][0], f2=r['folds'][1], f3=r['folds'][2], pf_full=r['pf'], bps_full=r['net_bps']))
        rec(f"{arm}_{tf}_grid_Y{p['Y']}_V{p['V']}_b{p['bid']}_H{p['H']}", tf, dict(arm=arm, **p), r, period,
            notes=f"full-period grid cell; fold1 is in-sample for WF selection; f1={r['folds'][0]:.1f}")
    table = pd.DataFrame(rows)
    run_fn = lambda p, s, e: simulate(P, p, s, e, arm=arm)
    best, oos, wf = C.walk_forward(grid, run_fn, times, n_folds=3, min_trades=10)
    res = C.oos_result(oos, times, 3)
    table['sel'] = ['*' if (r.Y == best['Y'] and r.V == best['V'] and r.bid == best['bid'] and r.H == best['H']) else '' for r in table.itertuples()]
    log(f"**Walk-forward best (fold 1):** `{best}`\n")
    log(f"**OOS folds 2+3:** {fmt(res)}\n")
    log("### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets, full period)\n")
    log("| Y | V | bid | H | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |")
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in table.itertuples():
        log(f"| {r.Y} | {r.V} | {r.bid} | {r.H} | {r.is_n} | {r.is_net:.1f} | {r.is_pf:.2f} | {r.is_wr:.2f} | {r.is_bps:.1f} | {r.n_full} | {r.f1:.1f} | {r.f2:.1f} | {r.f3:.1f} | {r.pf_full:.2f} | {r.bps_full:.1f} | {r.sel} |")
    rec(f"{arm}_{tf}_wf_oos", tf, dict(arm=arm, **best), res, period, notes='HEADLINE walk-forward OOS folds 2+3 (fold 1 = selection)')
    if len(oos):
        log("\nOOS by exit reason:\n\n| reason | n | net | avg bps |\n|---|---|---|---|")
        t = C.add_pnl(oos)
        for k, g in t.groupby('reason'):
            log(f"| {k} | {len(g)} | {g.net_pnl.sum():.1f} | {g.net_pnl.mean()/NOTIONAL*1e4:.1f} |")
        log(f"\nOOS funding paid total = {t.funding_usd.sum():.2f} USD; fees only = {t.fees_only.sum():.2f} USD; "
            f"avg hold = {t.hold_min.mean()/60:.1f} h")
    return best, oos, res, table, bounds

def oos_window_eval(P, params, bounds, **kw):
    tr = simulate(P, params, bounds[1][0], bounds[2][1] + pd.Timedelta('1D'), **kw)
    return tr, C.evaluate(tr, 3, start=bounds[0][0], end=bounds[2][1])

# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    d1h = load_1h_all()
    log(f"# flush_reversal_long -- results\n\nLoaded {len(d1h)} coins with 1h candles ({len(C.list_hl_coins())} cached top-50 + {len(d1h)-len(C.list_hl_coins())} ext).")
    member = pit_universe(d1h)
    ever = [c for c in member.columns if member[c].any()]
    ext_in = [c for c in ever if c not in C.list_hl_coins()]
    log(f"Point-in-time top-{TOP_N} by trailing-30d USD volume: {len(ever)} coins ever members; {len(ext_in)} not in the cached snapshot universe: {ext_in}")
    fetch_funding_ext(ext_in)
    funding = load_funding(ever)
    missing_f = [c for c in ever if c not in funding]
    log(f"Funding series available for {len(funding)}/{len(ever)} universe coins; missing (funding=0 assumed): {missing_f}")
    data1h = {c: d1h[c] for c in ever}
    P1 = Panel('1h', data1h, member, funding, d1h['BTC'])
    usnap = pd.read_parquet(C.DATA / 'hl_universe_all.parquet').set_index('coin')

    # ---- descriptive check: unconditional forward 12-bar returns (links to the rationale) ----
    log("\n## Descriptive: signal counts and raw forward returns (1h, Y=4,V=6, coin-specific vs market-wide)\n")
    bounds = C.fold_bounds((P1.start, P1.end), 3)
    for mw in (False, True):
        tr = simulate(P1, dict(Y=4, V=6, bid=0.0, H=12), P1.start, P1.end + pd.Timedelta('1D'), arm='B', market_wide=mw, taker_unconditional=True)
        t = C.add_pnl(tr); lab = C.fold_labels(t.entry_time, 3, bounds[0][0], bounds[2][1]) if len(t) else []
        g = [t.alt_ret[lab == k].mean() * 1e4 if len(t) and (lab == k).sum() else np.nan for k in range(3)]
        nn = [int((lab == k).sum()) for k in range(3)] if len(t) else [0, 0, 0]
        log(f"- {'market-wide (>=3 others)' if mw else 'coin-specific (<3 others)'}: n by fold {nn}; mean raw open->open(12) return bps by fold {[round(x,1) for x in g]}")

    # ---- fill-rate / adverse-selection diagnostic ----
    log("\n## Fill diagnostic (1h, Y=4,V=6,H=12, arm B): all signals taker-at-open vs filled-at-limit subsets\n")
    log("| entry | n | mean gross bps | mean net bps | fold nets |\n|---|---|---|---|---|")
    tr_u = simulate(P1, dict(Y=4, V=6, bid=0.0, H=12), P1.start, P1.end + pd.Timedelta('1D'), arm='B', taker_unconditional=True)
    ru = C.evaluate(tr_u, 3, start=P1.start, end=P1.end); tu = C.add_pnl(tr_u)
    log(f"| taker at open (all signals) | {ru['n']} | {tu.alt_ret.mean()*1e4:.1f} | {ru['net_bps']:.1f} | {[round(x,1) for x in ru['folds']]} |")
    for b in (0.0, 0.25, 0.5):
        tr_f = simulate(P1, dict(Y=4, V=6, bid=b, H=12), P1.start, P1.end + pd.Timedelta('1D'), arm='B')
        rf = C.evaluate(tr_f, 3, start=P1.start, end=P1.end); tf_ = C.add_pnl(tr_f) if len(tr_f) else None
        log(f"| maker bid at close-{b}xrange (filled only) | {rf['n']} | {(tf_.alt_ret.mean()*1e4 if tf_ is not None else float('nan')):.1f} | {rf['net_bps']:.1f} | {[round(x,1) for x in rf['folds']]} |")
        rec(f"B_1h_filldiag_b{b}", '1h', dict(arm='B', Y=4, V=6, bid=b, H=12), rf, (P1.start, P1.end), notes='fill diagnostic full period')
    rec("B_1h_filldiag_taker_open", '1h', dict(arm='B', Y=4, V=6, bid='taker_open', H=12), ru, (P1.start, P1.end), notes='all signals taker at next open (unconditional)')

    # ---- primary: 1h, arm A and arm B ----
    bestA, oosA, resA, tabA, bounds = run_timeframe(P1, 'A', '1h')
    bestB, oosB, resB, tabB, _ = run_timeframe(P1, 'B', '1h')
    headline_arm = 'A'; best, oos, res = bestA, oosA, resA
    oos_win = (bounds[1][0], bounds[2][1])

    # ---- controls on the headline (arm A, 1h) ----
    log("\n## Controls (1h, arm A, selected params, OOS window folds 2+3)\n")
    # (1) neighbours
    log("### Neighbouring parameters (no re-selection)\n")
    log("| Y | V | bid | H | n | net | pf | wr | bps | f2 | f3 |\n|---|---|---|---|---|---|---|---|---|---|---|")
    neigh = []
    for k, vals in (('Y', (3, 4, 5)), ('V', (4, 6, 8)), ('bid', (0.0, 0.25, 0.5)), ('H', (6, 12, 24))):
        for v in vals:
            if v == best[k]: continue
            p = dict(best); p[k] = v
            tr, r = oos_window_eval(P1, p, bounds, arm='A')
            neigh.append((p, r))
            log(f"| {p['Y']} | {p['V']} | {p['bid']} | {p['H']} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['net_bps']:.1f} | {r['folds'][1]:.1f} | {r['folds'][2]:.1f} |")
            rec(f"A_1h_neigh_Y{p['Y']}_V{p['V']}_b{p['bid']}_H{p['H']}", '1h', dict(arm='A', **p), r, oos_win, notes='neighbour of WF-selected params, OOS window only')
    n_pos = sum(r['net'] > 0 for _, r in neigh)
    log(f"\nneighbours positive: {n_pos}/{len(neigh)}")

    # (2) shuffle test: same mechanics on random bars (same coin, OOS window), 100 reps
    log("\n### Shuffle test (random signal bars in the same coin inside the OOS window, same mechanics, 100 reps)\n")
    real_sig = {}
    if len(oos):
        for coin, g in oos.groupby('instrument'):
            F = P1.F[coin]; real_sig[coin] = [F.index.get_loc(t) for t in g.signal_time]
    lo_i = {c: max(120, int(P1.F[c].index.searchsorted(oos_win[0]))) for c in real_sig}
    hi_i = {c: int(P1.F[c].index.searchsorted(oos_win[1])) - best['H'] - 2 for c in real_sig}
    sh = []
    for rep in range(100):
        ov = {c: list(RNG.integers(lo_i[c], max(lo_i[c] + 1, hi_i[c]), size=len(v))) for c, v in real_sig.items()}
        tr = simulate(P1, best, oos_win[0], oos_win[1] + pd.Timedelta('1D'), arm='A', sig_override=ov)
        sh.append(C.evaluate(tr, 1)['net'] if len(tr) else 0.0)
    sh = np.array(sh)
    pct = float((sh < res['net']).mean())
    log(f"real OOS net={res['net']:.1f} (n={res['n']}); shuffled mean={sh.mean():.1f} sd={sh.std():.1f} p95={np.percentile(sh,95):.1f}; real percentile={pct:.2f}")
    rec("A_1h_shuffle_mean", '1h', dict(arm='A', **best, reps=100), dict(C.empty_result(), n=res['n'], net=float(sh.mean())), oos_win,
        notes=f'shuffle control mean net; sd={sh.std():.1f}; real pct={pct:.2f}')

    # (3) beta control: random-hour longs, same coin, same H, 200 reps (open-to-open, maker-entry/taker-exit fee)
    log("\n### Beta control (random-hour longs in the same coin, hold H bars open->open, OOS window, 200 reps)\n")
    if len(oos):
        t = C.add_pnl(oos)
        real_gross = float(t.alt_ret.mean() * 1e4); real_net = res['net_bps']
        fee_bps = (FEE_M + FEE_T) * 1e4
        bc = []
        coins_n = t.instrument.value_counts()
        for rep in range(200):
            rets = []
            for coin, k in coins_n.items():
                F = P1.F[coin]; o = F['open'].values
                lo = max(120, int(F.index.searchsorted(oos_win[0]))); hi = int(F.index.searchsorted(oos_win[1])) - best['H'] - 2
                ii = RNG.integers(lo, max(lo + 1, hi), size=k)
                rets.extend(list(o[ii + 1 + best["H"]] / o[ii + 1] - 1))
            bc.append(np.mean(rets) * 1e4)
        bc = np.array(bc)
        log(f"real: gross {real_gross:.1f} bps / net {real_net:.1f} bps per trade; random-hour gross mean={bc.mean():.1f} sd={bc.std():.1f} p95={np.percentile(bc,95):.1f} "
            f"(net ~ gross - {fee_bps:.0f} bps); real gross percentile={float((bc < real_gross).mean()):.2f}")
        beta_pct = float((bc < real_gross).mean())
    else:
        beta_pct = float('nan'); log('no OOS trades')

    # (4) BTC-hedged arm
    log("\n### BTC-hedged arm (short equal notional BTC, taker both sides, BTC funding received)\n")
    trh, rh = oos_window_eval(P1, best, bounds, arm='A', hedged=True)
    log(fmt(rh, 'hedged OOS: '))
    if len(trh):
        log(f"mean alt leg {trh.alt_ret.mean()*1e4:.1f} bps, mean hedge leg {trh.hedge_ret.mean()*1e4:.1f} bps")
    rec("A_1h_btc_hedged_oos", '1h', dict(arm='A', **best, hedge='BTC'), rh, oos_win, notes='BTC-hedged control, OOS window')
    # hedged full period too
    trh_full = simulate(P1, best, P1.start, P1.end + pd.Timedelta('1D'), arm='A', hedged=True)
    rhf = C.evaluate(trh_full, 3, start=P1.start, end=P1.end)
    log(fmt(rhf, 'hedged full period: '))

    # (5) market-wide flushes and up-spike mirror (diagnostics)
    log("\n### Diagnostics: market-wide flushes (>=3 other coins) and up-spike mirror, selected params, full period\n")
    for name, kw in (('market-wide flush longs', dict(market_wide=True)), ('up-spike mirror (long after +2% high-vol bar)', dict(mirror=True)),
                     ('up-spike mirror market-wide', dict(mirror=True, market_wide=True))):
        tr = simulate(P1, best, P1.start, P1.end + pd.Timedelta('1D'), arm='A', **kw)
        r = C.evaluate(tr, 3, start=P1.start, end=P1.end)
        log(fmt(r, f'- {name}: '))
        rec(f"A_1h_diag_{name.split(' (')[0].replace(' ', '_')}", '1h', dict(arm='A', **best, **{k: str(v) for k, v in kw.items()}), r, (P1.start, P1.end), notes='diagnostic only')

    # (6) per-coin / liquidity
    log("\n### Per-coin OOS (arm A) and liquidity split (24h vol < $5M = illiquid, current snapshot)\n")
    if len(oos):
        t = C.add_pnl(oos)
        t['dayvol'] = t.instrument.map(usnap['dayNtlVlm'])
        t['illiq'] = t.dayvol < 5e6
        for il, g in t.groupby('illiq'):
            log(f"- {'illiquid' if il else 'liquid'}: n={len(g)} net={g.net_pnl.sum():.1f} bps={g.net_pnl.mean()/NOTIONAL*1e4:.1f}")
        pc = t.groupby('instrument').agg(n=('net_pnl', 'size'), net=('net_pnl', 'sum'), dayvol=('dayvol', 'first')).sort_values('net', ascending=False)
        log("\n| coin | n | net | dayNtlVlm |\n|---|---|---|---|")
        for c, r in pc.iterrows():
            log(f"| {c} | {r.n} | {r.net:.1f} | {r.dayvol/1e6:.1f}M |")
        top_share = pc.net.clip(lower=0).max() / max(pc.net.clip(lower=0).sum(), 1e-9)
        log(f"\nlargest single-coin share of positive PnL = {top_share:.2f}; coins net>0: {(pc.net>0).sum()}/{len(pc)}")
        # by signal size
        log("\nOOS by flush size (rng_pct quantiles):\n")
        t['q'] = pd.qcut(t.rng_pct, 3, labels=['small', 'mid', 'large'], duplicates='drop')
        for q, g in t.groupby('q'):
            log(f"- {q}: n={len(g)} net={g.net_pnl.sum():.1f} bps={g.net_pnl.mean()/NOTIONAL*1e4:.1f}")
        # monthly
        log("\nOOS monthly net:\n")
        for m, g in t.groupby(t.entry_time.dt.to_period('M')):
            log(f"- {m}: n={len(g)} net={g.net_pnl.sum():.1f}")

    # ---- secondary timeframes ----
    sec = {}
    for tf in ('15m', '5m'):
        cached = [c for c in C.list_hl_coins() if c in ever]
        data = {c: C.hl_candles(c, tf) for c in cached}
        Ptf = Panel(tf, data, member, funding, C.hl_candles('BTC', tf))
        bA, oA, rA, tA, bnd = run_timeframe(Ptf, 'A', tf, label=' (cached top-50 coins only, PIT membership applied)')
        tr1, r1 = oos_window_eval(Ptf, best, bnd, arm='A')
        log(f"\n1h-selected params {best} applied to {tf} OOS window: {fmt(r1)}")
        rec(f"A_{tf}_1hparams_oos", tf, dict(arm='A', **best), r1, (bnd[1][0], bnd[2][1]), notes='1h-selected params applied to secondary timeframe OOS window')
        sec[tf] = dict(best=bA, oos=rA, oos_1hparams=r1)

    # ---- verdict ----
    oos_folds = res['folds'][1:]
    crit = dict(net_pos=res['net'] > 0, pf=res['pf'] >= 1.2, n=res['n'] >= 60, folds=all(f > 0 for f in oos_folds),
                shuffle=pct >= 0.95, neigh=(n_pos >= max(1, int(0.6 * len(neigh)))), hedged_folds=all(f > 0 for f in rh['folds'][1:]),
                beta=(beta_pct >= 0.95) if not np.isnan(beta_pct) else False)
    if all(crit.values()):
        verdict = 'edge'
    elif res['net'] > 0:
        verdict = 'weak'
    else:
        verdict = 'none'
    log(f"\n## Verdict: **{verdict}**\n\ncriteria: {crit}")
    out = dict(key='flush_reversal_long', best_params=best, oos=res, oos_folds=oos_folds, crit=crit, verdict=verdict,
               armB=dict(best=bestB, oos=resB), hedged=rh, shuffle=dict(mean=float(sh.mean()), sd=float(sh.std()), pct=pct),
               beta_pct=beta_pct, secondary=sec, neighbours=[(p, r['net'], r['n']) for p, r in neigh], runtime_s=time.time() - t0)
    OUT_JSON.write_text(json.dumps(out, default=str, indent=1))
    OUT_MD.write_text('\n'.join(MD))
    print('runtime', time.time() - t0)
    return out

if __name__ == '__main__':
    main()
