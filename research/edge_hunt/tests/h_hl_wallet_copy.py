"""h_hl_wallet_copy: do informed Hyperliquid wallets persist, and can their entries be copied net of fees?

Data: full public fill histories (userFillsByTime) for a 550-wallet panel drawn from the public
leaderboard (top 300 by 30d PnL with >=$100k 30d volume, bottom 100, 150 random active), cached under
data/hl_wallets/fills/.  Only native perps (no spot '@', no HIP-3 'xyz:' builder markets).

Part A - persistence: monthly wallet panel; trailing 30d/90d net realized PnL, Sharpe, PnL/volume rank
         -> next-30d net realized PnL / Sharpe.  Spearman per month + decile spreads.
Part B - copy strategy: mirror fresh position openings (flat -> non-flat) of trailing-top-decile wallets
         with delay D, exit when the wallet is flat again (or after H hours), $1k/trade, taker fees.
         Execution price = first REAL fill on the tape (all panel fills in that coin) on our side at or
         after t+D; fallback next 1h candle open.  Inverse (fade bottom decile) too.  Monthly folds,
         walk-forward selection on early months only.
"""
from __future__ import annotations
import glob, json, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C

WD = ROOT / "data" / "hl_wallets"
TAKER = C.FEES["hl_taker"]
SIZE = 1000.0
import os
MIN_WALLETS = int(os.environ.get("HLC_MIN_WALLETS", "20"))
# leaderboard snapshot date: 'top'/'bottom' groups were selected on PnL over [SNAP-30d, SNAP] -> that
# window is look-ahead contaminated for those groups.
SNAP = pd.Timestamp("2026-08-28", tz="UTC")
CONTAM_START = SNAP - pd.Timedelta(days=30)


def is_native_perp(coin: str) -> bool:
    return not (coin.startswith("@") or ":" in coin)


def load_panel():
    panel = pd.read_parquet(WD / "panel.parquet").set_index("addr")
    fills = {}
    for f in glob.glob(str(WD / "fills" / "*.parquet")):
        addr = Path(f).stem
        df = pd.read_parquet(f)
        if len(df) == 0:
            continue
        df = df[df.coin.map(is_native_perp) & ~df.dir.isin(["Buy", "Sell", "Settlement"])].copy()
        if len(df) == 0:
            continue
        df = df[df.feeToken == "USDC"]
        df["notional"] = df.px * df.sz
        df["net"] = df.closedPnl - df.fee
        # signed position after the fill
        sgn = np.where(df.side == "B", 1.0, -1.0)
        df["pos_after"] = df.startPosition + sgn * df.sz
        df["sgn"] = sgn
        fills[addr] = df.sort_values("time").reset_index(drop=True)
    return panel, fills


# ----------------------------------------------------------------------------- Part A
def wallet_daily(fills):
    """addr -> DataFrame(day, net, notional, nfills)"""
    out = {}
    for a, df in fills.items():
        d = df.assign(day=df.time.dt.floor("D")).groupby("day").agg(net=("net", "sum"), notional=("notional", "sum"), n=("net", "size"))
        out[a] = d
    return out


def window_stats(d: pd.DataFrame, s, e):
    w = d[(d.index >= s) & (d.index < e)]
    if len(w) == 0:
        return dict(pnl=0.0, vol=0.0, n=0, sharpe=np.nan, roi=np.nan, days=0)
    days = int((e - s).days)
    full = w.net.reindex(pd.date_range(s, e - pd.Timedelta(days=1), freq="D", tz="UTC"), fill_value=0.0)
    sd = full.std(ddof=1)
    sharpe = full.mean() / sd * np.sqrt(365) if sd > 0 else np.nan
    return dict(pnl=float(w.net.sum()), vol=float(w.notional.sum()), n=int(w.n.sum()), sharpe=float(sharpe),
                roi=float(w.net.sum() / w.notional.sum() * 1e4) if w.notional.sum() > 0 else np.nan, days=int((w.n > 0).sum()))


def build_month_panel(daily, panel, months, min_fills=10, min_vol=1e5):
    rows = []
    for m in months:
        for a, d in daily.items():
            t30 = window_stats(d, m - pd.Timedelta(days=30), m)
            if t30["n"] < min_fills or t30["vol"] < min_vol:
                continue
            t90 = window_stats(d, m - pd.Timedelta(days=90), m)
            nx = window_stats(d, m, m + pd.Timedelta(days=30))
            rows.append(dict(month=m, addr=a, group=panel.group.get(a, "?"),
                             t30_pnl=t30["pnl"], t30_sharpe=t30["sharpe"], t30_roi=t30["roi"], t30_vol=t30["vol"], t30_n=t30["n"],
                             t90_pnl=t90["pnl"], t90_sharpe=t90["sharpe"], t90_roi=t90["roi"], t90_vol=t90["vol"],
                             nx_pnl=nx["pnl"], nx_sharpe=nx["sharpe"], nx_roi=nx["roi"], nx_vol=nx["vol"], nx_n=nx["n"]))
    return pd.DataFrame(rows)


def persistence_table(mp: pd.DataFrame, feats, targets):
    rows = []
    for f in feats:
        for tg in targets:
            per = []
            for m, g in mp.groupby("month"):
                g = g.dropna(subset=[f, tg])
                if len(g) < 20:
                    continue
                rho = stats.spearmanr(g[f], g[tg]).statistic
                q = pd.qcut(g[f].rank(method="first"), 10, labels=False)
                top, bot = g[tg][q == 9].mean(), g[tg][q == 0].mean()
                per.append(dict(month=m, n=len(g), rho=rho, top=top, bot=bot, spread=top - bot,
                                top_pos=(g[tg][q == 9] > 0).mean()))
            p = pd.DataFrame(per)
            if len(p) == 0:
                continue
            t = stats.ttest_1samp(p.rho, 0) if len(p) > 2 else None
            rows.append(dict(feature=f, target=tg, months=len(p), wallet_months=int(p.n.sum()), mean_rho=p.rho.mean(),
                             rho_t=t.statistic if t else np.nan, rho_pos_frac=(p.rho > 0).mean(),
                             mean_top=p.top.mean(), mean_bot=p.bot.mean(), mean_spread=p.spread.mean(),
                             spread_pos_frac=(p.spread > 0).mean(), top_winrate=p.top_pos.mean()))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- tape + candles
class Tape:
    """All panel fills per coin = real trade prints. price(coin, T, side): first print with the given
    side ('B' buy = we lift the ask; 'A' = we hit the bid) at time >= T within `within` minutes; else
    any side within `within`; else next 1h candle open (causal); else NaN."""
    def __init__(self, fills, within_min=15):
        allf = pd.concat([df[["time", "coin", "side", "px", "crossed"]] for df in fills.values()], ignore_index=True)
        allf = allf.sort_values("time")
        self.within = np.timedelta64(within_min, "m")
        self.tp = {}
        for c, g in allf.groupby("coin"):
            t = g.time.values.astype("datetime64[ns]"); px = g.px.values; sd = g.side.values; cr = g.crossed.values.astype(bool)
            self.tp[c] = dict(all=(t, px))
            for s_ in ("B", "A"):
                m1 = (sd == s_) & cr; m2 = (sd == s_)
                self.tp[c][s_ + "T"] = (t[m1], px[m1])   # taker prints on our side (what a taker actually paid)
                self.tp[c][s_] = (t[m2], px[m2])
        self.candles = {}
        self.stats = dict(tape=0, side=0, any=0, candle=0, miss=0)

    def density(self):
        return {c: len(v["all"][0]) for c, v in self.tp.items()}

    def _cand(self, coin):
        if coin not in self.candles:
            try:
                self.candles[coin] = C.hl_candles(coin, "1h")
            except FileNotFoundError:
                self.candles[coin] = None
        return self.candles[coin]

    def price(self, coin, T, side):
        T = np.datetime64(pd.Timestamp(T).tz_convert("UTC").tz_localize(None), "ns")
        tp = self.tp.get(coin)
        if tp is not None:
            for key, tag in ((side + "T", "tape"), (side, "side"), ("all", "any")):
                t, px = tp[key]
                i = np.searchsorted(t, T)
                if i < len(t) and t[i] - T <= self.within:
                    self.stats[tag] += 1
                    return float(px[i]), pd.Timestamp(t[i], tz="UTC"), tag
        cd = self._cand(coin)
        if cd is not None:
            i = cd.index.searchsorted(pd.Timestamp(T, tz="UTC"), side="right")
            if i < len(cd):
                self.stats["candle"] += 1
                return float(cd["open"].iloc[i]), cd.index[i], "candle"
        self.stats["miss"] += 1
        return np.nan, pd.NaT, "miss"


# ----------------------------------------------------------------------------- Part B
def episodes(df: pd.DataFrame, min_notional=0.0):
    """Fresh position episodes per coin: open when pos goes 0 -> non-zero (or flips), close when pos returns
    to 0 (or flips). Returns DataFrame(coin, t_open, side, t_close, open_notional)."""
    out = []
    for c, g in df.groupby("coin", sort=False):
        g = g.sort_values("time")
        open_t, open_side, open_ntl = None, 0, 0.0
        for t, sp, pa, ntl in zip(g.time.values, g.startPosition.values, g.pos_after.values, g.notional.values):
            s_before = int(np.sign(round(sp, 10))); s_after = int(np.sign(round(pa, 10)))
            if open_t is not None and s_after != open_side:      # closed or flipped
                out.append((c, open_t, open_side, t, open_ntl)); open_t = None
            if open_t is None and s_after != 0 and s_before != s_after:
                open_t, open_side, open_ntl = t, s_after, ntl
        if open_t is not None:
            out.append((c, open_t, open_side, pd.NaT, open_ntl))
    e = pd.DataFrame(out, columns=["coin", "t_open", "side", "t_close", "open_notional"])
    e["t_open"] = pd.to_datetime(e.t_open, utc=True); e["t_close"] = pd.to_datetime(e.t_close, utc=True)
    return e[e.open_notional >= min_notional]


def copy_trades(ep: pd.DataFrame, tape: Tape, delay_min: float, hold_h: float, mode: str, sign: int = 1):
    """mode 'mirror' = exit when the wallet exits (cap hold_h); 'fixed' = exit after hold_h regardless.
    sign=-1 fades (opposite side)."""
    rows = []
    D = pd.Timedelta(minutes=delay_min)
    for r in ep.itertuples(index=False):
        side = r.side * sign
        t_in = r.t_open + D
        px_in, f_in, tag_in = tape.price(r.coin, t_in, "B" if side > 0 else "A")
        if not np.isfinite(px_in):
            continue
        t_cap = r.t_open + pd.Timedelta(hours=hold_h)
        if mode == "mirror" and pd.notna(r.t_close) and r.t_close + D < t_cap:
            t_out = r.t_close + D
        else:
            t_out = t_cap
        if t_out <= f_in:
            t_out = f_in + pd.Timedelta(seconds=1)
        px_out, f_out, tag_out = tape.price(r.coin, t_out, "A" if side > 0 else "B")
        if not np.isfinite(px_out):
            continue
        qty = SIZE / px_in
        tr = C.crypto_trade(f_in, f_out, side, px_in, px_out, qty, r.coin)
        tr.update(wallet=r.wallet, month=r.month, tag_in=tag_in, tag_out=tag_out)
        rows.append(tr)
    return pd.DataFrame(rows)


def month_starts(a, b):
    return list(pd.date_range(a, b, freq="MS", tz="UTC"))


def select_wallets(mp: pd.DataFrame, m, metric: str, decile: str, q=0.1):
    g = mp[(mp.month == m)].dropna(subset=[metric])
    if len(g) < MIN_WALLETS:
        return []
    k = max(3, int(len(g) * q))
    g = g.sort_values(metric, ascending=(decile == "bottom"))
    return list(g.addr.head(k))


def run_copy(params, mp, eps_by_wallet, tape, months):
    parts = []
    for m in months:
        ws = select_wallets(mp, m, params["metric"], params["decile"])
        for w in ws:
            e = eps_by_wallet.get(w)
            if e is None:
                continue
            e = e[(e.t_open >= m) & (e.t_open < m + pd.offsets.MonthBegin(1))]
            if params.get("min_notional"):
                e = e[e.open_notional >= params["min_notional"]]
            if len(e) == 0:
                continue
            e = e.assign(wallet=w, month=m)
            parts.append(e)
    if not parts:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    ep = pd.concat(parts, ignore_index=True)
    return copy_trades(ep, tape, params["delay"], params["hold"], params["mode"], 1 if params["decile"] == "top" else -1)


def summarize(tr, label=""):
    r = C.evaluate(tr, n_folds=1) if len(tr) else C.empty_result(1)
    return r


def monthly_folds(tr: pd.DataFrame):
    if len(tr) == 0:
        return pd.Series(dtype=float)
    t = C.add_pnl(tr)
    return t.groupby(t.entry_time.dt.to_period("M")).net_pnl.sum()


def main(out_prefix="h_hl_wallet_copy"):
    panel, fills = load_panel()
    print("wallets with perp fills:", len(fills), panel.group.value_counts().to_dict())
    daily = wallet_daily(fills)
    first = min(df.time.min() for df in fills.values()); last = max(df.time.max() for df in fills.values())
    months = month_starts("2025-06-01", "2026-08-01")
    mp = build_month_panel(daily, panel, months)
    mp.to_parquet(WD / "month_panel.parquet")
    print("wallet-months:", len(mp), mp.groupby("month").size().to_dict())
    feats = ["t30_pnl", "t30_sharpe", "t30_roi", "t90_pnl", "t90_sharpe", "t90_roi"]
    targets = ["nx_pnl", "nx_sharpe", "nx_roi"]
    clean = mp[mp.month + pd.Timedelta(days=30) <= CONTAM_START]
    persist_clean = persistence_table(clean, feats, targets)
    persist_all = persistence_table(mp, feats, targets)
    persist_rand = persistence_table(clean[clean.group != "top"], feats, targets)
    # shuffle baseline for persistence: permute feature within month
    rng = np.random.default_rng(0)
    sh = clean.copy(); sh["t30_sharpe"] = sh.groupby("month").t30_sharpe.transform(lambda s: rng.permutation(s.values))
    persist_shuf = persistence_table(sh, ["t30_sharpe"], targets)

    # ---- Part B
    tape = Tape(fills)
    dens = pd.Series(tape.density()).sort_values(ascending=False)
    eps = {a: episodes(df) for a, df in fills.items()}
    n_ep = sum(len(e) for e in eps.values())
    print("episodes:", n_ep, "tape coins:", len(dens))
    test_months = month_starts("2026-01-01", "2026-08-01")
    is_months = test_months[:3]; oos_months = test_months[3:]
    grid = [dict(metric=met, decile="top", delay=d, hold=h, mode=mo)
            for met in ("t30_sharpe", "t90_sharpe", "t30_roi", "t30_pnl")
            for d in (1, 5, 60) for h, mo in ((24, "mirror"), (24, "fixed"), (4, "mirror"))]
    results = []
    cache = {}
    for p in grid:
        key = json.dumps(p, sort_keys=True)
        tr = run_copy(p, mp, eps, tape, test_months); cache[key] = tr
        t = C.add_pnl(tr) if len(tr) else tr
        is_tr = t[t.month.isin(is_months)] if len(t) else t
        oos_tr = t[t.month.isin(oos_months)] if len(t) else t
        r_is = C.evaluate(is_tr, 1) if len(is_tr) else C.empty_result(1)
        r_oos = C.evaluate(oos_tr, 1) if len(oos_tr) else C.empty_result(1)
        oos_clean = oos_tr[oos_tr.entry_time < CONTAM_START] if len(oos_tr) else oos_tr
        r_oc = C.evaluate(oos_clean, 1) if len(oos_clean) else C.empty_result(1)
        results.append(dict(**p, is_n=r_is["n"], is_net=r_is["net"], is_pf=r_is["pf"], is_sharpe=r_is["sharpe"],
                            oos_n=r_oos["n"], oos_net=r_oos["net"], oos_pf=r_oos["pf"], oos_bps=r_oos["net_bps"],
                            oosclean_n=r_oc["n"], oosclean_net=r_oc["net"], oosclean_pf=r_oc["pf"],
                            wallet_months=int(tr[["wallet", "month"]].drop_duplicates().shape[0]) if len(tr) else 0))
        print(p, "IS", r_is["n"], round(r_is["net"], 1), "OOS", r_oos["n"], round(r_oos["net"], 1), round(r_oos["pf"], 2), flush=True)
    res = pd.DataFrame(results)
    # walk-forward: pick by in-sample net (min 30 trades)
    elig = res[res.is_n >= 30]
    best = (elig if len(elig) else res).sort_values("is_net", ascending=False).iloc[0]
    bp = {k: best[k] for k in ("metric", "decile", "delay", "hold", "mode")}
    bp["delay"] = int(bp["delay"]); bp["hold"] = int(bp["hold"])
    tr_best = cache[json.dumps(bp, sort_keys=True)]
    tr_best = C.add_pnl(tr_best) if len(tr_best) else tr_best.assign(month=pd.NaT, wallet="", tag_in="", tag_out="")
    oos = tr_best[tr_best.month.isin(oos_months)]
    # inverse: fade bottom decile, same params
    fp = dict(bp, decile="bottom")
    tr_fade = run_copy(fp, mp, eps, tape, test_months)
    tr_fade = C.add_pnl(tr_fade) if len(tr_fade) else tr_fade
    # random-wallet baseline: same params but random decile of wallets (10 draws)
    rand_nets = []
    rng = np.random.default_rng(1)
    for k in range(10):
        parts = []
        for m in oos_months:
            g = mp[mp.month == m].dropna(subset=[bp["metric"]])
            if len(g) < MIN_WALLETS:
                continue
            ws = rng.choice(g.addr.values, max(3, int(len(g) * 0.1)), replace=False)
            for w in ws:
                e = eps.get(w)
                if e is None: continue
                e = e[(e.t_open >= m) & (e.t_open < m + pd.offsets.MonthBegin(1))]
                if len(e): parts.append(e.assign(wallet=w, month=m))
        if parts:
            trr = copy_trades(pd.concat(parts, ignore_index=True), tape, bp["delay"], bp["hold"], bp["mode"], 1)
            rr = C.evaluate(trr, 1) if len(trr) else C.empty_result(1)
            rand_nets.append((rr["n"], rr["net"], rr["net_bps"]))
    out = dict(panel=panel, mp=mp, persist_clean=persist_clean, persist_all=persist_all, persist_rand=persist_rand,
               persist_shuf=persist_shuf, res=res, bp=bp, tr_best=tr_best, oos=oos, tr_fade=tr_fade, rand=rand_nets,
               tape=tape, dens=dens, months=test_months, is_months=is_months, oos_months=oos_months, n_ep=n_ep,
               first=first, last=last, fills=fills, eps=eps)
    return out


if __name__ == "__main__":
    o = main()


# ----------------------------------------------------------------------------- report
def fmt(df: pd.DataFrame, cols=None, nd=2):
    d = df if cols is None else df[cols]
    lines = ["| " + " | ".join(d.columns) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        cells = []
        for v in r.values:
            if isinstance(v, (float, np.floating)):
                cells.append("nan" if not np.isfinite(v) else (f"{v:.{nd}f}" if abs(v) < 1e6 else f"{v:.3g}"))
            elif isinstance(v, pd.Timestamp):
                cells.append(v.strftime("%Y-%m"))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def sanity(o):
    """Sanity checks on the walk-forward OOS trades of the selected copy variant."""
    oos = o["oos"]; res = o["res"]; bp = o["bp"]
    out = {}
    if len(oos) == 0:
        return out
    r = C.evaluate(oos, 1)
    out["oos"] = r
    out["monthly"] = monthly_folds(oos)
    clean = oos[oos.entry_time < CONTAM_START]
    out["oos_clean"] = C.evaluate(clean, 1) if len(clean) else C.empty_result(1)
    out["oos_clean_monthly"] = monthly_folds(clean)
    # top-3 trade removal
    s = oos.sort_values("net_pnl", ascending=False)
    out["top3_removed_net"] = float(s.net_pnl.iloc[3:].sum())
    out["top3_share"] = float(s.net_pnl.iloc[:3].sum())
    # shuffle: random sign per trade (sign-flip null) -> distribution of net
    rng = np.random.default_rng(7)
    g = oos.gross_pnl.values; f = oos.fee_usd.values
    sh = np.array([(g * rng.choice([-1, 1], len(g)) - f).sum() for _ in range(2000)])
    out["signflip_p"] = float((sh >= r["net"]).mean()); out["signflip_mean"] = float(sh.mean()); out["signflip_sd"] = float(sh.std())
    # random-wallet baseline (same params, random decile of wallets)
    out["random_wallets"] = o["rand"]
    # concentration
    out["by_coin"] = oos.groupby("instrument").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"), ntl=("notional_usd", "sum")).sort_values("n", ascending=False)
    out["by_wallet"] = oos.groupby("wallet").agg(n=("net_pnl", "size"), net=("net_pnl", "sum")).sort_values("net", ascending=False)
    out["wallet_months"] = int(oos[["wallet", "month"]].drop_duplicates().shape[0])
    out["n_wallets"] = int(oos.wallet.nunique())
    out["tag_in"] = oos.tag_in.value_counts().to_dict(); out["tag_out"] = oos.tag_out.value_counts().to_dict()
    # neighbours in the grid (same metric/mode, other delay/hold) OOS net
    nb = res[(res["metric"] == bp["metric"]) & (res["mode"] == bp["mode"])][["delay", "hold", "oos_n", "oos_net", "oos_pf", "oosclean_net"]]
    out["neighbours"] = nb
    # fade (inverse) same params
    tf = o["tr_fade"]
    if len(tf):
        tfo = tf[tf.month.isin(o["oos_months"])]
        out["fade_oos"] = C.evaluate(tfo, 1) if len(tfo) else C.empty_result(1)
        out["fade_monthly"] = monthly_folds(tfo)
    # hold-time / side split
    out["by_side"] = oos.groupby("side").agg(n=("net_pnl", "size"), net=("net_pnl", "sum"))
    return out


def write_md(o, sc, path):
    L = []
    P = L.append
    panel = o["panel"]; mp = o["mp"]
    P("# hl_wallet_copy - follow informed Hyperliquid wallets\n")
    P(f"Panel: {len(o['fills'])} wallets with native-perp fills (of {len(panel)} sampled from the public leaderboard snapshot {SNAP.date()}: "
      f"{panel.group.value_counts().to_dict()}). Full public fill histories via `userFillsByTime` (cached data/hl_wallets/fills/). "
      f"Fills span {o['first'].date()} -> {o['last'].date()}. Spot (@pairs) and HIP-3 builder markets (xyz:) excluded. "
      f"Position episodes (flat->non-flat->flat) = {o['n_ep']}.\n")
    P("**Survivorship caveat.** The leaderboard is a live snapshot, so 'top'/'bottom' membership is conditioned on PnL over "
      f"{CONTAM_START.date()} -> {SNAP.date()}. Everything that touches that window is marked *contaminated*; the clean headline excludes it. "
      "The 'random' group is conditioned only on being active (>=$100k 30d volume) at the snapshot.\n")
    P("## Part A - persistence of wallet skill (monthly wallet panel)\n")
    P(f"Wallet-month eligibility: >=10 fills and >=$100k notional in the trailing 30d. Wallet-months: {len(mp)} total, "
      f"{len(mp[mp.month + pd.Timedelta(days=30) <= CONTAM_START])} clean. Features = trailing 30d/90d net realized PnL (closedPnl - fees), "
      "daily-PnL Sharpe (annualised), PnL per $ notional (bps). Targets = next-30d net realized PnL / Sharpe / bps. "
      "Spearman rho per month, mean across months, t-stat; decile spread = mean target of top decile minus bottom decile; "
      "top_winrate = fraction of months in which the top decile's mean next-30d PnL was positive.\n")
    P("### Clean months (target window ends before the contaminated window)\n")
    P(fmt(o["persist_clean"], nd=3))
    P("\n### Clean months, 'top' group excluded (bottom + random only)\n")
    P(fmt(o["persist_rand"], nd=3))
    P("\n### All months incl. contaminated (look-ahead by construction for 'top' - shown for contrast)\n")
    P(fmt(o["persist_all"], nd=3))
    P("\n### Shuffle baseline (t30_sharpe permuted within month, clean months)\n")
    P(fmt(o["persist_shuf"], nd=3))
    P(f"\nPer-month wallet counts: {mp.groupby('month').size().to_dict()}\n".replace("Timestamp(", "").replace(", tz='UTC')", ""))
    P("## Part B - copy strategy (walk-forward)\n")
    P(f"Months tested {o['months'][0].date()} -> {o['months'][-1].date()}; in-sample selection = {[m.strftime('%Y-%m') for m in o['is_months']]}, "
      f"OOS = {[m.strftime('%Y-%m') for m in o['oos_months']]}. Each month the top decile of eligible wallets by `metric` (trailing window ending at the month start) "
      "is followed for that month. Signal = wallet opens a fresh position (flat -> long/short) at t; we enter at t + delay at the first real "
      "taker print on our side (panel tape, 15-min window; fallback next 1h candle open); exit when the wallet is flat again + delay ('mirror') "
      f"or after `hold` hours ('fixed'), same price rule. ${SIZE:.0f} notional per trade, taker {TAKER*1e4:.1f} bps per side. "
      "Fill-source counts on OOS trades: " + str(sc.get("tag_in")) + " (entry), " + str(sc.get("tag_out")) + " (exit).\n")
    P("### In-sample grid (all variants; OOS columns shown for transparency only, selection used is_net)\n")
    P(fmt(o["res"].sort_values("is_net", ascending=False), ["metric", "delay", "hold", "mode", "is_n", "is_net", "is_pf", "oos_n", "oos_net", "oos_pf", "oos_bps", "oosclean_n", "oosclean_net", "oosclean_pf", "wallet_months"]))
    P(f"\n### Selected (by in-sample net): `{o['bp']}`\n")
    if "oos" in sc:
        r = sc["oos"]; rc = sc["oos_clean"]
        P(f"OOS (all OOS months): n={r['n']} net=${r['net']:.2f} gross=${r['gross']:.2f} fees=${r['fees']:.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
          f"sharpe={r['sharpe']:.2f} bps={r['net_bps']:.1f} maxdd=${r['max_dd']:.0f} wallets={sc['n_wallets']} wallet-months={sc['wallet_months']}\n")
        P(f"OOS CLEAN (entries before {CONTAM_START.date()}): n={rc['n']} net=${rc['net']:.2f} pf={rc['pf']:.2f} wr={rc['wr']:.2f} bps={rc['net_bps']:.1f}\n")
        P("Monthly OOS net (USD): " + ", ".join(f"{k}: {v:.1f}" for k, v in sc["monthly"].items()) + "\n")
        P("### Sanity checks (OOS trades)\n")
        P(f"- Top-3 trade removal: top-3 contribute ${sc['top3_share']:.1f}; net without them = ${sc['top3_removed_net']:.1f}")
        P(f"- Sign-flip null (2000 draws, fees kept): mean={sc['signflip_mean']:.1f} sd={sc['signflip_sd']:.1f}, p(net >= observed)={sc['signflip_p']:.3f}")
        P(f"- Random-wallet baseline (same params, random decile of eligible wallets, 10 draws) [n, net, bps]: {[(a, round(b, 1), round(c, 1)) for a, b, c in sc['random_wallets']]}")
        if "fade_oos" in sc:
            f = sc["fade_oos"]
            P(f"- Inverse (fade bottom decile, same params) OOS: n={f['n']} net=${f['net']:.2f} pf={f['pf']:.2f} bps={f['net_bps']:.1f}; monthly: " + ", ".join(f"{k}: {v:.1f}" for k, v in sc["fade_monthly"].items()))
        P("- By side:\n\n" + fmt(sc["by_side"].reset_index()))
        P("\n- Neighbours (same metric/mode, other delay/hold):\n\n" + fmt(sc["neighbours"]))
        P("\n- Concentration by coin (top 12):\n\n" + fmt(sc["by_coin"].head(12).reset_index()))
        P("\n- Concentration by wallet (top 8 / bottom 4):\n\n" + fmt(pd.concat([sc["by_wallet"].head(8), sc["by_wallet"].tail(4)]).reset_index()))
    P("\n## Interpretation\n")
    P(o.get("interp", "(filled in after the run)"))
    Path(path).write_text("\n".join(L))
