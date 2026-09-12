"""key=xsec_mom_longhist  -  DECISIVE long-history test of the round-2 candidate
(h_xsec_mom30_rev1_hedged): score = z(30d ret) - z(1d ret) cross-sectionally,
long top-q, equal $ per name, weekly rebalance, optional BTC short hedge.

Data: Binance SPOT daily klines (data-api.binance.vision mirror; api.binance.com
and fapi.binance.com answer HTTP 451 here, so no perp klines / funding) for every
USDT pair in exchangeInfo INCLUDING delisted (status=BREAK) pairs -> survivorship
aware.  Stablecoins / leveraged tokens excluded.  2018-11 -> now.
Universe (point-in-time at each decision close): >= 31 daily closes, trailing-24h
quote volume >= LIQ_USD, top-TOP_N by trailing-30d quote volume.
Causality: signal at close of day D (index i), fill at OPEN of day D+1 (index i+1).
Fees: (4.5 bps taker + 5 bps slippage) = 9.5 bps per side on every fill; also
10 bps/side reported.  Hedge = BTCUSDT short (perp proxy; no funding available).
Walk-forward: grid chosen on 2019-2021 fills only; headline = 2022 -> now.
"""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa

OUT_MD = ROOT / "tests" / "h_xsec_mom_longhist.md"
OUT_JSON = ROOT / "tests" / "h_xsec_mom_longhist_result.json"
STRATEGY = "xsec_mom_longhist"
NOTIONAL = 1000.0
TOP_N, LIQ_USD, MIN_NAMES = 100, 2e6, 10
L_REV = 1
FEE_MAIN = 0.00045 + 0.0005     # per side
FEE_ALT = 0.0010
IS_START, IS_END = pd.Timestamp("2019-01-01", tz="UTC"), pd.Timestamp("2022-01-01", tz="UTC")
SEED = 11
RNG = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# panel
# ---------------------------------------------------------------------------
def load_panel():
    p = pd.read_parquet(ROOT / "data" / "binance_panel_1d.parquet")
    p["coin"] = p["symbol"].str.replace("USDT$", "", regex=True)
    p["time"] = pd.to_datetime(p["time"], utc=True).dt.floor("D")
    p = p[p["time"] >= "2018-11-01"]
    days = pd.date_range(p["time"].min(), p["time"].max(), freq="D", tz="UTC")
    O = p.pivot(index="time", columns="coin", values="open").reindex(days)
    Cl = p.pivot(index="time", columns="coin", values="close").reindex(days)
    QV = p.pivot(index="time", columns="coin", values="quote_volume").reindex(days)
    coins = list(Cl.columns)
    vol30 = QV.rolling(30, min_periods=20).sum()
    nclose = Cl.notna().astype(float).rolling(31, min_periods=1).sum()
    rets = {L: (Cl / Cl.shift(L) - 1.0).values for L in (1, 7, 14, 21, 28, 30)}
    btc_sma = Cl["BTC"].rolling(200).mean()
    bull = (Cl["BTC"] > btc_sma).values
    return dict(days=days, coins=coins, O=O.values, Cl=Cl.values, QV=QV.values, vol30=vol30.values,
                nclose=nclose.values, rets=rets, bull=bull, btc=Cl["BTC"].values)

P = load_panel()
DAYS, COINS = P["days"], P["coins"]
CIDX = {c: j for j, c in enumerate(COINS)}
BTC = CIDX["BTC"]
N_D = len(DAYS)

def universe_mask(top_n=TOP_N, liq=LIQ_USD):
    """eligible at decision index i (fill at i+1)."""
    O_next = np.vstack([P["O"][1:], np.full((1, len(COINS)), np.nan)])
    ok = np.isfinite(P["rets"][30]) & np.isfinite(P["rets"][1]) & np.isfinite(O_next) \
        & np.isfinite(P["vol30"]) & (P["QV"] >= liq) & (P["nclose"] >= 31)
    v = np.where(ok, P["vol30"], -np.inf)
    mask = np.zeros_like(ok)
    for i in range(ok.shape[0]):
        n_ok = int(ok[i].sum())
        if n_ok == 0: continue
        top = np.argsort(-v[i])[:min(top_n, n_ok)]
        mask[i, top] = True
    return mask

MASKS = {}
def get_mask(top_n, liq):
    k = (top_n, liq)
    if k not in MASKS: MASKS[k] = universe_mask(top_n, liq)
    return MASKS[k]

def zs(x):
    m, s = np.nanmean(x), np.nanstd(x)
    return (x - m) / s if s > 0 else np.zeros_like(x)

def last_close_before(j, f):
    """delisting exit: last finite close strictly before fill index f."""
    col = P["Cl"][:f, j]
    idx = np.where(np.isfinite(col))[0]
    return (col[idx[-1]], idx[-1]) if len(idx) else (np.nan, None)

# ---------------------------------------------------------------------------
# strategy
# ---------------------------------------------------------------------------
_CACHE = {}
def build_trades(params, start=None, end=None):
    """Returns (trades DataFrame, diag dict).  Rebalance decisions whose FILL
    date is in [start, end)."""
    key = json.dumps(params, sort_keys=True, default=str) + str(start) + str(end)
    if key in _CACHE: return _CACHE[key]
    R = int(params["rebal_d"]); q = float(params["quantile"]); hedge = int(params["hedge"])
    sig = params.get("signal", "combo"); L = int(params.get("l_mom", 30))
    fee = float(params.get("fee", FEE_MAIN)); phase = int(params.get("_phase", 0)) % R
    shuffle = int(params.get("_shuffle", 0))
    mask = get_mask(int(params.get("top_n", TOP_N)), float(params.get("liq", LIQ_USD)))
    s = C._utc(start or "2019-01-01"); e = C._utc(end) if end else DAYS[-1] + pd.Timedelta(days=1)
    fill_idx = [f for f in range(1, N_D) if DAYS[f] >= s and DAYS[f] < e]
    fill_idx = fill_idx[phase::R]
    if not fill_idx: return pd.DataFrame(), {}
    rows = []; open_pos = {}; short_pos = {}; interval = []   # interval = per-rebalance book pnl (mark-to-market)
    n_univ, n_long, turn_num, turn_den = [], [], 0, 0
    hedge_H, hedge_entry, hedge_f = 0.0, np.nan, None
    delist_exits = 0
    prev_f = None
    def mtm(f):
        """mark book at open of fill index f, close positions of delisted names."""
        pnl = 0.0
        for j, pos in list(open_pos.items()):
            px = P["O"][f, j]
            if not np.isfinite(px):
                px, _ = last_close_before(j, f)
            pnl += pos["qty"] * (px - pos["mark"]); pos["mark"] = px
        for j, pos in list(short_pos.items()):
            px = P["O"][f, j]
            if not np.isfinite(px):
                px, _ = last_close_before(j, f)
            pnl -= pos["qty"] * (px - pos["mark"]); pos["mark"] = px
        if hedge_H > 0:
            pnl -= hedge_H * (P["O"][f, BTC] / hedge_entry_mark[0] - 1.0); hedge_entry_mark[0] = P["O"][f, BTC]
        return pnl
    hedge_entry_mark = [np.nan]
    for f in fill_idx:
        i = f - 1; t_fill = DAYS[f]
        fees_now = 0.0
        # --- mark to market since previous rebalance
        if prev_f is not None:
            ipnl = mtm(f)
        else:
            ipnl = 0.0
        # --- signal
        m = mask[i]; idx = np.where(m)[0]; n_univ.append(len(idx))
        if len(idx) < MIN_NAMES:
            target = set(); short_target = set()
        else:
            if sig == "combo": sc = zs(P["rets"][L][i, idx]) - zs(P["rets"][L_REV][i, idx])
            elif sig == "mom": sc = zs(P["rets"][L][i, idx])
            elif sig == "rev": sc = -zs(P["rets"][L_REV][i, idx])
            else: raise ValueError(sig)
            if shuffle: sc = RNG.permutation(sc)
            k = max(1, int(np.floor(len(idx) * q)))
            order = np.argsort(-sc); target = set(idx[order[:k]])
            short_target = set(idx[order[-k:]]) if hedge == 2 else set()
        # --- close longs that left the bucket (or got delisted)
        for j in list(open_pos):
            if j not in target:
                pos = open_pos.pop(j); px = P["O"][f, j]; dl = False
                if not np.isfinite(px):
                    px, li = last_close_before(j, f); dl = True; delist_exits += 1
                    t_exit = DAYS[li] if li is not None else t_fill
                else:
                    t_exit = t_fill
                nx = pos["qty"] * px; fee_x = nx * fee; fees_now += fee_x
                rows.append(dict(entry_time=pos["entry_time"], exit_time=t_exit, side=1, entry_px=pos["entry_px"],
                                 exit_px=px, qty=pos["qty"], notional_usd=NOTIONAL, fee_usd=NOTIONAL * fee + fee_x,
                                 instrument=COINS[j], delist=dl, vol24=pos["vol24"], vol30=pos["vol30"], leg="long"))
        # --- short bucket (hedge==2): close shorts that left, open new
        for j in list(short_pos):
            if j not in short_target:
                pos = short_pos.pop(j); px = P["O"][f, j]; dl = False
                if not np.isfinite(px):
                    px, li = last_close_before(j, f); dl = True; delist_exits += 1
                nx = pos["qty"] * px; fees_now += nx * fee
                rows.append(dict(entry_time=pos["entry_time"], exit_time=t_fill, side=-1, entry_px=pos["entry_px"], exit_px=px,
                                 qty=pos["qty"], notional_usd=NOTIONAL, fee_usd=NOTIONAL * fee + nx * fee, instrument=COINS[j],
                                 delist=dl, vol24=pos["vol24"], vol30=pos["vol30"], leg="short"))
        for j in short_target:
            if j in short_pos: continue
            px = P["O"][f, j]
            if not np.isfinite(px): continue
            fees_now += NOTIONAL * fee
            short_pos[j] = dict(entry_time=t_fill, entry_px=px, qty=NOTIONAL / px, mark=px, vol24=P["QV"][i, j], vol30=P["vol30"][i, j])
        # --- open new longs
        changed = 0
        for j in target:
            if j in open_pos: continue
            px = P["O"][f, j]
            if not np.isfinite(px): continue
            changed += 1; fees_now += NOTIONAL * fee
            open_pos[j] = dict(entry_time=t_fill, entry_px=px, qty=NOTIONAL / px, mark=px,
                               vol24=P["QV"][i, j], vol30=P["vol30"][i, j])
        turn_num += changed; turn_den += max(len(target), 1); n_long.append(len(open_pos))
        # --- hedge resize
        if hedge == 1:
            H_new = NOTIONAL * len(open_pos); px_b = P["O"][f, BTC]
            if hedge_f is not None:      # close previous hedge interval row
                fee_adj = abs(H_new - hedge_H) * fee; fees_now += fee_adj
                rows.append(dict(entry_time=DAYS[hedge_f], exit_time=t_fill, side=-1, entry_px=hedge_entry, exit_px=px_b,
                                 qty=hedge_H / hedge_entry, notional_usd=hedge_H, fee_usd=fee_adj, instrument="BTC",
                                 delist=False, vol24=np.nan, vol30=np.nan, leg="hedge"))
            else:
                fees_now += H_new * fee
                if H_new > 0: rows.append(dict(entry_time=t_fill, exit_time=t_fill, side=-1, entry_px=px_b, exit_px=px_b,
                                              qty=0.0, notional_usd=0.0, fee_usd=H_new * fee, instrument="BTC", delist=False,
                                              vol24=np.nan, vol30=np.nan, leg="hedge"))
            hedge_H, hedge_entry, hedge_f = H_new, px_b, (f if H_new > 0 else None)
            hedge_entry_mark[0] = px_b
        if prev_f is not None:
            interval.append(dict(t=DAYS[prev_f], t_end=t_fill, pnl=ipnl - fees_prev_carry, bull=bool(P["bull"][prev_f - 1]),
                                 n_long=n_prev_long))
        fees_prev_carry = fees_now; n_prev_long = len(open_pos); prev_f = f
    # --- final close at last day open
    f_end = N_D - 1
    ipnl = mtm(f_end); fees_final = 0.0
    for j, pos in list(open_pos.items()):
        if pos["entry_time"] >= DAYS[f_end]: continue
        px = P["O"][f_end, j]; dl = False; t_exit = DAYS[f_end]
        if not np.isfinite(px):
            px, li = last_close_before(j, f_end); dl = True; delist_exits += 1; t_exit = DAYS[li]
        nx = pos["qty"] * px; fees_final += nx * fee
        rows.append(dict(entry_time=pos["entry_time"], exit_time=t_exit, side=1, entry_px=pos["entry_px"], exit_px=px,
                         qty=pos["qty"], notional_usd=NOTIONAL, fee_usd=NOTIONAL * fee + nx * fee, instrument=COINS[j],
                         delist=dl, vol24=pos["vol24"], vol30=pos["vol30"], leg="long"))
    for j, pos in list(short_pos.items()):
        if pos["entry_time"] >= DAYS[f_end]: continue
        px = P["O"][f_end, j]; dl = False; t_exit = DAYS[f_end]
        if not np.isfinite(px):
            px, li = last_close_before(j, f_end); dl = True; delist_exits += 1; t_exit = DAYS[li]
        nx = pos["qty"] * px; fees_final += nx * fee
        rows.append(dict(entry_time=pos["entry_time"], exit_time=t_exit, side=-1, entry_px=pos["entry_px"], exit_px=px,
                         qty=pos["qty"], notional_usd=NOTIONAL, fee_usd=NOTIONAL * fee + nx * fee, instrument=COINS[j],
                         delist=dl, vol24=pos["vol24"], vol30=pos["vol30"], leg="short"))
    if hedge == 1 and hedge_f is not None and hedge_f < f_end:
        fees_final += hedge_H * fee
        rows.append(dict(entry_time=DAYS[hedge_f], exit_time=DAYS[f_end], side=-1, entry_px=hedge_entry, exit_px=P["O"][f_end, BTC],
                         qty=hedge_H / hedge_entry, notional_usd=hedge_H, fee_usd=hedge_H * fee, instrument="BTC",
                         delist=False, vol24=np.nan, vol30=np.nan, leg="hedge"))
    if prev_f is not None and f_end > prev_f:
        interval.append(dict(t=DAYS[prev_f], t_end=DAYS[f_end], pnl=ipnl - fees_prev_carry - fees_final, bull=bool(P["bull"][prev_f - 1]), n_long=n_prev_long))
    trades = pd.DataFrame(rows)
    diag = dict(n_rebal=len(fill_idx), turnover=(turn_num / turn_den if turn_den else np.nan),
                avg_univ=float(np.mean(n_univ)) if n_univ else 0, avg_long=float(np.mean(n_long)) if n_long else 0,
                delist_exits=delist_exits, intervals=pd.DataFrame(interval))
    _CACHE[key] = (trades, diag)
    return trades, diag

def run_fn(params, start, end):
    tr, _ = build_trades(params, start, end)
    return tr

def name_of(p):
    return f"{p.get('signal','combo')}_L{p.get('l_mom',30)}_R{p['rebal_d']}_q{p['quantile']}_h{p['hedge']}" + \
           (f"_fee{int(p['fee']*1e4)}" if 'fee' in p else "") + (f"_top{p['top_n']}" if 'top_n' in p else "") + \
           (f"_liq{int(p['liq']/1e6)}M" if 'liq' in p else "")

def summarize(trades, diag, start, end):
    r = C.evaluate(trades, n_folds=1) if len(trades) else C.empty_result(1)
    longs = trades[trades["leg"] == "long"] if len(trades) else trades
    rl = C.evaluate(longs, n_folds=1) if len(longs) else C.empty_result(1)
    iv = diag.get("intervals", pd.DataFrame())
    if len(iv):
        iv = iv[(iv["t"] >= C._utc(start)) & (iv["t"] < C._utc(end))]
    eq = iv["pnl"].cumsum().values if len(iv) else np.array([0.0])
    dd = float((np.maximum.accumulate(np.concatenate([[0.0], eq])) [1:] - eq).max()) if len(iv) else 0.0
    tl = C.add_pnl(longs) if len(longs) else pd.DataFrame(columns=["net_pnl"])
    top5 = float(tl["net_pnl"].nlargest(5).sum() / tl["net_pnl"].sum()) if len(tl) and tl["net_pnl"].sum() > 0 else np.nan
    top3_removed = float(tl["net_pnl"].sum() - tl["net_pnl"].nlargest(3).sum()) if len(tl) else 0.0
    if hedge_rows := (trades["leg"] == "hedge").sum() if len(trades) else 0:
        top3_removed += float(C.add_pnl(trades[trades["leg"] == "hedge"])["net_pnl"].sum())
    return dict(n_trades=int(r["n"]), n_long=int(rl["n"]), n_rebal=int(len(iv)), net=r["net"], pf=r["pf"], wr=r["wr"],
                long_net=rl["net"], long_pf=rl["pf"], hedge_net=r["net"] - rl["net"], fees=r["fees"],
                max_dd=dd, turnover=diag.get("turnover", np.nan), avg_univ=diag.get("avg_univ", 0), avg_long=diag.get("avg_long", 0),
                top5_frac=top5, ex_top3=top3_removed, iv_mean=float(iv["pnl"].mean()) if len(iv) else 0.0,
                iv_t=float(iv["pnl"].mean() / iv["pnl"].std(ddof=1) * np.sqrt(len(iv))) if len(iv) > 2 else 0.0,
                iv_pos=float((iv["pnl"] > 0).mean()) if len(iv) else 0.0, delist=diag.get("delist_exits", 0),
                bull_net=float(iv.loc[iv["bull"], "pnl"].sum()) if len(iv) else 0.0,
                bear_net=float(iv.loc[~iv["bull"], "pnl"].sum()) if len(iv) else 0.0,
                bull_n=int(iv["bull"].sum()) if len(iv) else 0, bear_n=int((~iv["bull"]).sum()) if len(iv) else 0)

def by_year(params, years):
    out = {}
    for y in years:
        tr, dg = build_trades(params, f"{y}-01-01", f"{y+1}-01-01")
        out[y] = summarize(tr, dg, f"{y}-01-01", f"{y+1}-01-01")
    return out

def md_table(df, cols=None, fmt=2):
    df = df if cols is None else df[cols]
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f"{v:.{fmt}f}" if isinstance(v, float) else str(v) for v in r.values) + " |")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    END = DAYS[-1] + pd.Timedelta(days=1)
    YEARS = list(range(2019, DAYS[-1].year + 1))
    OOS_S, OOS_E = "2022-01-01", str(END.date())
    print(f"panel: {len(COINS)} coins, {DAYS[0].date()} -> {DAYS[-1].date()}", flush=True)
    m = get_mask(TOP_N, LIQ_USD)
    univ_sz = pd.Series(m.sum(axis=1), index=DAYS)
    print("universe size by year:", univ_sz.groupby(univ_sz.index.year).mean().round(1).to_dict(), flush=True)

    # ---- main grid (combo signal) : walk-forward selection on IS (2019-2021)
    grid = [dict(rebal_d=R, quantile=q, hedge=h, signal="combo", l_mom=30)
            for R, q, h in itertools.product([7, 14], [0.1, 0.2], [0, 1])]
    arms = [dict(rebal_d=R, quantile=q, hedge=h, signal=s, l_mom=30)
            for R, q, h, s in itertools.product([7, 14], [0.1, 0.2], [0, 1], ["mom", "rev"])]
    lookbacks = [dict(rebal_d=R, quantile=q, hedge=h, signal="combo", l_mom=L)
                 for R, q, h, L in itertools.product([7, 14], [0.1, 0.2], [0, 1], [7, 14, 21, 28])]
    mom_lb = [dict(rebal_d=7, quantile=0.2, hedge=h, signal="mom", l_mom=L) for h, L in itertools.product([0, 1], [7, 14, 21, 28])]
    rows = []
    def eval_variant(p, tag):
        tr_is, dg_is = build_trades(p, IS_START, IS_END); tr_oos, dg_oos = build_trades(p, OOS_S, OOS_E)
        s_is = summarize(tr_is, dg_is, IS_START, IS_END); s_oos = summarize(tr_oos, dg_oos, OOS_S, OOS_E)
        yr = by_year(p, YEARS)
        row = dict(name=name_of(p), tag=tag, is_n=s_is["n_trades"], is_net=s_is["net"], is_pf=s_is["pf"],
                   oos_n=s_oos["n_trades"], oos_long_n=s_oos["n_long"], oos_rebal=s_oos["n_rebal"], oos_net=s_oos["net"], oos_pf=s_oos["pf"],
                   oos_long_net=s_oos["long_net"], oos_hedge_net=s_oos["hedge_net"], oos_fees=s_oos["fees"], oos_dd=s_oos["max_dd"],
                   turnover=s_oos["turnover"], avg_univ=s_oos["avg_univ"], avg_long=s_oos["avg_long"], top5=s_oos["top5_frac"],
                   ex_top3=s_oos["ex_top3"], iv_t=s_oos["iv_t"], iv_pos=s_oos["iv_pos"], bull=s_oos["bull_net"], bear=s_oos["bear_net"],
                   delist=s_oos["delist"])
        for y in YEARS: row[f"y{y}"] = yr[y]["net"]
        rows.append(row)
        C.record_to_lab(STRATEGY, f"{tag}:{name_of(p)}", "BINANCE_SPOT_USDT_PANEL", "1d", p,
                        dict(C.evaluate(tr_oos, n_folds=1) if len(tr_oos) else C.empty_result(1),
                             folds=[yr[y]["net"] for y in YEARS if y >= 2022]),
                        period=(OOS_S, OOS_E), source="tests/h_xsec_mom_longhist.py",
                        notes=f"OOS 2022+ (IS 2019-21 net {s_is['net']:.0f}); fee {p.get('fee', FEE_MAIN)*1e4:.1f}bps/side; per-year " +
                              json.dumps({y: round(yr[y]['net']) for y in YEARS}))
        return row, yr
    YR = {}
    for p in grid: r, yr = eval_variant(p, "grid"); YR[r["name"]] = yr
    is_tab = pd.DataFrame(rows)
    elig = is_tab[is_tab["is_n"] >= 10]
    best_row = (elig if len(elig) else is_tab).sort_values("is_net", ascending=False).iloc[0]
    best = grid[int(is_tab.index[is_tab["name"] == best_row["name"]][0])]
    print("selected on IS:", best, flush=True)
    for p in arms + lookbacks + mom_lb:
        r, yr = eval_variant(p, "arm" if p["signal"] != "combo" else "lookback"); YR[r["name"]] = yr
    # fee 10bps + universe neighbours + phases (same structure as best)
    ls_rows = [dict(rebal_d=R, quantile=0.2, hedge=2, signal=sg, l_mom=30) for R, sg in itertools.product([7, 14], ["combo", "mom", "rev"])] + \
              [dict(rebal_d=7, quantile=0.2, hedge=2, signal="mom", l_mom=L) for L in (7, 14, 21)]
    for p in ls_rows: r, yr = eval_variant(p, "longshort"); YR[r["name"]] = yr
    # score-quintile forward-return table (equal-weight, fill i+1 open -> i+1+R open, gross of fees)
    def quintile_table(sig, L, R, mask):
        out = {}
        O = P["O"]; fwd = np.full_like(O, np.nan); fwd[:-(R + 1)] = O[R + 1:] / O[1:-R] - 1
        for i in range(1, N_D - R - 1, R):
            if DAYS[i] < pd.Timestamp("2019-01-01", tz="UTC"): continue
            idx = np.where(mask[i])[0]
            if len(idx) < MIN_NAMES: continue
            if sig == "combo": sc = zs(P["rets"][L][i, idx]) - zs(P["rets"][1][i, idx])
            elif sig == "mom": sc = zs(P["rets"][L][i, idx])
            else: sc = -zs(P["rets"][1][i, idx])
            fr = fwd[i, idx]; ok = np.isfinite(fr)
            if ok.sum() < MIN_NAMES: continue
            qs = pd.qcut(pd.Series(sc[ok]).rank(method="first"), 5, labels=False)
            out[DAYS[i]] = [float(np.mean(fr[ok][qs == g])) for g in range(5)]
        df = pd.DataFrame(out, index=[f"Q{g+1}" for g in range(5)]).T
        df["Q5-Q1"] = df["Q5"] - df["Q1"]
        g = df.groupby(df.index.year).mean() * 100
        g["n"] = df.groupby(df.index.year).size()
        g["t(Q5-Q1)"] = df.groupby(df.index.year)["Q5-Q1"].apply(lambda x: x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else np.nan)
        return g.reset_index().rename(columns={"index": "year"})
    qt = {f"{sg}_L{L}_R{R}": quintile_table(sg, L, R, get_mask(TOP_N, LIQ_USD)) for sg, L, R in
          [("combo", 30, 14), ("combo", 30, 7), ("mom", 30, 7), ("rev", 1, 7), ("mom", 7, 7), ("mom", 21, 7)]}
    nb = [dict(best, fee=FEE_ALT), dict(best, top_n=50), dict(best, liq=5e6), dict(best, top_n=200), dict(best, liq=1e6)]
    for p in nb: r, yr = eval_variant(p, "neighbour"); YR[r["name"]] = yr
    tab = pd.DataFrame(rows)

    # ---- headline
    tr_oos, dg_oos = build_trades(best, OOS_S, OOS_E)
    H = summarize(tr_oos, dg_oos, OOS_S, OOS_E)
    yr_best = YR[name_of(best)]
    oos_years = [y for y in YEARS if y >= 2022]
    # ---- shuffle
    sh = []
    for k in range(40):
        p = dict(best, _shuffle=1, _seed=k)
        tr, dg = build_trades(p, OOS_S, OOS_E); sh.append(summarize(tr, dg, OOS_S, OOS_E)["net"])
    sh = np.array(sh)
    # ---- phases
    ph = []
    for k in range(int(best["rebal_d"])):
        tr, dg = build_trades(dict(best, _phase=k), OOS_S, OOS_E); s = summarize(tr, dg, OOS_S, OOS_E)
        ph.append(dict(phase=k, oos_n=s["n_trades"], oos_net=s["net"], oos_pf=s["pf"], iv_t=s["iv_t"]))
    ph = pd.DataFrame(ph)
    # ---- liquidity / concentration
    tl = C.add_pnl(tr_oos[tr_oos["leg"] == "long"])
    liq_split = tl.groupby(tl["vol24"] < 10e6)["net_pnl"].agg(["size", "sum"]).to_dict("index")
    tl["vol30_tercile"] = pd.qcut(tl["vol30"].rank(method="first"), 3, labels=["low", "mid", "high"])
    ter = tl.groupby("vol30_tercile", observed=True)["net_pnl"].agg(["size", "sum", "mean"])
    percoin = tl.groupby("instrument")["net_pnl"].agg(["size", "sum"]).sort_values("sum")
    top_trades = tl.nlargest(5, "net_pnl")[["instrument", "entry_time", "exit_time", "net_pnl"]]
    # ---- one-param neighbours of best in the grid
    nb_names = [name_of(dict(best, rebal_d=14 if best["rebal_d"] == 7 else 7)), name_of(dict(best, quantile=0.1 if best["quantile"] == 0.2 else 0.2)),
                name_of(dict(best, hedge=1 - best["hedge"])), name_of(dict(best, l_mom=28)), name_of(dict(best, l_mom=21))]
    nb_tab = tab[tab["name"].isin(nb_names)]
    nb_tab = pd.concat([nb_tab, tab[tab["tag"] == "neighbour"]]).drop_duplicates("name")

    # ---- criteria
    oos_fold_nets = [yr_best[y]["net"] for y in oos_years]
    crit = dict(net_pos=H["net"] > 0, pf=H["pf"] >= 1.2, n=H["n_long"] >= 60 and H["n_rebal"] >= 60,
                folds=all(v > 0 for v in oos_fold_nets), shuffle=float((sh >= H["net"]).mean()) < 0.05,
                neighbours=bool((nb_tab["oos_net"] > 0).mean() >= 0.75), ex_top3=H["ex_top3"] > 0,
                phases=bool((ph["oos_net"] > 0).all()))
    core = ["net_pos", "pf", "n", "folds", "shuffle", "neighbours", "ex_top3"]
    if all(crit[k] for k in core): verdict = "edge"
    elif H["net"] > 0 and sum(not crit[k] for k in core) <= 1: verdict = "weak"
    else: verdict = "none"

    # ---- md
    yr_tab = pd.DataFrame([dict(year=y, n_rebal=v["n_rebal"], n_trades=v["n_trades"], net=v["net"], pf=v["pf"], long_net=v["long_net"],
                                hedge_net=v["hedge_net"], fees=v["fees"], max_dd=v["max_dd"], turnover=v["turnover"], avg_univ=v["avg_univ"],
                                avg_long=v["avg_long"], top5_frac=v["top5_frac"], iv_t=v["iv_t"], bull_net=v["bull_net"], bear_net=v["bear_net"],
                                bull_n=v["bull_n"], bear_n=v["bear_n"], delist=v["delist"]) for y, v in yr_best.items()])
    cols_main = ["name", "is_n", "is_net", "is_pf", "oos_n", "oos_long_n", "oos_rebal", "oos_net", "oos_pf", "oos_long_net", "oos_hedge_net",
                 "oos_fees", "oos_dd", "turnover", "avg_long", "top5", "ex_top3", "iv_t", "iv_pos", "bull", "bear"] + [f"y{y}" for y in YEARS]
    md = [f"# h_xsec_mom_longhist - long-history (2019->{DAYS[-1].year}) test of z(30d)-z(1d) long book, Binance spot daily panel", "",
          f"Data: Binance SPOT daily klines via data-api.binance.vision (api.binance.com / fapi.binance.com -> HTTP 451 here; no perp klines, "
          f"NO funding). {len(COINS)} USDT pairs incl. delisted (BREAK) -> survivorship-aware; stables/leveraged tokens excluded. "
          f"{DAYS[0].date()} -> {DAYS[-1].date()}.",
          f"Universe (PIT at each decision close): >=31 closes, 24h quote vol >= ${LIQ_USD/1e6:.0f}M, top-{TOP_N} by 30d quote vol. Mean size by year: "
          + json.dumps(univ_sz.groupby(univ_sz.index.year).mean().round(0).astype(int).to_dict()),
          f"Execution: signal at day-D close, fill at day-D+1 OPEN, {FEE_MAIN*1e4:.1f} bps/side (4.5 taker + 5 slippage) on every fill; "
          f"$1000/name; names staying in the bucket are kept; equal-notional BTC short hedge resized at each rebalance (fee on adjustment; "
          f"perp proxy = BTCUSDT spot, no funding). Walk-forward: grid (rebal 7/14, q 10/20%, hedge 0/1; combo signal, L=30) chosen on "
          f"2019-2021 fills, OOS = 2022 -> {DAYS[-1].date()}. Folds = calendar years.", "",
          f"## Headline (walk-forward OOS 2022+)", "", f"Selected on IS: `{best}` (IS net {best_row['is_net']:.0f}, IS PF {best_row['is_pf']:.2f})", "",
          f"| n trades | n long | n rebal | net USD | PF | WR | long net | hedge net | fees | maxDD (MTM) | turnover | top5 frac | ex-top3 | iv t | iv pos |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
          f"| {H['n_trades']} | {H['n_long']} | {H['n_rebal']} | {H['net']:.0f} | {H['pf']:.2f} | {H['wr']:.2f} | {H['long_net']:.0f} | {H['hedge_net']:.0f} | "
          f"{H['fees']:.0f} | {H['max_dd']:.0f} | {H['turnover']:.2f} | {H['top5_frac']:.2f} | {H['ex_top3']:.0f} | {H['iv_t']:.2f} | {H['iv_pos']:.2f} |", "",
          f"OOS by calendar year: " + ", ".join(f"{y}: {yr_best[y]['net']:.0f}" for y in oos_years), "",
          "## Per-year (selected params; 2019-2021 = in-sample)", "", md_table(yr_tab), "",
          f"Regime (BTC > 200d SMA at decision): OOS bull net {H['bull_net']:.0f} ({H['bull_n']} intervals), bear net {H['bear_net']:.0f} ({H['bear_n']} intervals).", "",
          "## Grid (combo signal; IS 2019-21 -> OOS 2022+, per-year nets)", "", md_table(tab[tab["tag"] == "grid"], cols_main), "",
          "## Momentum-only / reversal-only arms", "", md_table(tab[tab["tag"] == "arm"], cols_main), "",
          "## Lookback neighbours (Liu-Tsyvinski 1-4 week momentum; combo + mom-only)", "", md_table(tab[tab["tag"] == "lookback"], cols_main), "",
          "## Fee / universe neighbours of the selected structure", "", md_table(tab[tab["tag"] == "neighbour"], cols_main), "",
          "## Diagnostic: dollar-neutral long top-20% / short bottom-20% (perp proxy, same fees; NOT part of the hypothesis)", "",
          md_table(tab[tab["tag"] == "longshort"], cols_main), "",
          "## Diagnostic: equal-weight forward return by score quintile (gross, % per holding period; Q5 = highest score = the long bucket)", "",
          *sum([[f"### {k}", "", md_table(v), ""] for k, v in qt.items()], []),
          "## Sanity checks", "",
          f"- Shuffle (random bucket, 40 reps, OOS): mean {sh.mean():.0f}, sd {sh.std():.0f}, P(shuffle >= real) = {(sh >= H['net']).mean():.2f}; real {H['net']:.0f}.",
          f"- One-param neighbours positive OOS: {(nb_tab['oos_net'] > 0).sum()}/{len(nb_tab)}", md_table(nb_tab, ["name", "oos_n", "oos_net", "oos_pf", "iv_t"] + [f"y{y}" for y in oos_years]), "",
          f"- Top-3 removal (long leg + hedge): {H['ex_top3']:.0f}; top-5 fraction of long PnL {H['top5_frac']:.2f}", "",
          "Top 5 OOS long trades:", "", md_table(top_trades.assign(entry_time=top_trades['entry_time'].dt.date.astype(str), exit_time=top_trades['exit_time'].dt.date.astype(str))), "",
          f"- Liquidity split of OOS long trades (thin = 24h vol < $10M): {liq_split}", "",
          "Vol30 terciles of OOS long trades:", "", md_table(ter.reset_index()), "",
          "- Rebalance-phase robustness (OOS):", "", md_table(ph), "",
          "- Per-rebalance book PnL (MTM incl. fees): " + f"OOS n={H['n_rebal']}, mean {H['iv_mean']:.1f}, t={H['iv_t']:.2f}, positive {H['iv_pos']:.2f}", "",
          f"- Delisting exits in OOS: {H['delist']} (exit at last available close).", "",
          "Per-coin OOS long PnL (worst 10 / best 10):", "", md_table(pd.concat([percoin.head(10), percoin.tail(10)]).reset_index()), "",
          "## Criteria", "", f"`{crit}`", "", f"## Verdict: **{verdict}**", ""]
    OUT_MD.write_text("\n".join(md))
    res = dict(key="xsec_mom_longhist", best=best, oos=H, oos_years={y: yr_best[y]["net"] for y in oos_years}, shuffle=dict(mean=float(sh.mean()), sd=float(sh.std()), p=float((sh >= H["net"]).mean())),
               criteria={k: bool(v) for k, v in crit.items()}, verdict=verdict, univ_by_year=univ_sz.groupby(univ_sz.index.year).mean().round(1).to_dict())
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str))
    tab.to_csv(ROOT / "tests" / "h_xsec_mom_longhist_table.csv", index=False)
    print(json.dumps(res, indent=1, default=str))
