# hl_listing_drift -- results

Fees: Binance UM taker 5.0 bps/side, Hyperliquid taker 4.5 bps/side; funding included (long pays positive rate); hedge = opposite BTC leg of equal notional (fees on both legs, BTC funding ignored). $1000 notional per event.

Binance UM archive: 820 usable listings; dropped: archive_start=11, month_boundary=0, no_data=0, gap_first_48h=1; earliest archive month 2020-01 (symbols starting there are excluded as unverifiable listings: ['ADAUSDT', 'BCHUSDT', 'BTCUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'LINKUSDT', 'LTCUSDT', 'TRXUSDT', 'XLMUSDT', 'XRPUSDT'])
month-boundary starts excluded (could be archive artefacts): []
listings per year: 2020: 70, 2021: 59, 2022: 26, 2023: 99, 2024: 131, 2025: 242, 2026: 193
HL exchange-launch batch (2023-02-26, not listing events) excluded: ['ATOM', 'BTC', 'ETH', 'MATIC']
'fresh' listings (exchange listing <= 3 days after the token's first trade in any of our sources: Binance spot 2018+, Binance UM, HL): Binance 548/820, HL 112/228

Hyperliquid: 228 listings (meta incl. delisted; listing day = first daily candle with volume>0); dropped: never_traded=0, short=0
listings per year: 2023: 96, 2024: 66, 2025: 58, 2026: 8; delisted since: 55; funding series present: 219
HL listings inside the cached 1h window (>= 2026-02-01): ['AZTEC', 'CASHCAT', 'CHIP', 'GRAM'] -> too few for an hourly test; HL rules use daily bars.

## Descriptive: post-listing return paths (Binance UM 1h), excess vs BTC, from listing open  (n=820)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1h | 820 | 1.78 | -0.22 | 1.78 | -0.18 | 3.08 | 0.48 | -0.015 |
| 4h | 820 | 1.91 | -0.35 | 1.96 | -0.36 | 2.64 | 0.47 | -0.096 |
| 24h | 819 | 1.47 | -1.58 | 1.67 | -1.44 | 1.61 | 0.45 | -0.340 |
| 3d | 817 | -0.16 | -3.40 | -0.03 | -3.47 | -0.02 | 0.40 | -0.628 |
| 7d | 814 | -1.30 | -7.38 | -1.67 | -7.30 | -1.06 | 0.38 | -1.000 |
| 14d | 806 | -1.71 | -9.26 | -2.71 | -10.25 | -1.20 | 0.35 | -1.219 |

Post-day-1 drift (Binance UM 1h): from open of bar 24 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +24h | 819 | -1.25 | -2.46 | -2.16 | 0.37 |
| +3d | 816 | -2.40 | -4.38 | -2.75 | 0.35 |
| +7d | 813 | -3.94 | -8.87 | -3.26 | 0.33 |
| +14d | 802 | -1.14 | -12.45 | -0.25 | 0.31 |

## Descriptive: post-listing return paths (Binance UM 1h, FRESH tokens only), excess vs BTC, from listing open  (n=548)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1h | 548 | 2.33 | -0.26 | 2.34 | -0.22 | 2.84 | 0.48 | -0.023 |
| 4h | 548 | 2.76 | -0.28 | 2.80 | -0.37 | 2.64 | 0.46 | -0.121 |
| 24h | 548 | 2.38 | -1.51 | 2.73 | -1.00 | 1.87 | 0.46 | -0.405 |
| 3d | 545 | 0.49 | -2.78 | 0.91 | -2.57 | 0.55 | 0.42 | -0.672 |
| 7d | 542 | -0.79 | -6.02 | -0.73 | -6.06 | -0.34 | 0.41 | -1.019 |
| 14d | 534 | -2.58 | -9.22 | -2.32 | -8.89 | -0.75 | 0.38 | -1.341 |

Post-day-1 drift (Binance UM 1h, FRESH tokens only): from open of bar 24 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +24h | 548 | -1.17 | -2.21 | -1.52 | 0.39 |
| +3d | 545 | -2.63 | -3.75 | -2.21 | 0.36 |
| +7d | 542 | -3.79 | -8.58 | -2.31 | 0.35 |
| +14d | 532 | -0.77 | -12.57 | -0.11 | 0.31 |

## Descriptive: post-listing return paths (Hyperliquid 1d), excess vs BTC, from listing open  (n=228)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1d | 228 | 0.92 | -0.71 | 0.96 | -0.78 | 0.59 | 0.45 | -0.155 |
| 3d | 228 | 0.04 | -3.13 | -0.20 | -3.84 | -0.09 | 0.38 | -0.412 |
| 7d | 228 | 0.34 | -7.50 | -0.26 | -7.19 | -0.09 | 0.37 | -0.265 |
| 14d | 228 | -0.65 | -7.86 | -3.19 | -12.08 | -0.94 | 0.33 | -0.457 |

Post-day-1 drift (Hyperliquid 1d): from open of bar 1 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +1d | 228 | -0.14 | -2.74 | -0.12 | 0.35 |
| +3d | 228 | -2.28 | -4.04 | -1.54 | 0.36 |
| +7d | 228 | -2.55 | -9.12 | -1.07 | 0.35 |
| +14d | 228 | -3.50 | -12.36 | -1.09 | 0.34 |

## Descriptive: post-listing return paths (Hyperliquid 1d, FRESH tokens only), excess vs BTC, from listing open  (n=112)

| horizon | n | mean raw % | median raw % | mean excess % | median excess % | t(excess) | share>0 | mean cum funding % (long pays) |
|---|---|---|---|---|---|---|---|---|
| 1d | 112 | 1.08 | -0.66 | 1.16 | -2.17 | 0.38 | 0.44 | 0.058 |
| 3d | 112 | 1.18 | -4.49 | 0.86 | -6.18 | 0.20 | 0.41 | 0.027 |
| 7d | 112 | 4.43 | -8.94 | 2.88 | -10.33 | 0.52 | 0.40 | 0.537 |
| 14d | 112 | 2.08 | -11.93 | -0.60 | -13.21 | -0.10 | 0.35 | 0.815 |

Post-day-1 drift (Hyperliquid 1d, FRESH tokens only): from open of bar 1 to later, excess vs BTC

| horizon after day 1 | n | mean excess % | median excess % | t | share>0 |
|---|---|---|---|---|---|
| +1d | 112 | 2.25 | -1.48 | 0.96 | 0.42 |
| +3d | 112 | -1.43 | -4.25 | -0.54 | 0.40 |
| +7d | 112 | -1.70 | -11.75 | -0.39 | 0.35 |
| +14d | 112 | -2.49 | -13.24 | -0.46 | 0.35 |

# Binance UM listings 2019-2026 (1h): walk-forward  (listings 2020-02-03 -> 2026-07-29; fold starts ['2020-02-03', '2022-04-02', '2024-05-31'])
events per fold: [138, 151, 528] (last fold inclusive of end: 531)

**Walk-forward best (fold 1, by net):** `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}`

**OOS folds 2+3:** n= 676 net= 18004.7 pf=1.26 wr=0.66 sharpe=1.89 bps= 266.3 folds=[0.0, 8099.6, 9905.0] fold_n=[0, 150, 526]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period)

| params | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {"rule": "short_after", "N": 4, "H": 1, "hedge": false} | 138 | -788.3 | 0.91 | 0.57 | -57.1 | 820 | -788.3 | 1043.0 | 4917.2 | 1.10 | 63.1 |  |
| {"rule": "short_after", "N": 4, "H": 1, "hedge": true} | 137 | -477.2 | 0.94 | 0.53 | -34.8 | 819 | -477.2 | 1289.9 | 2625.7 | 1.07 | 42.0 |  |
| {"rule": "short_after", "N": 4, "H": 3, "hedge": false} | 138 | 5162.0 | 1.67 | 0.64 | 374.1 | 817 | 5162.0 | 3148.4 | 6603.8 | 1.23 | 182.5 |  |
| {"rule": "short_after", "N": 4, "H": 3, "hedge": true} | 138 | 5357.1 | 1.78 | 0.67 | 388.2 | 817 | 5357.1 | 3598.6 | 3944.0 | 1.20 | 157.9 |  |
| {"rule": "short_after", "N": 4, "H": 7, "hedge": false} | 138 | 4971.9 | 1.36 | 0.64 | 360.3 | 814 | 4971.9 | 7406.2 | 3550.8 | 1.17 | 195.7 |  |
| {"rule": "short_after", "N": 4, "H": 7, "hedge": true} | 137 | 5642.4 | 1.46 | 0.66 | 411.9 | 813 | 5642.4 | 10484.8 | 2989.4 | 1.21 | 235.1 |  |
| {"rule": "short_after", "N": 4, "H": 14, "hedge": false} | 138 | 290.3 | 1.01 | 0.62 | 21.0 | 806 | 290.3 | 4836.1 | 4885.9 | 1.08 | 124.2 |  |
| {"rule": "short_after", "N": 4, "H": 14, "hedge": true} | 137 | 5086.2 | 1.28 | 0.66 | 371.3 | 805 | 5086.2 | 9988.7 | 2971.5 | 1.15 | 224.2 |  |
| {"rule": "short_after", "N": 24, "H": 1, "hedge": false} | 138 | 1864.9 | 1.34 | 0.59 | 135.1 | 820 | 1864.9 | 805.0 | 4204.9 | 1.18 | 83.8 |  |
| {"rule": "short_after", "N": 24, "H": 1, "hedge": true} | 137 | 2401.0 | 1.50 | 0.64 | 175.3 | 819 | 2401.0 | 973.1 | 3765.8 | 1.19 | 87.2 |  |
| {"rule": "short_after", "N": 24, "H": 3, "hedge": false} | 138 | 6118.3 | 1.93 | 0.67 | 443.4 | 817 | 6118.3 | 1648.7 | 7380.1 | 1.28 | 185.4 |  |
| {"rule": "short_after", "N": 24, "H": 3, "hedge": true} | 137 | 5814.7 | 2.00 | 0.66 | 424.4 | 816 | 5814.7 | 2150.8 | 7001.2 | 1.28 | 183.4 |  |
| {"rule": "short_after", "N": 24, "H": 7, "hedge": false} | 138 | 5703.9 | 1.46 | 0.69 | 413.3 | 814 | 5703.9 | 4889.3 | 10437.1 | 1.26 | 258.4 |  |
| {"rule": "short_after", "N": 24, "H": 7, "hedge": true} | 137 | 6633.8 | 1.61 | 0.72 | 484.2 | 813 | 6633.8 | 8099.6 | 9905.0 | 1.31 | 303.1 | * |
| {"rule": "short_after", "N": 24, "H": 14, "hedge": false} | 137 | -2102.2 | 0.91 | 0.64 | -153.4 | 803 | -2102.2 | 1415.0 | -8092.8 | 0.94 | -109.3 |  |
| {"rule": "short_after", "N": 24, "H": 14, "hedge": true} | 136 | 3658.5 | 1.19 | 0.70 | 269.0 | 802 | 3658.5 | 6679.9 | -10024.8 | 1.00 | 3.9 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 4, "contra": false} | 138 | -473.7 | 0.87 | 0.51 | -34.3 | 820 | -473.7 | -1412.1 | 3577.7 | 1.05 | 20.6 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 4, "contra": true} | 138 | 198.1 | 1.06 | 0.46 | 14.4 | 820 | 198.1 | 1110.4 | -4641.5 | 0.90 | -40.6 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 24, "contra": false} | 138 | -825.5 | 0.90 | 0.50 | -59.8 | 820 | -825.5 | -2386.6 | 8584.4 | 1.09 | 65.5 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 24, "contra": true} | 138 | 549.3 | 1.07 | 0.49 | 39.8 | 820 | 549.3 | 2087.5 | -9645.7 | 0.89 | -85.5 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 4, "contra": false} | 101 | -567.1 | 0.81 | 0.46 | -56.1 | 553 | -567.1 | -1702.4 | 3843.0 | 1.06 | 28.5 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 4, "contra": true} | 101 | 365.2 | 1.15 | 0.51 | 36.2 | 553 | 365.2 | 1483.0 | -4527.0 | 0.90 | -48.4 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 24, "contra": false} | 101 | -429.3 | 0.94 | 0.50 | -42.5 | 553 | -429.3 | -2786.4 | 7672.7 | 1.10 | 80.6 |  |
| {"rule": "mom1", "thr": 0.02, "Hh": 24, "contra": true} | 101 | 227.2 | 1.03 | 0.50 | 22.5 | 553 | 227.2 | 2568.7 | -8356.6 | 0.89 | -100.6 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 4, "contra": false} | 52 | -240.3 | 0.86 | 0.42 | -46.2 | 365 | -240.3 | -1219.1 | 1791.6 | 1.02 | 9.1 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 4, "contra": true} | 52 | 136.7 | 1.09 | 0.54 | 26.3 | 365 | 136.7 | 1099.8 | -2298.7 | 0.95 | -29.1 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 24, "contra": false} | 52 | -203.5 | 0.95 | 0.50 | -39.1 | 365 | -203.5 | -3219.9 | 3455.0 | 1.00 | 0.9 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 24, "contra": true} | 52 | 99.5 | 1.03 | 0.50 | 19.1 | 365 | 99.5 | 3102.2 | -3959.7 | 0.98 | -20.8 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 1, "hedge": false} | 10 | -434.0 | 0.29 | 0.50 | -434.0 | 53 | -434.0 | 561.4 | 12.0 | 1.09 | 26.3 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 3, "hedge": false} | 10 | -545.7 | 0.51 | 0.60 | -545.7 | 53 | -545.7 | 397.9 | 273.9 | 1.05 | 23.8 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.02, "H": 7, "hedge": false} | 10 | -339.1 | 0.75 | 0.60 | -339.1 | 52 | -339.1 | 917.1 | -229.2 | 1.12 | 67.1 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 1, "hedge": false} | 33 | 220.0 | 1.24 | 0.67 | 66.7 | 175 | 220.0 | 55.7 | -472.6 | 0.96 | -11.2 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 3, "hedge": false} | 33 | -25.5 | 0.99 | 0.58 | -7.7 | 174 | -25.5 | 739.3 | -599.7 | 1.02 | 6.6 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 7, "hedge": false} | 33 | 453.3 | 1.14 | 0.64 | 137.3 | 171 | 453.3 | 1797.3 | -2506.8 | 0.98 | -15.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 1, "hedge": false} | 41 | -566.6 | 0.79 | 0.56 | -138.2 | 332 | -566.6 | -1024.6 | -8206.7 | 0.65 | -295.1 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 3, "hedge": false} | 41 | -3997.6 | 0.25 | 0.29 | -975.0 | 332 | -3997.6 | -2930.0 | -12389.0 | 0.53 | -581.8 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 7, "hedge": false} | 41 | -3961.2 | 0.42 | 0.32 | -966.1 | 332 | -3961.2 | -3633.9 | -16574.9 | 0.58 | -728.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 1, "hedge": false} | 14 | 492.3 | 1.85 | 0.79 | 351.7 | 146 | 492.3 | 164.8 | -5045.4 | 0.68 | -300.6 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 3, "hedge": false} | 14 | -1501.0 | 0.14 | 0.29 | -1072.1 | 146 | -1501.0 | -622.8 | -7585.0 | 0.52 | -665.0 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 7, "hedge": false} | 14 | -1266.0 | 0.43 | 0.29 | -904.3 | 146 | -1266.0 | 1215.9 | -9712.9 | 0.66 | -668.7 |  |

### Walk-forward pick per rule family (selection on fold 1 only)

| family | fold-1 pick | is_net | OOS n | OOS net | OOS pf | OOS folds |
|---|---|---|---|---|---|---|
| short_after | `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}` | 6633.8 | 676 | 18004.7 | 1.26 | [8099.6, 9905.0] |
| mom1 | `{'rule': 'mom1', 'thr': 0.0, 'Hh': 24, 'contra': True}` | 549.3 | 682 | -7558.2 | 0.86 | [2087.5, -9645.7] |
| wick | `{'rule': 'wick', 'mode': 'deep_wick_long', 'x': 0.4, 'H': 1, 'hedge': False}` | 492.3 | 132 | -4880.6 | 0.62 | [164.8, -5045.4] |

### Sanity checks on the walk-forward pick (OOS trades only)

- sign-shuffle (random long/short per trade, fees kept): actual net 18004.7; shuffled mean -1357.4 sd 9644.1; p(shuffled >= actual) = 0.020
- random-timing baseline (same rule/hold, entry at random bar >= day 16 after listing, same coins, 200 draws, avg n=651): mean net 2002.5 sd 5332.1 p95 10856.0 vs actual 18004.7
- independent decisions: 414 distinct entry days among 676 OOS trades (Binance lists several perps on one day)
- OOS net by year: 2022: 2092.7 (n=17), 2023: 4268.8 (n=99), 2024: 3569.4 (n=131), 2025: 7515.9 (n=240), 2026: 557.9 (n=189)
- top-3 winners removed: 18004.7 -> 16034.8  (top-3 = 1969.9: ['SXTUSDT', 'YBUSDT', 'BROCCOLIF3BUSDT'])
- concentration: top 10% of trades (67) contribute 30594.1 of gross-positive 86291.6; largest single coin share of |net| = 0.02
- OOS components: alt leg 22128.4, funding -6137.0, hedge leg 3356.0, fees -1342.6
- liquidity split (day-1 $ volume median 105.0M): low-liquidity half net 5086.3 (n=338), high half 12918.4 (n=338)
- fresh vs established: fresh-token listings net 11579.2 (n=518, pf=1.20), established-coin listings net 6425.4 (n=158, pf=1.60)
- full-period (incl. fold 1) net by year for the pick: 2020: 6415 (n=70, avg 92), 2021: 1647 (n=57, avg 29), 2022: 664 (n=27, avg 25), 2023: 4269 (n=99, avg 43), 2024: 3569 (n=131, avg 27), 2025: 7516 (n=240, avg 31), 2026: 558 (n=189, avg 3)
- neighbours (one param changed), OOS folds 2+3:
    - `{'rule': 'short_after', 'N': 4, 'H': 7, 'hedge': True}`: n=676 net=13474.2 pf=1.17 folds=[10484.8, 2989.4]
    - `{'rule': 'short_after', 'N': 24, 'H': 1, 'hedge': True}`: n=682 net=4738.9 pf=1.14 folds=[973.1, 3765.8]
    - `{'rule': 'short_after', 'N': 24, 'H': 3, 'hedge': True}`: n=679 net=9152.0 pf=1.20 folds=[2150.8, 7001.2]
    - `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': False}`: n=676 net=15326.4 pf=1.22 folds=[4889.3, 10437.1]
    - `{'rule': 'short_after', 'N': 24, 'H': 14, 'hedge': True}`: n=666 net=-3344.9 pf=0.97 folds=[6679.9, -10024.8]

# Hyperliquid listings 2023-2026 (1d): walk-forward  (listings 2023-03-04 -> 2026-07-11; fold starts ['2023-03-04', '2024-04-15', '2025-05-28'])
events per fold: [121, 73, 33] (last fold inclusive of end: 34)

**Walk-forward best (fold 1, by net):** `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': False}`

**OOS folds 2+3:** n= 107 net=  1299.2 pf=1.14 wr=0.54 sharpe=0.52 bps= 121.4 folds=[0.0, -14.6, 1313.8] fold_n=[0, 72, 35]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period)

| params | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {"rule": "short_after", "N": 1, "H": 1, "hedge": false} | 121 | -2702.7 | 0.62 | 0.55 | -223.4 | 228 | -2702.7 | 646.6 | 975.0 | 0.92 | -47.4 |  |
| {"rule": "short_after", "N": 1, "H": 1, "hedge": true} | 121 | -2157.2 | 0.68 | 0.57 | -178.3 | 228 | -2157.2 | 709.8 | 983.6 | 0.96 | -20.3 |  |
| {"rule": "short_after", "N": 1, "H": 3, "hedge": false} | 121 | -5076.0 | 0.53 | 0.55 | -419.5 | 228 | -5076.0 | 5559.7 | 2716.4 | 1.19 | 140.4 |  |
| {"rule": "short_after", "N": 1, "H": 3, "hedge": true} | 121 | -3738.5 | 0.63 | 0.55 | -309.0 | 228 | -3738.5 | 5627.4 | 2299.5 | 1.27 | 183.7 |  |
| {"rule": "short_after", "N": 1, "H": 7, "hedge": false} | 121 | -8003.0 | 0.57 | 0.51 | -661.4 | 228 | -8003.0 | 7347.1 | 4187.5 | 1.12 | 154.9 |  |
| {"rule": "short_after", "N": 1, "H": 7, "hedge": true} | 121 | -5896.9 | 0.64 | 0.55 | -487.3 | 228 | -5896.9 | 7527.4 | 3463.5 | 1.19 | 223.4 |  |
| {"rule": "short_after", "N": 1, "H": 14, "hedge": false} | 121 | -11920.3 | 0.49 | 0.49 | -985.1 | 228 | -11920.3 | 4767.5 | 7446.7 | 1.01 | 12.9 |  |
| {"rule": "short_after", "N": 1, "H": 14, "hedge": true} | 121 | -4859.1 | 0.75 | 0.59 | -401.6 | 228 | -4859.1 | 5390.3 | 6359.3 | 1.21 | 302.2 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 1, "contra": false} | 121 | -277.0 | 0.95 | 0.44 | -22.9 | 228 | -277.0 | -972.3 | 1977.7 | 1.06 | 31.9 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 1, "contra": true} | 121 | 57.0 | 1.01 | 0.54 | 4.7 | 228 | 57.0 | 843.5 | -2039.7 | 0.91 | -50.0 |  |
| {"rule": "mom1", "thr": 0.0, "Hh": 3, "contra": false} | 121 | 4368.8 | 1.72 | 0.58 | 361.1 | 228 | 4368.8 | -14.6 | 1313.8 | 1.37 | 248.6 | * |
| {"rule": "mom1", "thr": 0.0, "Hh": 3, "contra": true} | 121 | -4590.9 | 0.57 | 0.41 | -379.4 | 228 | -4590.9 | -109.7 | -1374.2 | 0.71 | -266.4 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 1, "contra": false} | 44 | 1041.8 | 1.44 | 0.39 | 236.8 | 120 | 1041.8 | -1437.7 | 1254.2 | 1.11 | 71.5 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 1, "contra": true} | 44 | -1122.5 | 0.67 | 0.61 | -255.1 | 120 | -1122.5 | 1345.7 | -1298.7 | 0.88 | -89.6 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 3, "contra": false} | 44 | 1770.0 | 1.47 | 0.55 | 402.3 | 120 | 1770.0 | -1512.4 | 245.4 | 1.04 | 41.9 |  |
| {"rule": "mom1", "thr": 0.05, "Hh": 3, "contra": true} | 44 | -1852.4 | 0.67 | 0.45 | -421.0 | 120 | -1852.4 | 1423.8 | -289.2 | 0.94 | -59.8 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 1, "hedge": false} | 69 | 541.7 | 1.32 | 0.57 | 78.5 | 84 | 541.7 | 311.8 | -801.4 | 1.02 | 6.2 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 3, "hedge": false} | 69 | -3001.2 | 0.40 | 0.48 | -435.0 | 84 | -3001.2 | 1086.1 | -809.4 | 0.54 | -324.3 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.05, "H": 7, "hedge": false} | 69 | -4878.5 | 0.49 | 0.51 | -707.0 | 84 | -4878.5 | 1139.1 | -1649.3 | 0.54 | -641.5 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 1, "hedge": false} | 96 | -1799.6 | 0.64 | 0.54 | -187.5 | 134 | -1799.6 | 1434.5 | -490.4 | 0.86 | -63.8 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 3, "hedge": false} | 96 | -3798.2 | 0.49 | 0.55 | -395.7 | 134 | -3798.2 | 3228.6 | -132.3 | 0.92 | -52.4 |  |
| {"rule": "wick", "mode": "near_top_short", "x": 0.1, "H": 7, "hedge": false} | 96 | -6451.6 | 0.53 | 0.53 | -672.0 | 134 | -6451.6 | 4717.2 | -527.5 | 0.86 | -168.8 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 1, "hedge": false} | 9 | 933.5 | 6.98 | 0.67 | 1037.2 | 50 | 933.5 | 847.2 | -1035.4 | 1.19 | 149.1 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 3, "hedge": false} | 9 | 2310.9 | 12.50 | 0.67 | 2567.7 | 50 | 2310.9 | -1491.2 | -1516.1 | 0.89 | -139.3 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.2, "H": 7, "hedge": false} | 9 | 1657.0 | 3.11 | 0.78 | 1841.1 | 50 | 1657.0 | -1332.8 | -2766.6 | 0.76 | -488.5 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 1, "hedge": false} | 3 | 158.1 | 3.13 | 0.67 | 527.0 | 21 | 158.1 | -800.4 | -523.7 | 0.49 | -555.2 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 3, "hedge": false} | 3 | 1497.1 | inf | 1.00 | 4990.5 | 21 | 1497.1 | -1281.8 | -1382.6 | 0.69 | -555.8 |  |
| {"rule": "wick", "mode": "deep_wick_long", "x": 0.4, "H": 7, "hedge": false} | 3 | 1395.9 | inf | 1.00 | 4653.0 | 21 | 1395.9 | -2493.3 | -2366.8 | 0.36 | -1649.6 |  |

### Walk-forward pick per rule family (selection on fold 1 only)

| family | fold-1 pick | is_net | OOS n | OOS net | OOS pf | OOS folds |
|---|---|---|---|---|---|---|
| short_after | `{'rule': 'short_after', 'N': 1, 'H': 1, 'hedge': True}` | -2157.2 | 107 | 1693.4 | 1.29 | [709.8, 983.6] |
| mom1 | `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': False}` | 4368.8 | 107 | 1299.2 | 1.14 | [-14.6, 1313.8] |
| wick | `{'rule': 'wick', 'mode': 'near_top_short', 'x': 0.05, 'H': 1, 'hedge': False}` | 541.7 | 15 | -489.6 | 0.55 | [311.8, -801.4] |

### Sanity checks on the walk-forward pick (OOS trades only)

- sign-shuffle (random long/short per trade, fees kept): actual net 1299.2; shuffled mean -61.2 sd 2472.2; p(shuffled >= actual) = 0.285
- random-timing baseline (same rule/hold, entry at random bar >= day 16 after listing, same coins, 200 draws, avg n=107): mean net -150.1 sd 1623.3 p95 2294.3 vs actual 1299.2
- independent decisions: 93 distinct entry days among 107 OOS trades (Binance lists several perps on one day)
- OOS net by year: 2024: -366.5 (n=41), 2025: 1933.8 (n=58), 2026: -268.1 (n=8)
- top-3 winners removed: 1299.2 -> -509.1  (top-3 = 1808.3: ['ASTER', 'TRUMP', 'JELLY'])
- concentration: top 10% of trades (10) contribute 4504.0 of gross-positive 10492.7; largest single coin share of |net| = 0.05
- OOS components: alt leg 1803.7, funding -412.1, hedge leg 0.0, fees -92.3
- liquidity split (day-1 $ volume median 2.1M): low-liquidity half net 1305.9 (n=53), high half -6.6 (n=54)
- fresh vs established: fresh-token listings net 2430.2 (n=65, pf=1.43), established-coin listings net -1131.0 (n=42, pf=0.68)
- full-period (incl. fold 1) net by year for the pick: 2023: 2718 (n=96, avg 28), 2024: 1284 (n=66, avg 19), 2025: 1934 (n=58, avg 33), 2026: -268 (n=8, avg -34)
- neighbours (one param changed), OOS folds 2+3:
    - `{'rule': 'mom1', 'thr': 0.0, 'Hh': 1, 'contra': False}`: n=107 net=1005.4 pf=1.16 folds=[-972.3, 1977.7]
    - `{'rule': 'mom1', 'thr': 0.0, 'Hh': 3, 'contra': True}`: n=107 net=-1483.9 pf=0.86 folds=[-109.7, -1374.2]
    - `{'rule': 'mom1', 'thr': 0.05, 'Hh': 3, 'contra': False}`: n=76 net=-1267.0 pf=0.84 folds=[-1512.4, 245.4]

# Cross-sample transfer

Binance fold-1 pick `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}` -> HL daily analogue `{'rule': 'short_after', 'N': 1, 'H': 7, 'hedge': True}` on ALL HL listings: n= 228 net=  5093.9 pf=1.19 wr=0.63 sharpe=0.93 bps= 223.4 folds=[-5896.9, 7527.4, 3463.5] fold_n=[121, 72, 35]

Capacity: HL listings since 2025 have median day-1 $ volume 25.1M (p25 11.2M); at 1% participation ~$251,348 per event, ~3.6 listings/month.

# Verdict

Binance (headline, multi-year): **edge**; Hyperliquid daily: **weak**.
