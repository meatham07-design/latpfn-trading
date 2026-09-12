# hl_listing_drift -- results

Fees: Binance UM taker 5.0 bps/side, Hyperliquid taker 4.5 bps/side; funding included (long pays positive rate); hedge = opposite BTC leg of equal notional (fees on both legs, BTC funding ignored). $1000 notional per event.

Binance UM archive: 139 usable listings; dropped: archive_start=3, month_boundary=0, no_data=0, gap_first_48h=0; earliest archive month 2020-01 (symbols starting there are excluded as unverifiable listings: ['ADAUSDT', 'XLMUSDT', 'XRPUSDT'])
month-boundary starts excluded (could be archive artefacts): []
listings per year: 2020: 13, 2021: 9, 2022: 7, 2023: 18, 2024: 22, 2025: 42, 2026: 28

Hyperliquid: 232 listings (meta incl. delisted; listing day = first daily candle with volume>0); dropped: never_traded=0, short=0
listings per year: 2023: 100, 2024: 66, 2025: 58, 2026: 8; delisted since: 56; funding series present: 91
HL listings inside the cached 1h window (>= 2026-02-01): ['AZTEC', 'CASHCAT', 'CHIP', 'GRAM'] -> too few for an hourly test; HL rules use daily bars.

## Descriptive: post-listing return paths (Binance UM 1h), excess vs BTC, from listing open  (n=139)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1h | 139 | 1.37 | 0.12 | 1.34 | 0.26 | 1.05 | 0.52 | -0.013 |
| 4h | 139 | 1.38 | 0.21 | 1.38 | 0.03 | 0.86 | 0.51 | -0.093 |
| 24h | 139 | 1.33 | -1.70 | 1.36 | -1.71 | 0.61 | 0.45 | -0.223 |
| 3d | 139 | -0.44 | -3.51 | -0.31 | -2.62 | -0.12 | 0.42 | -0.435 |
| 7d | 139 | -2.97 | -7.14 | -3.04 | -7.64 | -0.83 | 0.39 | -0.613 |
| 14d | 139 | -7.02 | -8.64 | -7.62 | -9.88 | -2.38 | 0.36 | -0.534 |

Post-day-1 drift (Binance UM 1h): from open of bar 24 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +24h | 139 | -1.64 | -1.91 | -1.38 | 0.38 |
| +3d | 139 | -4.24 | -3.77 | -2.63 | 0.36 |
| +7d | 139 | -5.95 | -6.66 | -2.82 | 0.37 |
| +14d | 138 | -7.09 | -7.14 | -2.12 | 0.32 |

## Descriptive: post-listing return paths (Hyperliquid 1d), excess vs BTC, from listing open  (n=232)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1d | 232 | 0.93 | -0.62 | 0.94 | -0.62 | 0.59 | 0.45 | -0.054 |
| 3d | 232 | -0.00 | -3.13 | -0.24 | -3.84 | -0.10 | 0.38 | -0.211 |
| 7d | 232 | 0.23 | -7.50 | -0.29 | -6.93 | -0.10 | 0.37 | -0.085 |
| 14d | 232 | -0.85 | -8.24 | -3.14 | -11.58 | -0.95 | 0.33 | -0.235 |

Post-day-1 drift (Hyperliquid 1d): from open of bar 1 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +1d | 232 | -0.16 | -2.71 | -0.13 | 0.34 |
| +3d | 232 | -2.25 | -3.95 | -1.55 | 0.36 |
| +7d | 232 | -2.54 | -8.93 | -1.08 | 0.35 |
| +14d | 232 | -3.46 | -11.87 | -1.10 | 0.34 |

# Binance UM listings 2019-2026 (1h): walk-forward  (listings 2020-02-03 -> 2026-07-17; fold starts ['2020-02-03', '2022-03-29', '2024-05-22'])
events per fold: [26, 28, 84] (last fold inclusive of end: 85)

**Walk-forward best (fold 1, by net):** `{'rule': 'short_after', 'N': 24, 'H': 14, 'hedge': True}`

**OOS folds 2+3:** n= 112 net=  7218.8 pf=1.61 wr=0.64 sharpe=1.71 bps= 644.5 folds=[0.0, 1214.8, 6003.9] fold_n=[0, 28, 84]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period)

| params | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {"rule": "short_after", "N": 4, "H": 1, "hedge": false} | 26 | -1056.3 | 0.54 | 0.50 | -406.3 | 139 | -1056.3 | 566.2 | 1113.8 | 1.07 | 44.9 |  |
| {"rule": "short_after", "N": 4, "H": 1, "hedge": true} | 25 | -989.3 | 0.53 | 0.48 | -395.7 | 138 | -989.3 | 691.6 | 1028.5 | 1.08 | 53.0 |  |
| {"rule": "short_after", "N": 4, "H": 3, "hedge": false} | 26 | 323.3 | 1.15 | 0.54 | 124.4 | 139 | 323.3 | 1301.0 | 1755.9 | 1.31 | 243.2 |  |
| {"rule": "short_after", "N": 4, "H": 3, "hedge": true} | 26 | 102.5 | 1.05 | 0.58 | 39.4 | 139 | 102.5 | 1272.2 | 1684.2 | 1.29 | 220.1 |  |
| {"rule": "short_after", "N": 4, "H": 7, "hedge": false} | 26 | -709.3 | 0.82 | 0.50 | -272.8 | 139 | -709.3 | 1704.0 | 4196.1 | 1.37 | 373.4 |  |
| {"rule": "short_after", "N": 4, "H": 7, "hedge": true} | 26 | -276.1 | 0.92 | 0.42 | -106.2 | 139 | -276.1 | 1559.7 | 3990.6 | 1.39 | 379.4 |  |
| {"rule": "short_after", "N": 4, "H": 14, "hedge": false} | 26 | -162.7 | 0.96 | 0.54 | -62.6 | 139 | -162.7 | 2049.2 | 8496.5 | 1.70 | 747.0 |  |
| {"rule": "short_after", "N": 4, "H": 14, "hedge": true} | 25 | 1142.0 | 1.39 | 0.60 | 456.8 | 138 | 1142.0 | 2015.6 | 7754.6 | 1.79 | 790.7 |  |
| {"rule": "short_after", "N": 24, "H": 1, "hedge": false} | 26 | 635.7 | 1.68 | 0.54 | 244.5 | 139 | 635.7 | -65.7 | 1293.3 | 1.31 | 134.0 |  |
| {"rule": "short_after", "N": 24, "H": 1, "hedge": true} | 26 | 783.4 | 1.93 | 0.62 | 301.3 | 139 | 783.4 | -66.4 | 1131.3 | 1.31 | 133.0 |  |
| {"rule": "short_after", "N": 24, "H": 3, "hedge": false} | 26 | 1378.8 | 2.10 | 0.69 | 530.3 | 139 | 1378.8 | 976.4 | 3223.2 | 1.77 | 401.3 |  |
| {"rule": "short_after", "N": 24, "H": 3, "hedge": true} | 26 | 1281.5 | 2.23 | 0.58 | 492.9 | 139 | 1281.5 | 775.2 | 3253.4 | 1.74 | 382.0 |  |
| {"rule": "short_after", "N": 24, "H": 7, "hedge": false} | 26 | 687.9 | 1.33 | 0.58 | 264.6 | 139 | 687.9 | 813.0 | 5750.1 | 1.80 | 521.7 |  |
| {"rule": "short_after", "N": 24, "H": 7, "hedge": true} | 26 | 1340.9 | 1.80 | 0.58 | 515.7 | 139 | 1340.9 | 712.7 | 5362.7 | 1.82 | 533.5 |  |
| {"rule": "short_after", "N": 24, "H": 14, "hedge": false} | 26 | 34.1 | 1.01 | 0.54 | 13.1 | 138 | 34.1 | 1154.8 | 7188.8 | 1.55 | 607.1 |  |
| {"rule": "short_after", "N": 24, "H": 14, "hedge": true} | 26 | 1881.2 | 1.75 | 0.65 | 723.5 | 138 | 1881.2 | 1214.8 | 6003.9 | 1.63 | 659.4 | * |
| {"rule": "mom1", "thr": 0.0, "Hh": 4, "contra": false} | 26 | -741.3 | 0.39 | 0.50 | -285.1 | 139 | -741.3 | -635.0 | 1554.8 | 1.03 | 12.8 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 4, "contra": true} | 26 | 689.1 | 2.35 | 0.50 | 265.0 | 139 | 689.1 | 578.9 | -1725.5 | 0.92 | -32.9 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 24, "contra": false} | 26 | -1125.1 | 0.53 | 0.50 | -432.7 | 139 | -1125.1 | 728.8 | -340.0 | 0.93 | -53.0 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 24, "contra": true} | 26 | 1072.1 | 1.83 | 0.50 | 412.3 | 139 | 1072.1 | -783.9 | 170.2 | 1.05 | 33.0 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 4, "contra": false} | 19 | -548.6 | 0.41 | 0.47 | -288.8 | 89 | -548.6 | -298.8 | 1406.2 | 1.15 | 62.8 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 4, "contra": true} | 19 | 510.7 | 2.28 | 0.53 | 268.8 | 89 | 510.7 | 259.0 | -1506.0 | 0.83 | -82.7 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 24, "contra": false} | 19 | -807.7 | 0.61 | 0.63 | -425.1 | 89 | -807.7 | 668.4 | -484.3 | 0.92 | -70.1 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 24, "contra": true} | 19 | 768.8 | 1.61 | 0.37 | 404.6 | 89 | 768.8 | -707.7 | 384.9 | 1.06 | 50.1 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 4, "contra": false} | 8 | -446.4 | 0.02 | 0.12 | -558.1 | 55 | -446.4 | -484.7 | 1478.2 | 1.21 | 99.5 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 4, "contra": true} | 8 | 430.4 | 42.32 | 0.88 | 538.0 | 55 | 430.4 | 466.9 | -1554.0 | 0.79 | -119.4 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 24, "contra": false} | 8 | -1120.8 | 0.21 | 0.50 | -1401.0 | 55 | -1120.8 | -445.5 | -17.8 | 0.75 | -288.0 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 24, "contra": true} | 8 | 1103.6 | 4.63 | 0.50 | 1379.5 | 55 | 1103.6 | 428.3 | -58.0 | 1.30 | 268.0 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 1, "hedge": false} | 3 | -273.0 | 0.13 | 0.33 | -910.0 | 10 | -273.0 | 0.0 | 222.1 | 0.86 | -50.9 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 3, "hedge": false} | 3 | -451.4 | 0.04 | 0.33 | -1504.8 | 10 | -451.4 | 0.0 | 117.6 | 0.53 | -333.9 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 7, "hedge": false} | 3 | -646.8 | 0.05 | 0.33 | -2156.2 | 10 | -646.8 | 0.0 | -260.6 | 0.23 | -907.5 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 1, "hedge": false} | 6 | -62.8 | 0.80 | 0.50 | -104.6 | 25 | -62.8 | -160.0 | 422.4 | 1.34 | 79.9 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 3, "hedge": false} | 6 | -661.5 | 0.10 | 0.33 | -1102.4 | 25 | -661.5 | -90.5 | 142.4 | 0.55 | -243.8 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 7, "hedge": false} | 6 | -1237.4 | 0.03 | 0.17 | -2062.4 | 25 | -1237.4 | 94.9 | -350.0 | 0.27 | -597.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 1, "hedge": false} | 8 | -647.7 | 0.10 | 0.38 | -809.6 | 61 | -647.7 | 48.1 | -1678.2 | 0.54 | -373.4 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 3, "hedge": false} | 8 | -1635.0 | 0.00 | 0.00 | -2043.7 | 61 | -1635.0 | -909.8 | -4094.6 | 0.24 | -1088.4 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 7, "hedge": false} | 8 | -1318.6 | 0.12 | 0.25 | -1648.3 | 61 | -1318.6 | 103.5 | -5696.1 | 0.35 | -1133.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 1, "hedge": false} | 3 | -414.7 | 0.01 | 0.33 | -1382.4 | 25 | -414.7 | 270.4 | -1686.1 | 0.36 | -732.2 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 3, "hedge": false} | 3 | -863.7 | 0.00 | 0.00 | -2878.9 | 25 | -863.7 | -222.4 | -2784.0 | 0.18 | -1548.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 7, "hedge": false} | 3 | -911.2 | 0.00 | 0.00 | -3037.3 | 25 | -911.2 | 655.7 | -3976.1 | 0.26 | -1692.6 |  |

### Walk-forward pick per rule family (selection on fold 1 only)

| family | fold-1 pick | is_net | OOS n | OOS net | OOS pf | OOS folds |
|---|---|---|---|---|---|---|
| short_after | `{'rule': 'short_after', 'N': 24, 'H': 14, 'hedge': True}` | 1881.2 | 112 | 7218.8 | 1.61 | [1214.8, 6003.9] |
| mom1 | `{'rule': 'mom1', 'thr': 0.0, 'Hh': 24, 'contra': True}` | 1072.1 | 113 | -613.7 | 0.93 | [-783.9, 170.2] |
| wick | `{'rule': 'wick', 'mode': 'near_top_short', 'x': 0.05, 'H': 1, 'hedge': False}` | -62.8 | 19 | 262.5 | 1.98 | [-160.0, 422.4] |

### Sanity checks on the walk-forward pick (OOS trades only)

- sign-shuffle (random long/short per trade, fees kept): actual net 7218.8; shuffled mean -95.3 sd 4268.5; p(shuffled >= actual) = 0.045
- random-timing baseline (same rule/hold, entry at random bar >= day 16 after listing, same coins, 200 draws): mean net 737.5 sd 3605.2 p95 6302.3 vs actual 7218.8
- OOS net by year: 2022: 327.5 (n=3), 2023: 1035.9 (n=18), 2024: 943.8 (n=22), 2025: 5210.4 (n=42), 2026: -298.8 (n=27)
- top-3 winners removed: 7218.8 -> 5159.8  (top-3 = 2059.0: ['XANUSDT', '1000000BOBUSDT', 'YBUSDT'])
- concentration: top 10% of trades (11) contribute 6499.8 of gross-positive 19078.1; largest single coin share of |net| = 0.08
- OOS components: alt leg 8939.8, funding -488.7, hedge leg -1013.4, fees -219.0
- liquidity split (day-1 $ volume median 143.6M): low-liquidity half net 2492.6 (n=56), high half 4726.2 (n=56)
- neighbours (one param changed), OOS folds 2+3:
    - `{'rule': 'short_after', 'N': 4, 'H': 14, 'hedge': True}`: n=113 net=9770.1 pf=1.91 folds=[2015.6, 7754.6]
    - `{'rule': 'short_after', 'N': 24, 'H': 1, 'hedge': True}`: n=113 net=1064.9 pf=1.21 folds=[-66.4, 1131.3]
    - `{'rule': 'short_after', 'N': 24, 'H': 3, 'hedge': True}`: n=113 net=4028.7 pf=1.66 folds=[775.2, 3253.4]
    - `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}`: n=113 net=6075.5 pf=1.82 folds=[712.7, 5362.7]
    - `{'rule': 'short_after', 'N': 24, 'H': 14, 'hedge': False}`: n=112 net=8343.6 pf=1.70 folds=[1154.8, 7188.8]

# Hyperliquid listings 2023-2026 (1d): walk-forward  (listings 2023-02-26 -> 2026-07-11; fold starts ['2023-02-26', '2024-04-11', '2025-05-26'])
events per fold: [125, 72, 34] (last fold inclusive of end: 35)

**Walk-forward best (fold 1, by net):** `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': False}`

**OOS folds 2+3:** n= 107 net=  1711.4 pf=1.19 wr=0.54 sharpe=0.69 bps= 159.9 folds=[0.0, 274.3, 1437.0] fold_n=[0, 72, 35]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period)

| params | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {"rule": "short_after", "N": 1, "H": 1, "hedge": false} | 125 | -2732.8 | 0.62 | 0.55 | -218.6 | 232 | -2732.8 | 778.0 | 1082.6 | 0.93 | -37.6 |  |
| {"rule": "short_after", "N": 1, "H": 1, "hedge": true} | 125 | -2204.6 | 0.68 | 0.56 | -176.4 | 232 | -2204.6 | 841.3 | 1091.3 | 0.98 | -11.7 |  |
| {"rule": "short_after", "N": 1, "H": 3, "hedge": false} | 125 | -5270.8 | 0.52 | 0.53 | -421.7 | 232 | -5270.8 | 5823.3 | 2907.2 | 1.21 | 149.1 |  |
| {"rule": "short_after", "N": 1, "H": 3, "hedge": true} | 125 | -3924.6 | 0.61 | 0.54 | -314.0 | 232 | -3924.6 | 5890.9 | 2490.3 | 1.29 | 192.1 |  |
| {"rule": "short_after", "N": 1, "H": 7, "hedge": false} | 125 | -8124.2 | 0.56 | 0.52 | -649.9 | 232 | -8124.2 | 7625.0 | 4465.9 | 1.14 | 171.0 |  |
| {"rule": "short_after", "N": 1, "H": 7, "hedge": true} | 125 | -6213.4 | 0.63 | 0.54 | -497.1 | 232 | -6213.4 | 7805.3 | 3741.9 | 1.20 | 229.9 |  |
| {"rule": "short_after", "N": 1, "H": 14, "hedge": false} | 125 | -12399.7 | 0.48 | 0.49 | -992.0 | 232 | -12399.7 | 4939.7 | 8283.5 | 1.02 | 35.5 |  |
| {"rule": "short_after", "N": 1, "H": 14, "hedge": true} | 125 | -5608.1 | 0.72 | 0.58 | -448.6 | 232 | -5608.1 | 5562.5 | 7196.0 | 1.22 | 308.2 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 1, "contra": false} | 125 | -425.9 | 0.93 | 0.42 | -34.1 | 232 | -425.9 | -795.2 | 2033.0 | 1.07 | 35.0 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 1, "contra": true} | 125 | 198.7 | 1.03 | 0.56 | 15.9 | 232 | 198.7 | 666.4 | -2095.0 | 0.91 | -53.0 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 3, "contra": false} | 125 | 4197.7 | 1.68 | 0.56 | 335.8 | 232 | 4197.7 | 274.3 | 1437.0 | 1.39 | 254.7 | * |
| {"rule": "mom1", "thr": 0.0, "Hh": 3, "contra": true} | 125 | -4427.0 | 0.58 | 0.43 | -354.2 | 232 | -4427.0 | -398.6 | -1497.4 | 0.70 | -272.5 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 1, "contra": false} | 44 | 946.5 | 1.39 | 0.36 | 215.1 | 120 | 946.5 | -1258.3 | 1300.8 | 1.13 | 82.4 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 1, "contra": true} | 44 | -1027.3 | 0.70 | 0.64 | -233.5 | 120 | -1027.3 | 1166.3 | -1345.4 | 0.87 | -100.5 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 3, "contra": false} | 44 | 1621.0 | 1.42 | 0.52 | 368.4 | 120 | 1621.0 | -1209.6 | 357.0 | 1.07 | 64.0 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 3, "contra": true} | 44 | -1703.4 | 0.69 | 0.48 | -387.1 | 120 | -1703.4 | 1121.1 | -400.8 | 0.92 | -81.9 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 1, "hedge": false} | 73 | 582.8 | 1.34 | 0.59 | 79.8 | 88 | 582.8 | 302.5 | -827.1 | 1.02 | 6.6 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 3, "hedge": false} | 73 | -3028.7 | 0.39 | 0.47 | -414.9 | 88 | -3028.7 | 1068.5 | -858.7 | 0.53 | -320.3 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 7, "hedge": false} | 73 | -4722.1 | 0.51 | 0.53 | -646.9 | 88 | -4722.1 | 1122.0 | -1731.5 | 0.55 | -605.9 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 1, "hedge": false} | 100 | -1804.8 | 0.64 | 0.56 | -180.5 | 138 | -1804.8 | 1400.8 | -483.6 | 0.86 | -64.3 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 3, "hedge": false} | 100 | -3910.8 | 0.49 | 0.54 | -391.1 | 138 | -3910.8 | 3142.1 | -118.9 | 0.90 | -64.3 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 7, "hedge": false} | 100 | -6416.7 | 0.54 | 0.54 | -641.7 | 138 | -6416.7 | 4588.6 | -503.2 | 0.86 | -168.9 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 1, "hedge": false} | 9 | 1007.0 | 8.68 | 0.78 | 1118.9 | 50 | 1007.0 | 793.7 | -1085.6 | 1.18 | 143.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 3, "hedge": false} | 9 | 2460.1 | 17.20 | 0.78 | 2733.5 | 50 | 2460.1 | -1727.3 | -1569.5 | 0.88 | -167.3 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 7, "hedge": false} | 9 | 1901.4 | 4.24 | 0.78 | 2112.7 | 50 | 1901.4 | -1715.4 | -2804.2 | 0.75 | -523.6 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 1, "hedge": false} | 3 | 158.1 | 3.13 | 0.67 | 527.0 | 21 | 158.1 | -793.3 | -577.1 | 0.47 | -577.3 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 3, "hedge": false} | 3 | 1497.1 | inf | 1.00 | 4990.5 | 21 | 1497.1 | -1368.5 | -1460.2 | 0.66 | -634.1 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 7, "hedge": false} | 3 | 1395.9 | inf | 1.00 | 4653.0 | 21 | 1395.9 | -2590.4 | -2466.9 | 0.35 | -1743.5 |  |

### Walk-forward pick per rule family (selection on fold 1 only)

| family | fold-1 pick | is_net | OOS n | OOS net | OOS pf | OOS folds |
|---|---|---|---|---|---|---|
| short_after | `{'rule': 'short_after', 'N': 1, 'H': 1, 'hedge': True}` | -2204.6 | 107 | 1932.5 | 1.34 | [841.3, 1091.3] |
| mom1 | `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': False}` | 4197.7 | 107 | 1711.4 | 1.19 | [274.3, 1437.0] |
| wick | `{'rule': 'wick', 'mode': 'near_top_short', 'x': 0.05, 'H': 1, 'hedge': False}` | 582.8 | 15 | -524.6 | 0.53 | [302.5, -827.1] |

### Sanity checks on the walk-forward pick (OOS trades only)

- sign-shuffle (random long/short per trade, fees kept): actual net 1711.4; shuffled mean -75.4 sd 2484.9; p(shuffled >= actual) = 0.243
- random-timing baseline (same rule/hold, entry at random bar >= day 16 after listing, same coins, 200 draws): mean net -201.0 sd 1672.4 p95 2583.4 vs actual 1711.4
- OOS net by year: 2024: -406.7 (n=41), 2025: 2295.5 (n=58), 2026: -177.4 (n=8)
- top-3 winners removed: 1711.4 -> -159.8  (top-3 = 1871.2: ['ASTER', 'TRUMP', 'JELLY'])
- concentration: top 10% of trades (10) contribute 4590.2 of gross-positive 10775.4; largest single coin share of |net| = 0.04
- OOS components: alt leg 1803.7, funding 0.0, hedge leg 0.0, fees -92.3
- liquidity split (day-1 $ volume median 1.9M): low-liquidity half net 1321.3 (n=53), high half 390.0 (n=54)
- neighbours (one param changed), OOS folds 2+3:
    - `{'rule': 'mom1', 'thr': 0.0, 'Hh': 1, 'contra': False}`: n=107 net=1237.8 pf=1.20 folds=[-795.2, 2033.0]
    - `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': True}`: n=107 net=-1896.0 pf=0.83 folds=[-398.6, -1497.4]
    - `{'rule': 'mom1', 'thr': 0.05, 'Hh': 3, 'contra': False}`: n=76 net=-852.6 pf=0.89 folds=[-1209.6, 357.0]

# Cross-sample transfer

Binance fold-1 pick `{'rule': 'short_after', 'N': 24, 'H': 14, 'hedge': True}` -> HL daily analogue `{'rule': 'short_after', 'N': 1, 'H': 14, 'hedge': True}` on ALL HL listings: n= 232 net=  7150.4 pf=1.22 wr=0.66 sharpe=0.97 bps= 308.2 folds=[-5608.1, 5562.5, 7196.0] fold_n=[125, 72, 35]

Capacity: HL listings since 2025 have median day-1 $ volume 25.1M (p25 11.2M); at 1% participation ~$251,348 per event, ~-3.9 listings/month.

# Verdict

Binance (headline, multi-year): **edge**; Hyperliquid daily: **weak**.
