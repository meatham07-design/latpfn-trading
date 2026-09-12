# range_edge_maker_fade - resting maker fade of opening-range edges, HL perps, 10 coins

Execution: sell limit at rh + k*w / buy limit at rl - k*w resting from the bar after the range completes; fill only if a bar trades THROUGH the level by >= 5 bps; maker fee 1.5 bps on entry and on the midpoint target (also trade-through 5 bps); taker 4.5 bps on stop (1R, R=|entry-target|), time stop (session-end open) and momentum-abort (fill bar range > opening range -> exit next open). Hourly funding charged. $1,000 per trade. One fill per side per session. HEADLINE = 15m / 60-min range (primary spec); 1h / 2-bar range is the long-sample check.


## Dataset 15m (range = first 4 bars; sessions [('00:00', ('00:00', '08:00')), ('13:30', ('13:30', '21:00'))])

Data 2026-07-06 -> 2026-08-27 UTC; folds f1 07-06->07-24; f2 07-24->08-10; f3 08-10->08-27

### Walk-forward OOS (selected on fold 1: `k0.25_mid_abort_tr1`, fold-1 net -176.54, n=216)

| n | net USD | gross | fees+fund | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 392 | -558.12 | -349.32 | 208.80 | 0.66 | 0.38 | -2.70 | 580 | -14.2 | -189.81 | -368.31 |

### In-sample grid (fold 1) + each cell's fold-2/fold-3 net

| variant | is_n | is_net | is_pf | is_wr | sel | f2 | f3 | f2+3 n | f2+3 net | f2+3 pf |
|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|--:|
| k0.0_mid_none_tr0 | 482 | -608.4 | 0.62 | 0.39 |  | -662.1 | -917.2 | 925 | -1579.3 | 0.55 |
| k0.0_mid_none_tr1 | 267 | -473.8 | 0.52 | 0.36 |  | -358.4 | -370.3 | 462 | -728.7 | 0.57 |
| k0.0_mid_abort_tr0 | 482 | -585.3 | 0.62 | 0.38 |  | -656.4 | -926.3 | 925 | -1582.7 | 0.55 |
| k0.0_mid_abort_tr1 | 267 | -463.3 | 0.51 | 0.35 |  | -350.3 | -372.7 | 462 | -723.0 | 0.57 |
| k0.0_half_none_tr0 | 482 | -608.0 | 0.62 | 0.39 |  | -655.9 | -915.3 | 925 | -1571.2 | 0.55 |
| k0.0_half_none_tr1 | 267 | -473.9 | 0.52 | 0.36 |  | -366.1 | -368.0 | 462 | -734.1 | 0.57 |
| k0.0_half_abort_tr0 | 482 | -584.8 | 0.62 | 0.38 |  | -650.2 | -922.8 | 925 | -1573.0 | 0.55 |
| k0.0_half_abort_tr1 | 267 | -463.4 | 0.51 | 0.35 |  | -358.1 | -370.4 | 462 | -728.4 | 0.57 |
| k0.1_mid_none_tr0 | 449 | -505.1 | 0.68 | 0.41 |  | -476.1 | -1262.5 | 864 | -1738.6 | 0.53 |
| k0.1_mid_none_tr1 | 246 | -402.2 | 0.58 | 0.38 |  | -200.7 | -536.0 | 430 | -736.8 | 0.59 |
| k0.1_mid_abort_tr0 | 449 | -407.7 | 0.72 | 0.40 |  | -502.7 | -1231.5 | 864 | -1734.1 | 0.52 |
| k0.1_mid_abort_tr1 | 246 | -362.8 | 0.59 | 0.38 |  | -221.2 | -507.6 | 430 | -728.8 | 0.58 |
| k0.1_half_none_tr0 | 449 | -505.5 | 0.65 | 0.40 |  | -542.2 | -1024.1 | 864 | -1566.3 | 0.52 |
| k0.1_half_none_tr1 | 246 | -370.4 | 0.57 | 0.38 |  | -259.1 | -450.0 | 430 | -709.1 | 0.56 |
| k0.1_half_abort_tr0 | 449 | -445.4 | 0.67 | 0.39 |  | -550.5 | -1026.5 | 864 | -1577.0 | 0.51 |
| k0.1_half_abort_tr1 | 246 | -357.0 | 0.55 | 0.37 |  | -263.9 | -444.2 | 430 | -708.1 | 0.55 |
| k0.25_mid_none_tr0 | 400 | -412.6 | 0.73 | 0.42 |  | -365.3 | -693.3 | 780 | -1058.7 | 0.69 |
| k0.25_mid_none_tr1 | 216 | -273.1 | 0.68 | 0.42 |  | -151.9 | -358.9 | 392 | -510.8 | 0.70 |
| k0.25_mid_abort_tr0 | 400 | -245.7 | 0.81 | 0.43 |  | -411.3 | -696.8 | 780 | -1108.1 | 0.66 |
| k0.25_mid_abort_tr1 | 216 | -176.5 | 0.76 | 0.43 | * | -189.8 | -368.3 | 392 | -558.1 | 0.66 |
| k0.25_half_none_tr0 | 400 | -454.3 | 0.64 | 0.38 |  | -361.3 | -818.4 | 780 | -1179.6 | 0.57 |
| k0.25_half_none_tr1 | 216 | -309.1 | 0.58 | 0.36 |  | -121.9 | -382.5 | 392 | -504.4 | 0.63 |
| k0.25_half_abort_tr0 | 400 | -362.6 | 0.69 | 0.39 |  | -387.3 | -794.2 | 780 | -1181.5 | 0.55 |
| k0.25_half_abort_tr1 | 216 | -252.5 | 0.62 | 0.38 |  | -142.0 | -349.6 | 392 | -491.6 | 0.62 |

### Sanity checks

- **Shuffle[level]** (200 reps): mean -546.6, sd 139.8, p5 -778.1, p95 -325.3; real OOS -558.1 at percentile 0.45.
- **Shuffle[time]** (100 reps): mean -3876.3, sd 275.0, p5 -4342.1, p95 -3441.6; real OOS -558.1 at percentile 1.00.
- **Folds**: fold2 -189.8, fold3 -368.3.
- **Neighbours** (same mom/trend, f2+3 net): k0.0_mid_abort_tr1=-723 (pf 0.57), k0.0_half_abort_tr1=-728 (pf 0.57), k0.1_mid_abort_tr1=-729 (pf 0.58), k0.1_half_abort_tr1=-708 (pf 0.55), k0.25_half_abort_tr1=-492 (pf 0.62)
- **Per coin (OOS)**: BTC: n=35 net=-14 (24h vol $3700M), DOGE: n=37 net=-46 (24h vol $17M), ENA: n=43 net=-142 (24h vol $120M), ETH: n=37 net=-63 (24h vol $1679M), HYPE: n=38 net=-26 (24h vol $970M), PUMP: n=50 net=-199 (24h vol $175M), SOL: n=36 net=4 (24h vol $1243M), SUI: n=40 net=-41 (24h vol $18M), XRP: n=38 net=79 (24h vol $118M), ZEC: n=38 net=-111 (24h vol $289M). No coin below $5M 24h volume.
- **Per session (OOS)**: 00:00: n=217 net=-388, 13:30: n=175 net=-170
- **Per side (OOS)**: short: n=176 net=-166, long: n=216 net=-392
- **Exit reason (OOS)**: abort: n=56 net=20, stop: n=179 net=-1488, target: n=94 net=806, time: n=63 net=104
- Avg range 115 bps, avg R 86 bps; gross -349.3, fees+funding 208.8 (funding 1.9).

**Verdict (15m): none** - criteria {"net_pos": false, "pf": false, "n": true, "folds": false, "shuffle": false, "neighbors": false}


## Dataset 1h (range = first 2 bars; sessions [('00:00', ('00:00', '08:00')), ('13:00', ('13:00', '21:00'))])

Data 2026-01-31 -> 2026-08-27 UTC; folds f1 01-31->04-11; f2 04-11->06-19; f3 06-19->08-27

### Walk-forward OOS (selected on fold 1: `k0.25_mid_abort_tr1`, fold-1 net -684.50, n=540)

| n | net USD | gross | fees+fund | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1039 | -696.51 | -119.51 | 577.00 | 0.84 | 0.43 | -1.80 | 1041 | -6.7 | -800.77 | 104.26 |

### In-sample grid (fold 1) + each cell's fold-2/fold-3 net

| variant | is_n | is_net | is_pf | is_wr | sel | f2 | f3 | f2+3 n | f2+3 net | f2+3 pf |
|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|--:|
| k0.0_mid_none_tr0 | 1625 | -3622.6 | 0.60 | 0.40 |  | -2772.8 | -3423.0 | 3187 | -6195.8 | 0.60 |
| k0.0_mid_none_tr1 | 735 | -1643.8 | 0.57 | 0.39 |  | -1316.4 | -1665.2 | 1383 | -2981.6 | 0.56 |
| k0.0_mid_abort_tr0 | 1625 | -3166.1 | 0.63 | 0.40 |  | -2414.7 | -3229.6 | 3187 | -5644.4 | 0.62 |
| k0.0_mid_abort_tr1 | 735 | -1483.0 | 0.59 | 0.39 |  | -1013.7 | -1563.2 | 1383 | -2576.8 | 0.60 |
| k0.0_half_none_tr0 | 1625 | -3622.8 | 0.60 | 0.40 |  | -2774.1 | -3421.0 | 3187 | -6195.2 | 0.60 |
| k0.0_half_none_tr1 | 735 | -1644.0 | 0.57 | 0.39 |  | -1315.9 | -1664.3 | 1383 | -2980.2 | 0.56 |
| k0.0_half_abort_tr0 | 1625 | -3165.8 | 0.63 | 0.40 |  | -2416.0 | -3227.7 | 3187 | -5643.8 | 0.62 |
| k0.0_half_abort_tr1 | 735 | -1483.2 | 0.59 | 0.39 |  | -1013.2 | -1562.3 | 1383 | -2575.4 | 0.60 |
| k0.1_mid_none_tr0 | 1459 | -2982.8 | 0.66 | 0.43 |  | -2367.5 | -2323.7 | 2840 | -4691.2 | 0.68 |
| k0.1_mid_none_tr1 | 658 | -1134.3 | 0.68 | 0.44 |  | -1418.8 | -941.5 | 1233 | -2360.4 | 0.63 |
| k0.1_mid_abort_tr0 | 1459 | -2585.3 | 0.67 | 0.43 |  | -2147.5 | -2158.6 | 2840 | -4306.1 | 0.68 |
| k0.1_mid_abort_tr1 | 658 | -933.1 | 0.70 | 0.45 |  | -1094.8 | -835.1 | 1233 | -1929.9 | 0.67 |
| k0.1_half_none_tr0 | 1459 | -2721.2 | 0.65 | 0.42 |  | -2304.9 | -2452.8 | 2840 | -4757.6 | 0.65 |
| k0.1_half_none_tr1 | 658 | -1118.0 | 0.66 | 0.42 |  | -1346.2 | -1091.1 | 1233 | -2437.4 | 0.58 |
| k0.1_half_abort_tr0 | 1459 | -2328.3 | 0.68 | 0.42 |  | -1921.4 | -2178.0 | 2840 | -4099.4 | 0.68 |
| k0.1_half_abort_tr1 | 658 | -899.0 | 0.69 | 0.43 |  | -1045.3 | -936.6 | 1233 | -1981.9 | 0.64 |
| k0.25_mid_none_tr0 | 1212 | -2259.0 | 0.71 | 0.45 |  | -1484.8 | -1031.9 | 2371 | -2516.6 | 0.80 |
| k0.25_mid_none_tr1 | 540 | -712.7 | 0.76 | 0.46 |  | -896.3 | -202.5 | 1039 | -1098.8 | 0.79 |
| k0.25_mid_abort_tr0 | 1212 | -1804.8 | 0.71 | 0.44 |  | -1429.7 | -633.9 | 2371 | -2063.7 | 0.81 |
| k0.25_mid_abort_tr1 | 540 | -684.5 | 0.72 | 0.44 | * | -800.8 | 104.3 | 1039 | -696.5 | 0.84 |
| k0.25_half_none_tr0 | 1212 | -2665.7 | 0.59 | 0.40 |  | -1870.5 | -1351.2 | 2371 | -3221.7 | 0.69 |
| k0.25_half_none_tr1 | 540 | -909.4 | 0.65 | 0.42 |  | -1140.8 | -624.2 | 1039 | -1765.0 | 0.63 |
| k0.25_half_abort_tr0 | 1212 | -2171.4 | 0.63 | 0.41 |  | -1403.3 | -928.7 | 2371 | -2331.9 | 0.76 |
| k0.25_half_abort_tr1 | 540 | -712.6 | 0.69 | 0.42 |  | -877.6 | -377.4 | 1039 | -1255.0 | 0.71 |

### Sanity checks

- **Shuffle[level]** (200 reps): mean -1724.5, sd 258.8, p5 -2134.1, p95 -1298.2; real OOS -696.5 at percentile 1.00.
- **Shuffle[time]** (100 reps): mean -12522.8, sd 521.3, p5 -13447.6, p95 -11701.5; real OOS -696.5 at percentile 1.00.
- **Folds**: fold2 -800.8, fold3 104.3.
- **Neighbours** (same mom/trend, f2+3 net): k0.0_mid_abort_tr1=-2577 (pf 0.60), k0.0_half_abort_tr1=-2575 (pf 0.60), k0.1_mid_abort_tr1=-1930 (pf 0.67), k0.1_half_abort_tr1=-1982 (pf 0.64), k0.25_half_abort_tr1=-1255 (pf 0.71)
- **Per coin (OOS)**: BTC: n=83 net=-41 (24h vol $3700M), DOGE: n=101 net=-196 (24h vol $17M), ENA: n=136 net=59 (24h vol $120M), ETH: n=89 net=-83 (24h vol $1679M), HYPE: n=103 net=-64 (24h vol $970M), PUMP: n=119 net=-131 (24h vol $175M), SOL: n=90 net=-162 (24h vol $1243M), SUI: n=110 net=-176 (24h vol $18M), XRP: n=96 net=53 (24h vol $118M), ZEC: n=112 net=43 (24h vol $289M). No coin below $5M 24h volume.
- **Per session (OOS)**: 00:00: n=531 net=293, 13:00: n=508 net=-989
- **Per side (OOS)**: short: n=501 net=-914, long: n=538 net=217
- **Exit reason (OOS)**: abort: n=305 net=322, stop: n=249 net=-3137, target: n=156 net=1755, time: n=329 net=364
- Avg range 168 bps, avg R 126 bps; gross -119.5, fees+funding 577.0 (funding -0.2).

**Verdict (1h): none** - criteria {"net_pos": false, "pf": false, "n": true, "folds": false, "shuffle": true, "neighbors": false}


## Post-hoc diagnostic (NOT a result): stop width on the fold-1-selected cell, full period

| tf | stop | n | net | gross | PF | WR | folds | stop/target/time/abort n |
|---|---|--:|--:|--:|--:|--:|---|---|
| 15m | 1.0 | 608 | -734.7 | -412.8 | 0.69 | 0.39 | [-177, -190, -368] | 265/149/104/90 |
| 15m | 2.0 | 608 | -676.0 | -365.3 | 0.74 | 0.46 | [-124, -176, -376] | 111/184/155/158 |
| 15m | 3.0 | 608 | -347.5 | -38.5 | 0.86 | 0.48 | [-152, -139, -57] | 48/190/202/168 |
| 15m | none | 608 | 36.0 | 343.4 | 1.02 | 0.50 | [-128, -155, 319] | 0/195/237/176 |
| 1h | 1.0 | 1579 | -1381.0 | -504.6 | 0.80 | 0.43 | [-685, -801, 104] | 379/235/488/477 |
| 1h | 2.0 | 1579 | -1311.3 | -438.1 | 0.81 | 0.45 | [-456, -960, 105] | 82/244/615/638 |
| 1h | 3.0 | 1579 | -922.5 | -49.6 | 0.86 | 0.46 | [-432, -915, 425] | 18/245/651/665 |
| 1h | none | 1579 | -863.4 | 9.5 | 0.87 | 0.46 | [-425, -968, 530] | 0/245/663/671 |