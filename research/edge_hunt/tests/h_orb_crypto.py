"""Hypothesis orb_crypto (round 1): Opening-range breakout / fade on HL 15m
BTC/ETH/SOL. Ranges at 00:00 UTC and 13:30 UTC, 30/60-min range, stop at
opposite side of range, target = R multiple, time stop at session end.
Taker fees on every side. Strict causality: signal is a 15m bar CLOSE outside
the range; fill at the NEXT bar's open.

Run: /Users/molt_bot/latpfn-trading/venv/bin/python tests/h_orb_crypto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as C  # noqa: E402

COINS = ["BTC", "ETH", "SOL"]
TF = "15m"
NOTIONAL = 10_000.0  # USD per trade, fixed
STRATEGY = "orb_crypto"
# session_start (UTC) -> session_end (UTC). Time stop = open of the bar at session_end.
SESSIONS = {
    "00:00": ("00:00", "08:00"),
    "13:30": ("13:30", "21:00"),
}
BAR = pd.Timedelta(minutes=15)

BARS = {c: C.hl_candles(c, TF) for c in COINS}
DATA_START = max(b.index.min() for b in BARS.values())
DATA_END = min(b.index.max() for b in BARS.values())
TIMES = (DATA_START, DATA_END)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def _sim_exit(bars: pd.DataFrame, i_entry: int, i_end: int, side: int,
              stop: float, target: float):
    """Walk bars i_entry..i_end-1 (bar i_entry is the fill bar, entry at its
    open). Conservative: if a bar touches both stop and target, stop wins.
    Time stop: exit at open of bar i_end. Returns (exit_time, exit_px, reason)."""
    hi = bars["high"].values
    lo = bars["low"].values
    idx = bars.index
    for i in range(i_entry, i_end):
        if side > 0:
            if lo[i] <= stop:
                return idx[i] + BAR, stop, "stop"
            if hi[i] >= target:
                return idx[i] + BAR, target, "target"
        else:
            if hi[i] >= stop:
                return idx[i] + BAR, stop, "stop"
            if lo[i] <= target:
                return idx[i] + BAR, target, "target"
    return idx[i_end], float(bars["open"].values[i_end]), "time"


def run_coin(coin: str, p: dict, start, end, rng: np.random.Generator | None = None) -> list[dict]:
    """p: range_min (30|60), tgt_mult (1|1.5|2), mode ('breakout'|'fade'),
    sessions (list of session keys).  If rng is given, run the SHUFFLE control:
    same sessions, but a random entry bar within the session and a random side
    (range geometry kept)."""
    bars = BARS[coin]
    idx = bars.index
    n_range = int(p["range_min"] // 15)
    out = []
    days = pd.date_range(idx.min().normalize(), idx.max().normalize(), freq="D")
    pos_map = {t: i for i, t in enumerate(idx)}
    for day in days:
        for skey in p["sessions"]:
            s_str, e_str = SESSIONS[skey]
            s_t = day + pd.Timedelta(hours=int(s_str[:2]), minutes=int(s_str[3:]))
            e_t = day + pd.Timedelta(hours=int(e_str[:2]), minutes=int(e_str[3:]))
            if s_t not in pos_map or e_t not in pos_map:
                continue
            i_s, i_e = pos_map[s_t], pos_map[e_t]
            # verify contiguity of the session bars
            if (i_e - i_s) != int((e_t - s_t) / BAR):
                continue
            rh = bars["high"].values[i_s:i_s + n_range].max()
            rl = bars["low"].values[i_s:i_s + n_range].min()
            width = rh - rl
            if width <= 0:
                continue
            # scan for first close outside the range, bar i in [i_s+n_range, i_e-2]
            # (need i+1 < i_e so the fill bar is inside the session)
            first = None
            if rng is None:
                cl = bars["close"].values
                for i in range(i_s + n_range, i_e - 1):
                    if cl[i] > rh:
                        first = (i, +1)
                        break
                    if cl[i] < rl:
                        first = (i, -1)
                        break
            else:
                i = int(rng.integers(i_s + n_range, i_e - 1))
                first = (i, int(rng.choice([-1, 1])))
            if first is None:
                continue
            i_sig, bdir = first
            i_fill = i_sig + 1
            entry_t = idx[i_fill]
            if not (pd.Timestamp(start) <= entry_t < pd.Timestamp(end)):
                continue
            entry_px = float(bars["open"].values[i_fill])
            # risk = distance from entry to opposite side of range (breakout stop)
            if bdir > 0:
                risk = entry_px - rl
            else:
                risk = rh - entry_px
            if risk <= 0:
                # gap back inside beyond the range - degenerate; use range width
                risk = width
            if p["mode"] == "breakout":
                side = bdir
            else:
                side = -bdir
            stop = entry_px - side * risk
            target = entry_px + side * p["tgt_mult"] * risk
            exit_t, exit_px, reason = _sim_exit(bars, i_fill, i_e, side, stop, target)
            qty = NOTIONAL / entry_px
            row = C.crypto_trade(entry_t, exit_t, side, entry_px, exit_px, qty, coin)
            row.update(reason=reason, session=skey, range_w_bps=width / entry_px * 1e4,
                       risk_bps=risk / entry_px * 1e4)
            out.append(row)
    return out


def run_fn(p: dict, start, end) -> pd.DataFrame:
    rows = []
    for c in COINS:
        rows.extend(run_coin(c, p, start, end))
    if not rows:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return pd.DataFrame(rows)


def shuffle_fn(p: dict, start, end, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for c in COINS:
        rows.extend(run_coin(c, p, start, end, rng=rng))
    if not rows:
        return pd.DataFrame(columns=C.REQUIRED_TRADE_COLS)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
GRID = [
    dict(range_min=rm, tgt_mult=tm, mode=md, sessions=["00:00", "13:30"])
    for md in ("breakout", "fade")
    for rm in (30, 60)
    for tm in (1.0, 1.5, 2.0)
]  # 12 combos; sessions pooled.  Per-session split reported as a diagnostic.


def vname(p: dict, suffix: str = "") -> str:
    return f"{p['mode']}_r{p['range_min']}_t{p['tgt_mult']}{suffix}"


def fmt(r: dict) -> str:
    return (f"n={r['n']:4d} net={r['net']:9.2f} pf={r['pf']:.2f} wr={r['wr']:.2f} "
            f"sharpe={r['sharpe']:.2f} dd={r['max_dd']:.0f} bps={r['net_bps']:.1f} "
            f"folds={[round(f, 1) for f in r['folds']]}")


def main():
    bounds = C.fold_bounds(TIMES, 3)
    print(f"Data {DATA_START} -> {DATA_END}; folds:")
    for i, (s, e) in enumerate(bounds):
        print(f"  fold{i+1}: {s} -> {e}")
    period = (DATA_START, DATA_END)
    lines = []
    lines.append(f"# orb_crypto - opening-range breakout/fade, HL 15m BTC/ETH/SOL\n")
    lines.append(f"Data: {DATA_START:%Y-%m-%d %H:%M} -> {DATA_END:%Y-%m-%d %H:%M} UTC (15m; only 52d cached). "
                 f"Folds: " + "; ".join(f"f{i+1} {s:%m-%d}->{e:%m-%d}" for i, (s, e) in enumerate(bounds)) + "\n")
    lines.append("Execution: signal = 15m close outside range, fill at NEXT bar open (taker). Stop/target "
                 "resolved intrabar, stop wins ties. Time stop = open of bar at session end "
                 "(00:00->08:00 UTC, 13:30->21:00 UTC). Taker fee 4.5 bps/side. $10k notional/trade.\n")

    # ---------------- walk-forward ----------------
    rep = C.full_report(GRID, run_fn, TIMES, n_folds=3, min_trades=10)
    best = rep["best_params"]
    oos = rep["oos"]
    print("\nBEST (fold1):", best)
    print("OOS:", fmt(oos))

    # full-period metrics for every cell (for sensitivity + lab recording)
    full_rows = []
    for i, p in enumerate(GRID):
        tr = run_fn(p, DATA_START, DATA_END + BAR)
        r = C.evaluate(tr, n_folds=3, start=bounds[0][0], end=bounds[-1][1])
        # fold2+3 only (out-of-sample relative to fold-1 selection)
        tr23 = tr[tr["entry_time"] >= bounds[1][0]] if len(tr) else tr
        r23 = C.evaluate(tr23, n_folds=3, start=bounds[0][0], end=bounds[-1][1])
        full_rows.append(dict(idx=i, variant=vname(p), n=r["n"], net=r["net"], pf=r["pf"], wr=r["wr"],
                              f1=r["folds"][0], f2=r["folds"][1], f3=r["folds"][2],
                              oos23_n=r23["n"], oos23_net=r23["net"], oos23_pf=r23["pf"]))
        C.record_to_lab(STRATEGY, vname(p, "_full"), "BTC,ETH,SOL", TF, p, r, period=period,
                        source="tests/h_orb_crypto.py",
                        notes="full-period all 3 folds (in-sample grid cell); taker fees; $10k notional")
        C.record_to_lab(STRATEGY, vname(p, "_oos23"), "BTC,ETH,SOL", TF, p, r23, period=period,
                        source="tests/h_orb_crypto.py",
                        notes="folds 2+3 only for this cell (not selected by walk-forward unless flagged)")
    full = pd.DataFrame(full_rows)
    ins = rep["insample"].copy()
    ins["variant"] = [vname(p) for p in GRID]
    table = ins[["idx", "variant", "is_n", "is_net", "is_pf", "is_wr", "selected"]].merge(
        full[["idx", "f2", "f3", "oos23_n", "oos23_net", "oos23_pf"]], on="idx")
    pd.set_option("display.width", 200)
    print("\nIN-SAMPLE GRID (fold1) + each cell's fold2/fold3 net:")
    print(table.to_string(index=False))

    C.record_to_lab(STRATEGY, "WF_selected_oos", "BTC,ETH,SOL", TF, best, oos, period=period,
                    source="tests/h_orb_crypto.py",
                    notes=f"HEADLINE walk-forward OOS (folds 2+3), selected on fold1: {vname(best)}")

    # ---------------- sanity checks ----------------
    oos_tr = rep["oos_trades"]
    # (a) shuffle: random entry bar within session + random side, same geometry
    sh_nets = []
    for seed in range(200):
        parts = [shuffle_fn(best, s, e, seed * 7 + k) for k, (s, e) in enumerate(bounds[1:])]
        st = pd.concat(parts, ignore_index=True)
        sh_nets.append(C.evaluate(st)["net"] if len(st) else 0.0)
    sh_nets = np.array(sh_nets)
    pct = float((sh_nets < oos["net"]).mean())
    print(f"\nSHUFFLE (200 reps, random timing+side): mean={sh_nets.mean():.1f} sd={sh_nets.std():.1f} "
          f"p5={np.percentile(sh_nets,5):.1f} p95={np.percentile(sh_nets,95):.1f}; real OOS={oos['net']:.1f} "
          f"-> percentile {pct:.2f}")
    C.record_to_lab(STRATEGY, "shuffle_control_mean", "BTC,ETH,SOL", TF, best,
                    dict(C.empty_result(), n=int(len(oos_tr)), net=float(sh_nets.mean()), folds=[0, 0, 0]),
                    period=period, source="tests/h_orb_crypto.py",
                    notes=f"mean of 200 shuffled-timing controls; real OOS percentile={pct:.2f}", trust="synthetic")

    # (b) fold consistency already in oos['folds']
    # (c) neighbors: same mode, adjacent range/target; report fold2+3 net for each
    nb = table[table["variant"].str.startswith(best["mode"])]
    print("\nNEIGHBORS (same mode), fold2+3 net:")
    print(nb[["variant", "is_net", "oos23_n", "oos23_net", "oos23_pf"]].to_string(index=False))

    # (d) per-coin / per-session / per-exit-reason breakdown of OOS
    if len(oos_tr):
        t = C.add_pnl(oos_tr)
        by_coin = t.groupby("instrument")["net_pnl"].agg(["count", "sum"])
        by_sess = t.groupby("session")["net_pnl"].agg(["count", "sum"])
        by_reason = t.groupby("reason")["net_pnl"].agg(["count", "sum"])
        print("\nOOS by coin:\n", by_coin)
        print("OOS by session:\n", by_sess)
        print("OOS by exit reason:\n", by_reason)
        u = C.hl_universe().set_index("coin")
        vol = {c: float(u.loc[c, "dayNtlVlm"]) for c in COINS}
        print("24h volume USD:", vol)
        for c in COINS:
            rc = C.evaluate(oos_tr[oos_tr["instrument"] == c], n_folds=3, start=bounds[0][0], end=bounds[-1][1])
            C.record_to_lab(STRATEGY, "WF_selected_oos_percoin", c, TF, best, rc, period=period,
                            source="tests/h_orb_crypto.py", notes="per-coin slice of WF OOS")
        avg_range = t["range_w_bps"].mean()
        avg_risk = t["risk_bps"].mean()
    else:
        by_coin = by_sess = by_reason = pd.DataFrame()
        vol = {}
        avg_range = avg_risk = float("nan")

    # per-session breakout vs fade full period (diagnostic: is either session special?)
    sess_rows = []
    for md in ("breakout", "fade"):
        for sk in SESSIONS:
            p = dict(best, mode=md, sessions=[sk])
            tr = run_fn(p, DATA_START, DATA_END + BAR)
            r = C.evaluate(tr, n_folds=3, start=bounds[0][0], end=bounds[-1][1])
            sess_rows.append(dict(mode=md, session=sk, n=r["n"], net=r["net"], pf=r["pf"], wr=r["wr"],
                                  folds=[round(f) for f in r["folds"]]))
            C.record_to_lab(STRATEGY, f"{md}_r{best['range_min']}_t{best['tgt_mult']}_sess{sk}",
                            "BTC,ETH,SOL", TF, p, r, period=period, source="tests/h_orb_crypto.py",
                            notes="single-session diagnostic, full period")
    sess_df = pd.DataFrame(sess_rows)
    print("\nPER-SESSION (best geometry), full period:\n", sess_df.to_string(index=False))

    # ---------------- verdict ----------------
    oos_folds = oos["folds"][1:]
    crit = dict(net_pos=oos["net"] > 0, pf=oos["pf"] >= 1.2, n=oos["n"] >= 60,
                folds=all(f > 0 for f in oos_folds), shuffle=pct >= 0.95,
                neighbors=bool((nb["oos23_net"] > 0).mean() >= 0.5))
    if all(crit.values()):
        verdict = "edge"
    elif oos["net"] > 0:
        verdict = "weak"
    else:
        verdict = "none"
    print("\nCRITERIA:", crit, "-> VERDICT:", verdict)

    # ---------------- markdown ----------------
    lines.append("## Headline: walk-forward OOS (params chosen on fold 1, reported on folds 2+3)\n")
    lines.append(f"Selected: `{vname(best)}` (fold-1 net {float(ins.loc[ins.selected,'is_net'].iloc[0]):.2f}, "
                 f"n={int(ins.loc[ins.selected,'is_n'].iloc[0])})\n")
    lines.append("| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |\n|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    lines.append(f"| {oos['n']} | {oos['net']:.2f} | {oos['pf']:.2f} | {oos['wr']:.2f} | {oos['sharpe']:.2f} | "
                 f"{oos['max_dd']:.0f} | {oos['net_bps']:.1f} | {oos_folds[0]:.2f} | {oos_folds[1]:.2f} |\n")
    lines.append("## In-sample grid (fold 1) with each cell's fold-2 / fold-3 net\n")
    lines.append("| variant | is_n | is_net | is_pf | is_wr | sel | f2 | f3 | f2+3 n | f2+3 net | f2+3 pf |\n"
                 "|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|--:|")
    for _, r in table.iterrows():
        lines.append(f"| {r.variant} | {r.is_n} | {r.is_net:.1f} | {r.is_pf:.2f} | {r.is_wr:.2f} | "
                     f"{'*' if r.selected else ''} | {r.f2:.1f} | {r.f3:.1f} | {r.oos23_n} | {r.oos23_net:.1f} | {r.oos23_pf:.2f} |")
    lines.append("\n## Sanity checks\n")
    lines.append(f"- **Shuffle** (200 reps; random entry bar inside session + random side, same stop/target geometry): "
                 f"mean {sh_nets.mean():.1f}, sd {sh_nets.std():.1f}, p5 {np.percentile(sh_nets,5):.1f}, "
                 f"p95 {np.percentile(sh_nets,95):.1f}. Real OOS {oos['net']:.1f} at percentile {pct:.2f}.")
    lines.append(f"- **Fold consistency**: fold2 {oos_folds[0]:.1f}, fold3 {oos_folds[1]:.1f}.")
    lines.append(f"- **Neighbors** (same mode, fold2+3 net): " +
                 ", ".join(f"{r.variant}={r.oos23_net:.0f}" for _, r in nb.iterrows()))
    if len(oos_tr):
        lines.append("- **Per coin (OOS)**: " + ", ".join(f"{c}: n={int(by_coin.loc[c,'count'])} net={by_coin.loc[c,'sum']:.0f}"
                                                        for c in by_coin.index) +
                     f". 24h vol USD: " + ", ".join(f"{c} {v/1e9:.2f}B" for c, v in vol.items()) + " (no illiquid names).")
        lines.append("- **Per session (OOS)**: " + ", ".join(f"{s}: n={int(by_sess.loc[s,'count'])} net={by_sess.loc[s,'sum']:.0f}"
                                                           for s in by_sess.index))
        lines.append("- **Exit reason (OOS)**: " + ", ".join(f"{s}: n={int(by_reason.loc[s,'count'])} net={by_reason.loc[s,'sum']:.0f}"
                                                            for s in by_reason.index))
        lines.append(f"- Avg range width {avg_range:.0f} bps; avg risk {avg_risk:.0f} bps; round-trip fee 9 bps "
                     f"= {9/avg_risk*100:.0f}% of 1R.")
    lines.append("\n## Per-session diagnostic (best geometry, full period, all folds)\n")
    lines.append("| mode | session | n | net | pf | wr | folds |\n|---|---|--:|--:|--:|--:|---|")
    for _, r in sess_df.iterrows():
        lines.append(f"| {r['mode']} | {r['session']} | {r['n']} | {r['net']:.1f} | {r['pf']:.2f} | {r['wr']:.2f} | {r['folds']} |")
    lines.append(f"\n## Verdict: **{verdict}**\n\nCriteria: {json.dumps({k: bool(v) for k, v in crit.items()})}\n")
    Path(__file__).with_suffix(".md").write_text("\n".join(lines))

    result = dict(best_params=best, oos=oos, oos_folds=oos_folds, verdict=verdict, crit=crit,
                  shuffle=dict(mean=float(sh_nets.mean()), sd=float(sh_nets.std()), pct=pct),
                  insample_best_net=float(ins.loc[ins.selected, "is_net"].iloc[0]),
                  table=table.to_dict("records"), sess=sess_rows,
                  by_coin=by_coin.to_dict() if len(oos_tr) else {},
                  by_reason=by_reason.to_dict() if len(oos_tr) else {},
                  avg_range_bps=avg_range, avg_risk_bps=avg_risk)
    (ROOT / "tests" / "h_orb_crypto_result.json").write_text(json.dumps(result, default=str, indent=1))
    return result


if __name__ == "__main__":
    main()
