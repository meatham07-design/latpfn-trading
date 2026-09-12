"""Edge-hunt round 1 -- key: crypto_seasonality

Hypothesis: time-of-day / day-of-week / funding-clock seasonality in crypto
(BTC, ETH) is tradeable net of Hyperliquid taker fees.

Rules tested (all are pure clock functions -> causal by construction; the
only data-fitted component, the hour ranking for the 'hours' family, is
estimated on FOLD 1 ONLY and frozen for folds 2+3):
  hours     : long the top-K / short the bottom-K UTC hours by fold-1 mean
              next-open return (K=1..4, dir long/short/both)
  weekend   : hold Fri 21:00 UTC -> Sun 21:00 UTC (long/short)
  us_sess   : hold 13:00 -> 20:00 UTC, weekdays (long/short)
  asia_sess : hold 00:00 -> 08:00 UTC, weekdays (long/short)
  fund_pre  : hold the hour BEFORE the legacy 00/08/16 UTC settlement (long/short)
  fund_post : hold the hour AFTER  the legacy 00/08/16 UTC settlement (long/short)

Execution model: decision at the close of bar t-1, fill at the OPEN of bar t
(entry) and the OPEN of the bar after the last held bar (exit).  Adjacent held
hours are merged into one position so fees are paid once per run.  Fees =
Hyperliquid TAKER both sides (0.045% x 2 = 9 bps round trip); $10k notional.
Primary data: yfinance BTC-USD / ETH-USD 1h (730d) as the price proxy for the
HL perp.  Secondary / per-coin: Hyperliquid 1h candles (208d, 51 coins).
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import numpy as np, pandas as pd

EDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDGE))
import common as C  # noqa: E402

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 40)
NOTIONAL = 10_000.0
STRATEGY = "crypto_seasonality"
RNG = np.random.default_rng(42)
OUT_MD = Path(__file__).with_suffix(".md")
LINES: list[str] = []


def say(s=""):
    print(s); LINES.append(str(s))


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_yf(sym):
    b = C.yf_bars(sym)[["open", "high", "low", "close", "volume"]].copy()
    b = b[~b.index.duplicated()]
    b["ro"] = b["open"].shift(-1) / b["open"] - 1.0        # return captured by open->next open
    b["gap_ok"] = (b.index.to_series().shift(-1) - b.index.to_series()) == pd.Timedelta("1h")
    return b


def load_hl(coin):
    b = C.hl_candles(coin, "1h")[["open", "high", "low", "close", "volume"]].copy()
    b = b[~b.index.duplicated()]
    b["ro"] = b["open"].shift(-1) / b["open"] - 1.0
    b["gap_ok"] = (b.index.to_series().shift(-1) - b.index.to_series()) == pd.Timedelta("1h")
    return b


# ---------------------------------------------------------------------------
# hold masks (True = in position during that bar). Pure clock functions.
# ---------------------------------------------------------------------------
def mask_hours(idx, hours):
    return pd.Series(np.isin(idx.hour, list(hours)), index=idx)


def mask_weekend(idx, start_h=21, end_h=21):
    dow, h = idx.dayofweek, idx.hour
    m = ((dow == 4) & (h >= start_h)) | (dow == 5) | ((dow == 6) & (h < end_h))
    return pd.Series(m, index=idx)


def mask_session(idx, h0, h1, weekdays_only=True):
    m = (idx.hour >= h0) & (idx.hour < h1)
    if weekdays_only:
        m &= idx.dayofweek < 5
    return pd.Series(m, index=idx)


def mask_fund(idx, pre=True, clock=(0, 8, 16)):
    hs = [(c - 1) % 24 for c in clock] if pre else list(clock)
    return mask_hours(idx, hs)


# ---------------------------------------------------------------------------
# trades from a hold mask: merge consecutive held bars into one position
# ---------------------------------------------------------------------------
def trades_from_mask(bars, mask, side, instrument, maker=False):
    m = mask.reindex(bars.index).fillna(False).values.astype(bool)
    gap = bars["gap_ok"].values
    op = bars["open"].values
    idx = bars.index
    rows = []
    i, n = 0, len(bars)
    while i < n:
        if not m[i]:
            i += 1; continue
        j = i
        while j + 1 < n and m[j + 1] and gap[j]:
            j += 1
        # exit at open of bar j+1, only if it is the contiguous next hour
        if j + 1 < n and gap[j]:
            e_px, x_px = op[i], op[j + 1]
            qty = NOTIONAL / e_px
            rows.append(C.crypto_trade(idx[i], idx[j + 1], side, e_px, x_px, qty, instrument,
                                       maker_entry=maker, maker_exit=maker))
        i = j + 1
    return pd.DataFrame(rows, columns=C.REQUIRED_TRADE_COLS + ["multiplier"])


# ---------------------------------------------------------------------------
# rule -> trades, given a frozen hour ranking (from fold 1)
# ---------------------------------------------------------------------------
def rank_hours(bars_list, start, end):
    """Mean next-open return per UTC hour, pooled across symbols, on [start,end)."""
    parts = []
    for b in bars_list:
        s = b.loc[(b.index >= start) & (b.index < end), "ro"]
        parts.append(pd.DataFrame({"ro": s.values, "h": s.index.hour}))
    d = pd.concat(parts)
    return d.groupby("h")["ro"].mean().sort_values()   # ascending: worst first


def rule_trades(p, bars, instrument, hour_rank, maker=False, shift=0):
    idx = bars.index
    if shift:   # circular clock shift used by the shuffle test
        idx = idx + pd.Timedelta(hours=int(shift))
    r = p["rule"]; d = p.get("dir", "long")
    out = []
    if r == "hours":
        k = p["k"]
        if d in ("long", "both"):
            hs = list(hour_rank.index[-k:])
            out.append(trades_from_mask(bars, pd.Series(mask_hours(idx, hs).values, index=bars.index), +1, instrument, maker))
        if d in ("short", "both"):
            hs = list(hour_rank.index[:k])
            out.append(trades_from_mask(bars, pd.Series(mask_hours(idx, hs).values, index=bars.index), -1, instrument, maker))
    else:
        side = +1 if d == "long" else -1
        if r == "weekend":
            m = mask_weekend(idx, p.get("start_h", 21), p.get("end_h", 21))
        elif r == "us_sess":
            m = mask_session(idx, p.get("h0", 13), p.get("h1", 20))
        elif r == "asia_sess":
            m = mask_session(idx, p.get("h0", 0), p.get("h1", 8))
        elif r == "fund_pre":
            m = mask_fund(idx, pre=True)
        elif r == "fund_post":
            m = mask_fund(idx, pre=False)
        else:
            raise ValueError(r)
        out.append(trades_from_mask(bars, pd.Series(m.values, index=bars.index), side, instrument, maker))
    out = [o for o in out if len(o)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS + ["multiplier"])


def make_run_fn(data: dict, hour_rank, maker=False, shift=0):
    def run_fn(p, start, end):
        parts = []
        for inst, b in data.items():
            t = rule_trades(p, b, inst, hour_rank, maker=maker, shift=shift)
            if len(t):
                t = t[(t["entry_time"] >= start) & (t["entry_time"] < end)]
                parts.append(t)
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=C.REQUIRED_TRADE_COLS + ["multiplier"])
    return run_fn


def grid():
    g = [dict(rule="hours", k=k, dir=d) for k in (1, 2, 3, 4) for d in ("long", "short", "both")]
    for r in ("weekend", "us_sess", "asia_sess", "fund_pre", "fund_post"):
        for d in ("long", "short"):
            g.append(dict(rule=r, dir=d))
    return g


def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:6.2f} net_bps={r['net_bps']:6.2f} folds={[round(f, 1) for f in r['folds']]}")


def vname(p):
    return "_".join(f"{k}={v}" for k, v in sorted(p.items()))


# ---------------------------------------------------------------------------
def main():
    yf = {"BTC": load_yf("BTC-USD"), "ETH": load_yf("ETH-USD")}
    lo = min(b.index.min() for b in yf.values()); hi = max(b.index.max() for b in yf.values())
    times = (lo, hi)
    bounds = C.fold_bounds(times, 3)
    period = (lo, hi)
    say(f"# crypto_seasonality -- results\n")
    say(f"Data: yfinance BTC-USD + ETH-USD 1h, {lo:%Y-%m-%d} -> {hi:%Y-%m-%d} ({(hi-lo).days}d). "
        f"Folds: " + ", ".join(f"F{i+1} {s:%Y-%m-%d}->{e:%Y-%m-%d}" for i, (s, e) in enumerate(bounds)))
    say(f"Execution: decide at close of bar t-1, fill at open of bar t; exit at open after last held bar; "
        f"HL taker fee both sides ({C.FEES['hl_taker']*2e4:.0f} bps RT); ${NOTIONAL:,.0f} notional/position.\n")

    # -- descriptive: mean next-open return by hour / dow per fold ---------
    say("## Descriptive: mean next-open return (bps) by UTC hour, pooled BTC+ETH, per fold")
    rows = []
    for k, (s, e) in enumerate(bounds):
        rk = rank_hours(list(yf.values()), s, e) * 1e4
        rows.append(rk.sort_index().rename(f"F{k+1}"))
    hour_tab = pd.concat(rows, axis=1).round(1)
    say("```\n" + hour_tab.T.to_string() + "\n```")
    say("Fold-to-fold rank correlation of hour means: "
        + ", ".join(f"F{i+1}vF{j+1}={hour_tab.iloc[:, i].corr(hour_tab.iloc[:, j], method='spearman'):.2f}"
                    for i, j in [(0, 1), (1, 2), (0, 2)]))
    # dow
    parts = []
    for inst, b in yf.items():
        lab = C.fold_labels(b.index.to_series(), 3, lo, hi)
        parts.append(pd.DataFrame({"ro": b["ro"].values * 1e4, "dow": b.index.dayofweek, "fold": lab}))
    d = pd.concat(parts)
    say("\nMean next-open return (bps/hour) by weekday (0=Mon), per fold:")
    say("```\n" + d.pivot_table(index="fold", columns="dow", values="ro", aggfunc="mean").round(2).to_string() + "\n```")
    # funding clock
    for inst, b in yf.items():
        h = b.index.hour
        pre = b["ro"][np.isin(h, [23, 7, 15])].mean() * 1e4
        post = b["ro"][np.isin(h, [0, 8, 16])].mean() * 1e4
        other = b["ro"][~np.isin(h, [23, 7, 15, 0, 8, 16])].mean() * 1e4
        say(f"{inst}: mean bps hour-before 00/08/16 = {pre:.2f}, hour-after = {post:.2f}, other hours = {other:.2f} "
            f"(hourly std {b['ro'].std()*1e4:.0f} bps, SE per hour-bucket ~{b['ro'].std()*1e4/np.sqrt(len(b)/24):.1f} bps)")
    say(f"Reference: round-trip taker fee = {C.FEES['hl_taker']*2e4:.0f} bps; maker = {C.FEES['hl_maker']*2e4:.0f} bps.\n")

    # -- walk-forward -----------------------------------------------------
    f1s, f1e = bounds[0]
    hour_rank = rank_hours(list(yf.values()), f1s, f1e)   # FOLD 1 ONLY, frozen
    say(f"Hour ranking fitted on fold 1 only (worst->best): {list(hour_rank.index)}\n")
    G = grid()
    run = make_run_fn(yf, hour_rank)
    best, oos, table = C.walk_forward(G, run, times, n_folds=3, select_by="net", min_trades=10)
    res = C.oos_result(oos, times, 3)
    say("## Walk-forward headline (select on F1 by net; OOS = F2+F3)")
    say(f"best_params = {best}")
    say("OOS: " + fmt(res))
    say(f"OOS folds (F2, F3) = {[round(f,2) for f in res['folds'][1:]]}, n per fold = {res['fold_n'][1:]}")

    # full-period per-cell table (folds 1..3) for transparency + lab
    say("\n## In-sample grid (fold 1 metrics) plus each cell's per-fold net over the full period")
    full_rows = []
    for i, p in enumerate(G):
        tr_all = run(p, lo, hi + pd.Timedelta("1h"))
        r_all = C.evaluate(tr_all, 3, lo, hi)
        r_is = C.evaluate(run(p, f1s, f1e), 1)
        full_rows.append(dict(idx=i, params=vname(p), is_n=r_is["n"], is_net=round(r_is["net"], 1), is_pf=round(r_is["pf"], 2),
                              is_net_bps=round(r_is["net_bps"], 2), F1=round(r_all["folds"][0], 1), F2=round(r_all["folds"][1], 1),
                              F3=round(r_all["folds"][2], 1), all_n=r_all["n"], all_pf=round(r_all["pf"], 2),
                              selected=bool(table.loc[i, "selected"])))
        C.record_to_lab(STRATEGY, f"grid_{vname(p)}", "BTC+ETH", "1h", p, r_all, period=period,
                        source=str(Path(__file__)), notes="full-period 3 folds; F1 is in-sample for 'hours' family; yf spot proxy, HL taker fees")
        C.record_to_lab(STRATEGY, f"is_f1_{vname(p)}", "BTC+ETH", "1h", p, r_is, period=(f1s, f1e),
                        source=str(Path(__file__)), notes="fold-1 in-sample selection cell")
    ft = pd.DataFrame(full_rows)
    say("```\n" + ft.to_string(index=False) + "\n```")
    C.record_to_lab(STRATEGY, "WF_headline_oos", "BTC+ETH", "1h", best, res, period=period,
                    source=str(Path(__file__)), notes="walk-forward OOS folds 2+3 (fold 1 = selection, zeroed)")

    # per-family best on F1 -> OOS
    say("\n## Per-family walk-forward (best cell of each family chosen on F1; OOS F2+F3)")
    fam_rows = []
    for fam in ("hours", "weekend", "us_sess", "asia_sess", "fund_pre", "fund_post"):
        sub = [p for p in G if p["rule"] == fam]
        b2, o2, t2 = C.walk_forward(sub, run, times, 3, min_trades=10)
        r2 = C.oos_result(o2, times, 3)
        fam_rows.append(dict(family=fam, best=vname(b2), oos_n=r2["n"], oos_net=round(r2["net"], 1), oos_pf=round(r2["pf"], 2),
                             oos_net_bps=round(r2["net_bps"], 2), F2=round(r2["folds"][1], 1), F3=round(r2["folds"][2], 1)))
        C.record_to_lab(STRATEGY, f"WF_family_{fam}", "BTC+ETH", "1h", b2, r2, period=period,
                        source=str(Path(__file__)), notes=f"family={fam} walk-forward OOS")
    say("```\n" + pd.DataFrame(fam_rows).to_string(index=False) + "\n```")

    # per-symbol OOS for headline
    say("\n## Headline rule OOS per symbol")
    for inst in yf:
        rr = C.oos_result(oos[oos["instrument"] == inst], times, 3) if len(oos) else C.empty_result()
        say(f"{inst}: " + fmt(rr))
        C.record_to_lab(STRATEGY, "WF_headline_oos", inst, "1h", best, rr, period=period, source=str(Path(__file__)))

    # maker-fee sensitivity (NOT claimed: a resting limit at next open is not verifiably filled)
    run_mk = make_run_fn(yf, hour_rank, maker=True)
    o_mk = pd.concat([run_mk(best, s, e) for (s, e) in bounds[1:]], ignore_index=True)
    r_mk = C.oos_result(o_mk, times, 3)
    say("\nMaker-both-sides sensitivity (best case, NOT verifiable fills): " + fmt(r_mk))
    C.record_to_lab(STRATEGY, "WF_headline_oos_makerfees", "BTC+ETH", "1h", best, r_mk, period=period,
                    source=str(Path(__file__)), notes="UNVERIFIABLE maker fills; sensitivity only")
    # gross (zero-fee) OOS
    o_g = oos.copy(); o_g["fee_usd"] = 0.0
    r_g = C.oos_result(o_g, times, 3)
    say("Zero-fee OOS (gross signal only): " + fmt(r_g))

    # -- sanity (a): shuffle = random circular clock shift of the best rule --
    say("\n## Sanity (a): shuffle test -- random circular shift of the clock (1..167h), 300 draws, OOS net")
    nulls = []
    for _ in range(300):
        sh = int(RNG.integers(1, 168))
        rf = make_run_fn(yf, hour_rank, shift=sh)
        o = pd.concat([rf(best, s, e) for (s, e) in bounds[1:]], ignore_index=True)
        nulls.append(C.oos_result(o, times, 3)["net"] if len(o) else 0.0)
    nulls = np.array(nulls)
    pct = float((nulls < res["net"]).mean())
    say(f"actual OOS net = {res['net']:.1f}; null mean = {nulls.mean():.1f}, sd = {nulls.std():.1f}, "
        f"5/50/95 pct = {np.percentile(nulls,5):.1f}/{np.percentile(nulls,50):.1f}/{np.percentile(nulls,95):.1f}; "
        f"actual percentile in null = {pct:.3f}")
    C.record_to_lab(STRATEGY, "sanity_shuffle_null", "BTC+ETH", "1h", dict(best=best, draws=300),
                    dict(C.empty_result(), n=300, net=float(nulls.mean()), wr=float((nulls > 0).mean()),
                         folds=[0.0, float(np.percentile(nulls, 5)), float(np.percentile(nulls, 95))]),
                    period=period, source=str(Path(__file__)), trust="synthetic",
                    notes=f"null distribution of OOS net under random clock shift; actual={res['net']:.1f} pct={pct:.3f}")

    # -- sanity (c): neighbouring parameters ------------------------------
    say("\n## Sanity (c): neighbouring parameters of the selected rule (OOS F2+F3)")
    neigh = []
    if best["rule"] == "hours":
        for k in (best["k"] - 1, best["k"] + 1):
            if 1 <= k <= 6:
                neigh.append(dict(best, k=k))
        for d in ("long", "short", "both"):
            if d != best["dir"]:
                neigh.append(dict(best, dir=d))
    elif best["rule"] == "weekend":
        for a, b in [(19, 21), (23, 21), (21, 19), (21, 23), (20, 20), (22, 22)]:
            neigh.append(dict(best, start_h=a, end_h=b))
    elif best["rule"] in ("us_sess", "asia_sess"):
        h0, h1 = (13, 20) if best["rule"] == "us_sess" else (0, 8)
        for a, b in [(h0 - 1, h1), (h0 + 1, h1), (h0, h1 - 1), (h0, h1 + 1)]:
            neigh.append(dict(best, h0=a, h1=b))
    else:
        neigh.append(dict(best, rule="fund_pre" if best["rule"] == "fund_post" else "fund_post"))
    nrows = []
    for p in neigh:
        o = pd.concat([run(p, s, e) for (s, e) in bounds[1:]], ignore_index=True)
        r = C.oos_result(o, times, 3)
        nrows.append(dict(params=vname(p), oos_n=r["n"], oos_net=round(r["net"], 1), oos_pf=round(r["pf"], 2),
                          F2=round(r["folds"][1], 1), F3=round(r["folds"][2], 1)))
        C.record_to_lab(STRATEGY, f"neighbor_{vname(p)}", "BTC+ETH", "1h", p, r, period=period,
                        source=str(Path(__file__)), notes="neighbour of WF-selected params, OOS F2+F3")
    ntab = pd.DataFrame(nrows)
    say("```\n" + ntab.to_string(index=False) + "\n```")
    neigh_ok = bool(len(ntab) and (ntab["oos_net"] > 0).mean() >= 0.5)

    # -- sanity (d): Hyperliquid universe, per coin, liquidity split ------
    say("\n## Sanity (d): Hyperliquid 1h universe (208d, fully inside yf fold 3 => OOS for the F1-selected rule)")
    uni = C.hl_universe().set_index("coin")
    crow = []
    for coin in C.list_hl_coins():
        try:
            b = load_hl(coin)
        except Exception as ex:
            continue
        if len(b) < 24 * 30:
            continue
        t = rule_trades(best, b, coin, hour_rank)
        r = C.evaluate(t, 3)
        vol = float(uni.loc[coin, "dayNtlVlm"]) if coin in uni.index else np.nan
        crow.append(dict(coin=coin, dayNtlVlm_m=round(vol / 1e6, 1), n=r["n"], net=round(r["net"], 1), pf=round(r["pf"], 2),
                         net_bps=round(r["net_bps"], 2), folds=[round(f, 0) for f in r["folds"]]))
        C.record_to_lab(STRATEGY, "HL_universe_F1rule", coin, "1h", best, r, period=(b.index.min(), b.index.max()),
                        source=str(Path(__file__)), notes=f"yf-F1-selected rule applied to HL {coin}; dayNtlVlm={vol:.0f}")
    ct = pd.DataFrame(crow).sort_values("dayNtlVlm_m", ascending=False)
    say("```\n" + ct.to_string(index=False) + "\n```")
    liq = ct[ct["dayNtlVlm_m"] >= 5]; ill = ct[ct["dayNtlVlm_m"] < 5]
    say(f"liquid (>=$5M/d): {len(liq)} coins, {int((liq['net']>0).sum())} positive, sum net={liq['net'].sum():.0f}, median net_bps={liq['net_bps'].median():.2f}")
    say(f"illiquid (<$5M/d): {len(ill)} coins, {int((ill['net']>0).sum())} positive, sum net={ill['net'].sum():.0f}, median net_bps={ill['net_bps'].median():.2f}")
    majors = ct[ct["coin"].isin(["BTC", "ETH", "SOL"])]
    say("HL majors: " + "; ".join(f"{r.coin} n={r.n} net={r.net} pf={r.pf}" for r in majors.itertuples()))

    # -- independent walk-forward on HL BTC/ETH/SOL (own fold-1 ranking) ----
    say("\n## Secondary: independent walk-forward on HL BTC+ETH+SOL 1h (208d; own fold-1 hour ranking)")
    hl = {c: load_hl(c) for c in ("BTC", "ETH", "SOL")}
    hlo = min(b.index.min() for b in hl.values()); hhi = max(b.index.max() for b in hl.values())
    hb = C.fold_bounds((hlo, hhi), 3)
    hl_rank = rank_hours(list(hl.values()), hb[0][0], hb[0][1])
    run_hl = make_run_fn(hl, hl_rank)
    b_hl, o_hl, t_hl = C.walk_forward(G, run_hl, (hlo, hhi), 3, min_trades=10)
    r_hl = C.oos_result(o_hl, (hlo, hhi), 3)
    say(f"best_params = {b_hl}; OOS: " + fmt(r_hl))
    say(f"HL fold-1 hour ranking (worst->best): {list(hl_rank.index)}; Spearman vs yf-F1 ranking = "
        f"{pd.Series(range(24), index=hl_rank.index).reindex(range(24)).corr(pd.Series(range(24), index=hour_rank.index).reindex(range(24)), method='spearman'):.2f}")
    C.record_to_lab(STRATEGY, "WF_HL_secondary_oos", "BTC+ETH+SOL", "1h", b_hl, r_hl, period=(hlo, hhi),
                    source=str(Path(__file__)), notes="independent walk-forward on HL candles, OOS F2+F3")
    for i, p in enumerate(G):
        r_c = C.evaluate(run_hl(p, hlo, hhi + pd.Timedelta("1h")), 3, hlo, hhi)
        C.record_to_lab(STRATEGY, f"HLgrid_{vname(p)}", "BTC+ETH+SOL", "1h", p, r_c, period=(hlo, hhi),
                        source=str(Path(__file__)), notes="HL full-period 3 folds per cell")

    # -- verdict ----------------------------------------------------------
    oos_folds = res["folds"][1:]
    crit = dict(net_pos=res["net"] > 0, pf=res["pf"] >= 1.2, n=res["n"] >= 60,
                folds=all(f > 0 for f in oos_folds), shuffle=pct >= 0.95, neighbors=neigh_ok)
    if all(crit.values()):
        verdict = "edge"
    elif res["net"] > 0:
        verdict = "weak"
    else:
        verdict = "none"
    say("\n## Verdict")
    say(f"criteria = {crit}")
    say(f"**{verdict}**")
    summary = dict(key="crypto_seasonality", best_params=best, oos_n=res["n"], oos_net=round(res["net"], 2),
                   oos_pf=round(res["pf"], 3), oos_wr=round(res["wr"], 3), oos_sharpe=round(res["sharpe"], 3),
                   oos_folds=[round(f, 2) for f in oos_folds], insample_best_net=float(table.loc[table.selected, "is_net"].iloc[0]),
                   shuffle_pct=pct, neighbors_ok=neigh_ok, verdict=verdict, criteria=crit,
                   zero_fee_oos_net=round(r_g["net"], 2), maker_oos_net=round(r_mk["net"], 2),
                   hl_secondary=dict(best=b_hl, oos_n=r_hl["n"], oos_net=round(r_hl["net"], 2), oos_pf=round(r_hl["pf"], 3)),
                   liquid=dict(n=len(liq), pos=int((liq['net'] > 0).sum()), net=float(liq['net'].sum())),
                   illiquid=dict(n=len(ill), pos=int((ill['net'] > 0).sum()), net=float(ill['net'].sum())),
                   families=fam_rows)
    Path(__file__).with_suffix(".json").write_text(json.dumps(summary, default=str, indent=1))
    OUT_MD.write_text("\n".join(LINES) + "\n")
    print("SUMMARY_JSON", json.dumps(summary, default=str))


if __name__ == "__main__":
    main()
