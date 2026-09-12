"""Hypothesis btc_alt_leadlag (round 1).

BTC leads alts: after BTC moves more than X% over the last K bars (5m / 15m),
buy (short) the alts that have NOT yet responded (lowest beta-adjusted response
in BTC's direction), hold H bars. Taker fees both sides (momentum entry).

Causality: signal computed from bar t close. Entry at bar t+1 OPEN. Exit at bar
t+1+H OPEN (i.e. hold exactly H full bars). Betas are estimated from a trailing
window ending at bar t-K (strictly before the signal window). Nothing from
bar t+1 or later is used to form the signal.

Usage: venv/bin/python tests/h_btc_alt_leadlag.py
"""
import sys, json, itertools, warnings
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
STRAT = "btc_alt_leadlag"
NOTIONAL = 1000.0        # USD per alt leg
N_PICK = 5               # number of laggard alts per signal
BETA_BARS = {"5m": 576, "15m": 192}   # trailing bars for beta (~2 days)
ILLIQ_USD = 5e6
RNG = np.random.default_rng(7)


# ---------------------------------------------------------------------------
# data panel
# ---------------------------------------------------------------------------
def load_panel(interval):
    coins = C.list_hl_coins()
    closes, opens = {}, {}
    for c in coins:
        try:
            b = C.hl_candles(c, interval)
        except Exception:
            continue
        b = b[~b.index.duplicated()]
        closes[c] = b["close"]
        opens[c] = b["open"]
    close = pd.DataFrame(closes).sort_index()
    open_ = pd.DataFrame(opens).sort_index()
    # keep only the regular grid rows that BTC has (BTC is the reference clock)
    close = close[close["BTC"].notna()]
    open_ = open_.reindex(close.index)
    return close, open_


PANELS = {}


def panel(interval):
    if interval not in PANELS:
        PANELS[interval] = load_panel(interval)
    return PANELS[interval]


def rolling_beta(close, K, win):
    """beta of each alt's K-bar return on BTC's K-bar return, trailing `win` bars,
    shifted by K so the beta window ends BEFORE the signal window."""
    r = close.pct_change(K)
    rb = r["BTC"]
    cov = r.rolling(win).cov(rb)
    var = rb.rolling(win).var()
    beta = cov.div(var, axis=0)
    return beta.shift(K).clip(-3, 5)


BETA_CACHE = {}


def get_beta(interval, K):
    key = (interval, K)
    if key not in BETA_CACHE:
        close, _ = panel(interval)
        BETA_CACHE[key] = rolling_beta(close, K, BETA_BARS[interval])
    return BETA_CACHE[key]


# ---------------------------------------------------------------------------
# strategy
# ---------------------------------------------------------------------------
TRADE_CACHE = {}


def build_trades(interval, X, K, H, select="lag", n_pick=N_PICK, time_shuffle=False,
                 coin_shuffle=False, start=None, end=None):
    """Deterministic (non-shuffled) variants are built ONCE over the whole
    period (so the per-coin no-overlap filter does not reset at fold edges) and
    then filtered to entry_time in [start, end). Shuffled variants are built
    directly inside the window."""
    if time_shuffle or coin_shuffle:
        return _build_trades(interval, X, K, H, select, n_pick, time_shuffle, coin_shuffle, start, end)
    key = (interval, X, K, H, select, n_pick)
    if key not in TRADE_CACHE:
        TRADE_CACHE[key] = _build_trades(interval, X, K, H, select, n_pick)
    tr = TRADE_CACHE[key]
    if start is None or len(tr) == 0:
        return tr.copy()
    s, e = C._utc(start), C._utc(end)
    return tr[(tr["entry_time"] >= s) & (tr["entry_time"] < e)].reset_index(drop=True)


def _build_trades(interval, X, K, H, select="lag", n_pick=N_PICK, time_shuffle=False,
                  coin_shuffle=False, start=None, end=None):
    """Return trades DataFrame (common.evaluate format).

    select: 'lag'  -> n_pick alts with LOWEST beta-adjusted response (hypothesis)
            'lead' -> n_pick alts with HIGHEST response (anti-hypothesis)
            'all'  -> every alt (pure BTC-spillover baseline)
    time_shuffle: keep (coin, side) of each real signal but move it to a random bar
    coin_shuffle: keep real signal bars/sides but pick random alts
    """
    close, open_ = panel(interval)
    beta = get_beta(interval, K)
    idx = close.index
    alts = [c for c in close.columns if c != "BTC"]
    rb = close["BTC"].pct_change(K)
    ra = close[alts].pct_change(K)
    thr = X / 100.0
    fresh = (rb.abs() > thr) & (rb.abs().shift(1) <= thr)     # first breach only
    sig_pos = np.where(fresh.values)[0]
    # need t+1 (entry) and t+1+H (exit) to exist
    sig_pos = sig_pos[(sig_pos + 1 + H) < len(idx)]
    if start is not None:
        s, e = C._utc(start), C._utc(end)
        ent = idx[np.minimum(sig_pos + 1, len(idx) - 1)]
        sig_pos = sig_pos[(ent >= s) & (ent < e)]
    if time_shuffle and len(sig_pos):
        # choose random signal bars (same count) uniformly inside the same window
        lo = idx.searchsorted(C._utc(start)) if start is not None else 0
        hi = idx.searchsorted(C._utc(end)) if end is not None else len(idx)
        cand = np.arange(max(lo, 1), min(hi, len(idx) - H - 1))
        rnd_pos = RNG.choice(cand, size=len(sig_pos), replace=False)
    rows = []
    for j, t in enumerate(sig_pos):
        side = 1 if rb.iat[t] > 0 else -1
        resp = (ra.iloc[t] * side) - beta.iloc[t][alts] * abs(rb.iat[t])   # residual in BTC direction
        resp = resp.dropna()
        if len(resp) < n_pick:
            continue
        if coin_shuffle:
            picks = list(RNG.choice(resp.index.values, size=n_pick, replace=False))
        elif select == "lag":
            picks = list(resp.nsmallest(n_pick).index)
        elif select == "lead":
            picks = list(resp.nlargest(n_pick).index)
        else:
            picks = list(resp.index)
        tt = rnd_pos[j] if time_shuffle else t
        et, xt = idx[tt + 1], idx[tt + 1 + H]
        for coin in picks:
            ep, xp = open_.at[et, coin], open_.at[xt, coin]
            if not (np.isfinite(ep) and np.isfinite(xp)) or ep <= 0:
                continue
            qty = NOTIONAL / ep
            rows.append(C.crypto_trade(et, xt, side, ep, xp, qty, coin,
                                       maker_entry=False, maker_exit=False))
    if not rows:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    tr = pd.DataFrame(rows)
    # per-coin no-overlap: drop a trade if the same coin is still held
    tr = tr.sort_values(["entry_time", "instrument"]).reset_index(drop=True)
    keep, last_exit = [], {}
    for i, r in tr.iterrows():
        if r["entry_time"] < last_exit.get(r["instrument"], pd.Timestamp.min.tz_localize("UTC")):
            keep.append(False)
            continue
        keep.append(True)
        last_exit[r["instrument"]] = r["exit_time"]
    return tr[np.array(keep)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def fmt(r):
    return (f"n={r['n']:4d} net={r['net']:8.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} bps={r['net_bps']:.1f} folds={[round(f, 1) for f in r['folds']]}")


def main():
    grid = [dict(X=X, K=K, H=H) for X, K, H in itertools.product([0.3, 0.5, 1.0], [3, 6], [3, 6, 12])]
    uni = C.hl_universe().set_index("coin")["dayNtlVlm"]
    md = ["# btc_alt_leadlag - round 1 results", "",
          f"Notional ${NOTIONAL:.0f}/leg, {N_PICK} laggard alts per signal, taker fees both sides "
          f"({C.FEES['hl_taker']*2*1e4:.0f} bps round trip). Entry next-bar open, exit H bars later at open. "
          "Fresh-breach signal only (|BTC K-bar ret| crosses X). Per-coin no overlap.", ""]
    out = {}
    for interval in ["15m", "5m"]:
        close, _ = panel(interval)
        times = (close.index[0], close.index[-1])
        bounds = C.fold_bounds(times, 3)
        print(f"\n===== {interval}: {times[0]} -> {times[1]} ({len(close)} bars, {close.shape[1]-1} alts) =====")
        md.append(f"## {interval}  ({times[0]:%Y-%m-%d} -> {times[1]:%Y-%m-%d}, {len(close)} bars)")
        md.append("")
        md.append("Folds: " + ", ".join(f"F{i+1} {s:%m-%d}->{e:%m-%d}" for i, (s, e) in enumerate(bounds)))
        md.append("")

        def run_fn(p, s, e):
            return build_trades(interval, p["X"], p["K"], p["H"], start=s, end=e)

        best, oos_tr, table = C.walk_forward(grid, run_fn, times, n_folds=3, min_trades=10)
        oos = C.oos_result(oos_tr, times, 3)
        # full-period grid (all folds) for sensitivity / neighbours
        full = []
        for i, p in enumerate(grid):
            tr = build_trades(interval, p["X"], p["K"], p["H"])
            r = C.evaluate(tr, 3, start=times[0], end=times[1])
            full.append(dict(idx=i, **p, n=r["n"], net=r["net"], pf=r["pf"], wr=r["wr"],
                             f1=r["folds"][0], f2=r["folds"][1], f3=r["folds"][2],
                             oos23=r["folds"][1] + r["folds"][2], bps=r["net_bps"]))
            C.record_to_lab(STRAT, f"grid_X{p['X']}_K{p['K']}_H{p['H']}", f"HL_alts_{N_PICK}lag", interval,
                            p, r, period=times, source=__file__,
                            notes=f"full-period grid cell (all 3 folds; fold1 = selection fold)")
        full = pd.DataFrame(full)
        full["selected"] = full["idx"] == grid.index(best)
        print("\n-- in-sample (fold 1) grid --")
        print(table.to_string(index=False))
        print("\n-- full-period grid (F1 is in-sample, F2+F3 is OOS for the selected row) --")
        print(full.to_string(index=False))
        print(f"\nSELECTED on fold 1: {best}")
        print("WALK-FORWARD OOS (folds 2+3):", fmt(oos))
        C.record_to_lab(STRAT, "walkforward_oos", f"HL_alts_{N_PICK}lag", interval, best, oos,
                        period=times, source=__file__,
                        notes=f"HEADLINE: params chosen on fold1, OOS = folds 2+3. fold1 entry is 0 by construction")

        # ---- sanity: decomposition (lead / all) on selected params, OOS window ----
        s2, e3 = bounds[1][0], bounds[2][1]
        decomp = {}
        for sel in ["lag", "lead", "all"]:
            tr = build_trades(interval, best["X"], best["K"], best["H"], select=sel, start=s2, end=e3)
            r = C.evaluate(tr, 3, start=times[0], end=times[1])
            decomp[sel] = r
            C.record_to_lab(STRAT, f"oos_select_{sel}", f"HL_alts_{sel}", interval, best, r, period=times,
                            source=__file__, notes="OOS window (folds 2+3) with selection rule swapped")
            print(f"  select={sel:4s}: {fmt(r)}")

        # ---- sanity: shuffles ----
        n_perm = 100
        time_nets, coin_nets = [], []
        for _ in range(n_perm):
            tr = build_trades(interval, best["X"], best["K"], best["H"], time_shuffle=True, start=s2, end=e3)
            time_nets.append(C.evaluate(tr)["net"])
            tr = build_trades(interval, best["X"], best["K"], best["H"], coin_shuffle=True, start=s2, end=e3)
            coin_nets.append(C.evaluate(tr)["net"])
        time_nets, coin_nets = np.array(time_nets), np.array(coin_nets)
        p_time = float((time_nets >= oos["net"]).mean())
        p_coin = float((coin_nets >= oos["net"]).mean())
        print(f"  time-shuffle: mean={time_nets.mean():.2f} sd={time_nets.std():.2f} p(>=real)={p_time:.2f}")
        print(f"  coin-shuffle: mean={coin_nets.mean():.2f} sd={coin_nets.std():.2f} p(>=real)={p_coin:.2f}")
        C.record_to_lab(STRAT, "shuffle_time_mean", f"HL_alts_{N_PICK}rand", interval, best,
                        dict(C.empty_result(), n=int(oos["n"]), net=float(time_nets.mean())),
                        period=times, source=__file__, trust="synthetic",
                        notes=f"mean of {n_perm} time-shuffled OOS nets; sd={time_nets.std():.2f}; p={p_time:.2f}")
        C.record_to_lab(STRAT, "shuffle_coin_mean", f"HL_alts_{N_PICK}rand", interval, best,
                        dict(C.empty_result(), n=int(oos["n"]), net=float(coin_nets.mean())),
                        period=times, source=__file__, trust="synthetic",
                        notes=f"mean of {n_perm} coin-shuffled OOS nets; sd={coin_nets.std():.2f}; p={p_coin:.2f}")

        # ---- sanity: neighbours ----
        def is_nb(row):
            d = sum(int(row[k] != best[k]) for k in ("X", "K", "H"))
            return d == 1
        nb = full[full.apply(is_nb, axis=1)]
        print("  neighbours (one-step) OOS23:", nb[["X", "K", "H", "n", "oos23", "pf"]].to_string(index=False))
        nb_pos = int((nb["oos23"] > 0).sum())

        # ---- per-coin OOS ----
        pc = pd.DataFrame()
        if len(oos_tr):
            t = C.add_pnl(oos_tr)
            pc = t.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"),
                                              wr=("net_pnl", lambda x: (x > 0).mean()))
            pc["vol24h_usd"] = uni.reindex(pc.index).values
            pc["illiquid"] = pc["vol24h_usd"] < ILLIQ_USD
            pc = pc.sort_values("net", ascending=False)
            ill_net = float(pc.loc[pc["illiquid"], "net"].sum())
            liq_net = float(pc.loc[~pc["illiquid"], "net"].sum())
            print(pc.to_string())
            print(f"  illiquid (<$5M) net={ill_net:.2f}  liquid net={liq_net:.2f}")
        else:
            ill_net = liq_net = 0.0

        # ---- side breakdown ----
        if len(oos_tr):
            t = C.add_pnl(oos_tr)
            sb = t.groupby("side")["net_pnl"].agg(["size", "sum"])
            print("  by side:", sb.to_dict())

        out[interval] = dict(best=best, oos=oos, oos_tr=oos_tr, table=table, full=full, decomp=decomp,
                             p_time=p_time, p_coin=p_coin, time_mean=float(time_nets.mean()),
                             coin_mean=float(coin_nets.mean()), nb=nb, nb_pos=nb_pos, pc=pc,
                             ill_net=ill_net, liq_net=liq_net, times=times)

        # ---- markdown ----
        md.append(f"**Selected on fold 1:** `{best}`  ")
        md.append(f"**Walk-forward OOS (folds 2+3):** n={oos['n']} net=${oos['net']:.2f} pf={oos['pf']:.2f} "
                  f"wr={oos['wr']:.2f} sharpe={oos['sharpe']:.2f} net_bps={oos['net_bps']:.1f} "
                  f"folds=[F2 {oos['folds'][1]:.2f}, F3 {oos['folds'][2]:.2f}] max_dd={oos['max_dd']:.2f}")
        md.append("")
        md.append("### Full grid (F1 = selection / in-sample, F2+F3 = out-of-sample)")
        md.append("")
        md.append("| X% | K | H | n | net | pf | wr | F1 | F2 | F3 | OOS23 | bps | sel |")
        md.append("|---:|--:|--:|--:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|")
        for _, r in full.iterrows():
            md.append(f"| {r.X} | {r.K} | {r.H} | {int(r.n)} | {r.net:.1f} | {r.pf:.2f} | {r.wr:.2f} | {r.f1:.1f} | "
                      f"{r.f2:.1f} | {r.f3:.1f} | {r.oos23:.1f} | {r.bps:.1f} | {'*' if r.selected else ''} |")
        md.append("")
        md.append("### Sanity checks (OOS window, selected params)")
        md.append("")
        for sel, r in decomp.items():
            md.append(f"- select={sel}: n={r['n']} net={r['net']:.2f} pf={r['pf']:.2f} wr={r['wr']:.2f}")
        md.append(f"- time-shuffle ({n_perm}x): mean={time_nets.mean():.2f} sd={time_nets.std():.2f} "
                  f"p(shuffled >= real)={p_time:.2f}")
        md.append(f"- coin-shuffle ({n_perm}x): mean={coin_nets.mean():.2f} sd={coin_nets.std():.2f} "
                  f"p(shuffled >= real)={p_coin:.2f}")
        md.append(f"- neighbours with OOS23 > 0: {nb_pos}/{len(nb)}")
        md.append(f"- illiquid (<$5M/24h) OOS net={ill_net:.2f}; liquid OOS net={liq_net:.2f}")
        md.append("")
        if len(pc):
            md.append("### Per-coin OOS (selected params)")
            md.append("")
            md.append("| coin | n | net | wr | 24h vol $M | illiquid |")
            md.append("|---|--:|---:|---:|---:|:--:|")
            for coin, r in pc.iterrows():
                md.append(f"| {coin} | {int(r.n)} | {r.net:.2f} | {r.wr:.2f} | {r.vol24h_usd/1e6:.1f} | "
                          f"{'Y' if r.illiquid else ''} |")
            md.append("")
    return out, md


if __name__ == "__main__":
    out, md = main()
    (HERE / "h_btc_alt_leadlag.md").write_text("\n".join(md))
    print("\nwrote", HERE / "h_btc_alt_leadlag.md")
    summary = {k: dict(best=v["best"], oos_n=v["oos"]["n"], oos_net=v["oos"]["net"], oos_pf=v["oos"]["pf"],
                       oos_folds=v["oos"]["folds"], p_time=v["p_time"], p_coin=v["p_coin"],
                       nb_pos=v["nb_pos"], nb_total=len(v["nb"])) for k, v in out.items()}
    print(json.dumps(summary, indent=1, default=str))
