#!/usr/bin/env python
"""Offline batch runner for the repo's LaT-PFN forecaster over cached HL candles.

For every `step`-th bar t (t = last CLOSED bar), builds the exact inputs the bot's
forecaster.wrapper uses (heldout = last n_history bars of OHLC, context = 12 lagged
self-windows of Close at stride 60 => needs 900 bars <= t), runs create_forecast in
batches, and stores the wrapper-equivalent outputs (direction/confidence/regime via
the wrapper's own helper methods) for bars 1-12 plus the 60-bar end level.

Output: data/latpfn_preds/hl_{coin}_{interval}.parquet  (index = bar OPEN time of bar t)
Usage: python latpfn_batch_forecast.py --coins BTC,ETH --interval 1h --step 4 --threads 3
"""
import argparse, sys, time, logging
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, '/Users/molt_bot/latpfn-trading')
sys.path.insert(0, '/Users/molt_bot/latpfn-trading/research/edge_hunt')
import numpy as np, pandas as pd, torch
import common as C

ap = argparse.ArgumentParser()
ap.add_argument("--coins", required=True)
ap.add_argument("--interval", default="1h")
ap.add_argument("--step", type=int, default=4)
ap.add_argument("--threads", type=int, default=3)
ap.add_argument("--batch", type=int, default=32)
ap.add_argument("--max_per_coin", type=int, default=0)
args = ap.parse_args()
torch.set_num_threads(args.threads)

from forecaster.wrapper import LaTPFNPredictor
from forecaster.input_formatter import format_inputs
from forecaster.output_processor import process_forecast

N_HIST, N_PROMPT, N_CTX, STRIDE = 180, 60, 12, 60
NEED = N_HIST + N_PROMPT + (N_CTX - 1) * STRIDE   # 900 bars
cfg = {"model": dict(device="cpu", weights_path="/Users/molt_bot/latpfn-trading/models/lat_pfn_checkpoint.ckpt",
       lat_pfn_repo="/Users/molt_bot/latpfn-trading/Lat-PFN", n_context=16, n_heldout=4, n_history=N_HIST,
       n_prompt=N_PROMPT, context_mode="lagged", context_stride=STRIDE, n_bins=100)}
P = LaTPFNPredictor(cfg)
OUT = C.DATA / "latpfn_preds"; OUT.mkdir(exist_ok=True)

def run_coin(coin):
    final = OUT / f"hl_{coin}_{args.interval}.parquet"
    part = OUT / f"hl_{coin}_{args.interval}_partial.parquet"
    if final.exists():
        print(coin, "done already"); return
    bars = C.hl_candles(coin, args.interval)
    df = bars.rename(columns=str.capitalize)[["Open", "High", "Low", "Close", "Volume"]]
    # t positions: last closed bar index; leave >= 13 bars after t so the 12-bar horizon is realised
    # (not required for forecasting, but we don't need forecasts we cannot score)
    positions = list(range(NEED - 1, len(df) - 1, args.step))
    if args.max_per_coin:
        positions = positions[-args.max_per_coin:]
    done = pd.read_parquet(part) if part.exists() else None
    done_times = set(done.index) if done is not None else set()
    positions = [i for i in positions if df.index[i] not in done_times]
    rows = [] if done is None else [done]
    t0 = time.time(); n = 0
    for b0 in range(0, len(positions), args.batch):
        pos = positions[b0:b0 + args.batch]
        ts, st = [], []
        for i in pos:
            win = df.iloc[i + 1 - NEED: i + 1]           # bars <= t only
            t, s = format_inputs(win, {}, n_history=N_HIST, n_prompt=N_PROMPT, n_context=N_CTX, context_stride=STRIDE)
            ts.append(t); st.append(s)
        batch = {k: torch.cat([t[k] for t in ts], 0) for k in ts[0]}
        if batch["V_heldout_history"].shape[0] == 1:   # model requires batch > 1
            batch = {k: v.repeat(2, *([1] * (v.dim() - 1))) for k, v in batch.items()}
        with torch.no_grad():
            out = P.model.create_forecast(**batch)
        recs = []
        for j, i in enumerate(pos):
            o = {k: v[j:j + 1] for k, v in out.items()}
            pr = process_forecast(o, st[j], heldout_idx=3)
            fc, unc = pr["forecast_prices"], pr["uncertainty"]
            cur = float(df["Close"].iloc[i])
            bc_last = float(pr["backcast_prices"][-1]) if "backcast_prices" in pr else np.nan
            if np.any(~np.isfinite(fc)):
                direction, conf, regime = "neutral", 0.0, "volatile"
            else:
                direction, conf = P._analyze_forecast(fc, unc, cur)
                regime = P._detect_regime(fc, unc, cur)
            r = dict(time=df.index[i], coin=coin, current_price=cur, backcast_last=bc_last,
                     fc_end=float(np.mean(fc[-10:])), unc_mean=float(np.mean(unc)),
                     unc12_mean=float(np.mean(unc[:12])), direction=direction, confidence=float(conf), regime=regime)
            for h in range(12):
                r[f"fc_{h+1}"] = float(fc[h])
            recs.append(r)
        chunk = pd.DataFrame(recs).set_index("time")
        rows.append(chunk)
        pd.concat(rows).sort_index().to_parquet(part)
        n += len(pos)
        el = time.time() - t0
        print(f"{coin}: {n}/{len(positions)}  {el/n:.2f}s/fc  eta {(len(positions)-n)*el/n/60:.1f}m", flush=True)
    res = pd.concat(rows).sort_index() if rows else pd.DataFrame()
    res.to_parquet(final)
    if part.exists():
        part.unlink()
    print(coin, "DONE", len(res), flush=True)

for c in args.coins.split(","):
    run_coin(c)
