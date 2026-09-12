# orb_crypto - opening-range breakout/fade, HL 15m BTC/ETH/SOL

Data: 2026-07-06 17:30 -> 2026-08-27 22:15 UTC (15m; only 52d cached). Folds: f1 07-06->07-24; f2 07-24->08-10; f3 08-10->08-27

Execution: signal = 15m close outside range, fill at NEXT bar open (taker). Stop/target resolved intrabar, stop wins ties. Time stop = open of bar at session end (00:00->08:00 UTC, 13:30->21:00 UTC). Taker fee 4.5 bps/side. $10k notional/trade.

## Headline: walk-forward OOS (params chosen on fold 1, reported on folds 2+3)

Selected: `fade_r60_t1.5` (fold-1 net -257.01, n=101)

| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 191 | -569.95 | 0.91 | 0.48 | -0.50 | 2755 | -3.0 | -543.34 | -26.61 |

## In-sample grid (fold 1) with each cell's fold-2 / fold-3 net

| variant | is_n | is_net | is_pf | is_wr | sel | f2 | f3 | f2+3 n | f2+3 net | f2+3 pf |
|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|--:|
| breakout_r30_t1.0 | 104 | -1140.6 | 0.69 | 0.45 |  | -1077.3 | -1590.9 | 203 | -2668.2 | 0.61 |
| breakout_r30_t1.5 | 104 | -1675.0 | 0.59 | 0.38 |  | -945.6 | -922.7 | 203 | -1868.3 | 0.74 |
| breakout_r30_t2.0 | 104 | -1589.2 | 0.61 | 0.38 |  | -694.2 | -1208.1 | 203 | -1902.3 | 0.74 |
| breakout_r60_t1.0 | 101 | -1456.3 | 0.58 | 0.43 |  | -1055.9 | -1423.7 | 191 | -2479.6 | 0.65 |
| breakout_r60_t1.5 | 101 | -1197.9 | 0.66 | 0.42 |  | -1545.3 | -1227.2 | 191 | -2772.5 | 0.63 |
| breakout_r60_t2.0 | 101 | -1083.5 | 0.69 | 0.42 |  | -1373.0 | -1272.7 | 191 | -2645.7 | 0.65 |
| fade_r30_t1.0 | 104 | -775.6 | 0.78 | 0.53 |  | -706.6 | -281.4 | 203 | -988.0 | 0.83 |
| fade_r30_t1.5 | 104 | -920.3 | 0.75 | 0.46 |  | -545.4 | 494.3 | 203 | -51.1 | 0.99 |
| fade_r30_t2.0 | 104 | -517.9 | 0.86 | 0.46 |  | -348.7 | 634.5 | 203 | 285.8 | 1.05 |
| fade_r60_t1.0 | 101 | -361.3 | 0.87 | 0.52 |  | -601.0 | -359.5 | 191 | -960.4 | 0.84 |
| fade_r60_t1.5 | 101 | -257.0 | 0.91 | 0.50 | * | -543.3 | -26.6 | 191 | -570.0 | 0.91 |
| fade_r60_t2.0 | 101 | -463.9 | 0.85 | 0.46 |  | -567.0 | 18.3 | 191 | -548.8 | 0.91 |

## Sanity checks

- **Shuffle** (200 reps; random entry bar inside session + random side, same stop/target geometry): mean -2157.9, sd 911.0, p5 -3649.3, p95 -597.3. Real OOS -570.0 at percentile 0.95.
- **Fold consistency**: fold2 -543.3, fold3 -26.6.
- **Neighbors** (same mode, fold2+3 net): fade_r30_t1.0=-988, fade_r30_t1.5=-51, fade_r30_t2.0=286, fade_r60_t1.0=-960, fade_r60_t1.5=-570, fade_r60_t2.0=-549
- **Per coin (OOS)**: BTC: n=62 net=174, ETH: n=66 net=-395, SOL: n=63 net=-350. 24h vol USD: BTC 3.70B, ETH 1.68B, SOL 1.24B (no illiquid names).
- **Per session (OOS)**: 00:00: n=99 net=-237, 13:30: n=92 net=-333
- **Exit reason (OOS)**: stop: n=64 net=-5191, target: n=31 net=2617, time: n=96 net=2004
- Avg range width 73 bps; avg risk 92 bps; round-trip fee 9 bps = 10% of 1R.

## Per-session diagnostic (best geometry, full period, all folds)

| mode | session | n | net | pf | wr | folds |
|---|---|--:|--:|--:|--:|---|
| breakout | 00:00 | 152 | -1489.8 | 0.72 | 0.36 | [-43, -1079, -368] |
| breakout | 13:30 | 140 | -2480.7 | 0.57 | 0.36 | [-1155, -466, -859] |
| fade | 00:00 | 152 | -717.3 | 0.85 | 0.47 | [-480, -130, -107] |
| fade | 13:30 | 140 | -109.7 | 0.98 | 0.50 | [223, -413, 80] |

## Verdict: **none**

Criteria: {"net_pos": false, "pf": false, "n": true, "folds": false, "shuffle": true, "neighbors": false}
