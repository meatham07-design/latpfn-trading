# flush_reversal_long -- results

Loaded 174 coins with 1h candles (50 cached top-50 + 124 ext).
Point-in-time top-50 by trailing-30d USD volume: 88 coins ever members; 39 not in the cached snapshot universe: ['ACE', 'ALGO', 'APE', 'APT', 'ARB', 'AXS', 'AZTEC', 'BCH', 'BERA', 'BIO', 'BLUR', 'DASH', 'DOT', 'DYDX', 'EIGEN', 'ICP', 'KAITO', 'LDO', 'MEGA', 'MET', 'MORPHO', 'NIL', 'OP', 'ORDI', 'PENDLE', 'POL', 'RENDER', 'RESOLV', 'SEI', 'SKR', 'STABLE', 'STRK', 'VIRTUAL', 'WLFI', 'XLM', 'ZK', 'ZORA', 'kBONK', 'kSHIB']
Funding series available for 88/88 universe coins; missing (funding=0 assumed): []

## Descriptive: signal counts and raw forward returns (1h, Y=4,V=6, coin-specific vs market-wide)

- coin-specific (<3 others): n by fold [31, 32, 43]; mean raw open->open(12) return bps by fold [np.float64(-122.9), np.float64(71.5), np.float64(158.1)]
- market-wide (>=3 others): n by fold [56, 38, 77]; mean raw open->open(12) return bps by fold [np.float64(338.6), np.float64(64.8), np.float64(110.9)]

## Fill diagnostic (1h, Y=4,V=6,H=12, arm B): all signals taker-at-open vs filled-at-limit subsets

| entry | n | mean gross bps | mean net bps | fold nets |
|---|---|---|---|---|
| taker at open (all signals) | 106 | 49.8 | 41.3 | [-404.1, 203.2, 638.4] |
| maker bid at close-0.0xrange (filled only) | 100 | 42.2 | 36.2 | [-389.7, 175.0, 577.3] |
| maker bid at close-0.25xrange (filled only) | 27 | -46.4 | -52.0 | [-184.1, 109.2, -65.5] |
| maker bid at close-0.5xrange (filled only) | 11 | 97.4 | 91.4 | [29.0, 14.2, 57.3] |

## 1h arm A  (data 2026-01-31 -> 2026-08-27; fold starts ['2026-01-31', '2026-04-10', '2026-06-19'])

**Walk-forward best (fold 1):** `{'Y': 4, 'V': 4, 'bid': 0.25, 'H': 12}`

**OOS folds 2+3:** n=  26 net=  -141.5 pf=0.72 wr=0.54 sharpe=-0.56 bps= -54.4 folds=[0.0, 136.6, -278.2] fold_n=[0, 11, 15]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets, full period)

| Y | V | bid | H | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 0.0 | 12 | 69 | -799.7 | 0.55 | 0.43 | -115.9 | 228 | -799.7 | 28.1 | -56.9 | 0.82 | -36.3 |  |
| 3 | 4 | 0.0 | 24 | 69 | -702.3 | 0.62 | 0.52 | -101.8 | 227 | -702.3 | -211.5 | -1.5 | 0.82 | -40.3 |  |
| 3 | 4 | 0.25 | 12 | 26 | -198.7 | 0.67 | 0.46 | -76.4 | 79 | -198.7 | 291.1 | -24.6 | 1.04 | 8.6 |  |
| 3 | 4 | 0.25 | 24 | 26 | -150.3 | 0.77 | 0.62 | -57.8 | 79 | -150.3 | 148.7 | 62.4 | 1.04 | 7.7 |  |
| 3 | 8 | 0.0 | 12 | 51 | -508.5 | 0.60 | 0.45 | -99.7 | 171 | -508.5 | 55.1 | 321.8 | 0.96 | -7.7 |  |
| 3 | 8 | 0.0 | 24 | 51 | -508.8 | 0.64 | 0.55 | -99.8 | 171 | -508.8 | -145.1 | 245.3 | 0.89 | -23.9 |  |
| 3 | 8 | 0.25 | 12 | 19 | -256.1 | 0.49 | 0.37 | -134.8 | 57 | -256.1 | 331.6 | 63.0 | 1.16 | 24.3 |  |
| 3 | 8 | 0.25 | 24 | 19 | -367.1 | 0.43 | 0.47 | -193.2 | 57 | -367.1 | 154.1 | 94.8 | 0.90 | -20.7 |  |
| 4 | 4 | 0.0 | 12 | 33 | -689.2 | 0.35 | 0.33 | -208.9 | 111 | -689.2 | 218.2 | -103.8 | 0.75 | -51.8 |  |
| 4 | 4 | 0.0 | 24 | 33 | -529.8 | 0.48 | 0.48 | -160.5 | 111 | -529.8 | 278.0 | -89.7 | 0.86 | -30.8 |  |
| 4 | 4 | 0.25 | 12 | 12 | -106.9 | 0.63 | 0.42 | -89.1 | 38 | -106.9 | 136.6 | -278.2 | 0.69 | -65.4 | * |
| 4 | 4 | 0.25 | 24 | 12 | -108.9 | 0.67 | 0.67 | -90.8 | 38 | -108.9 | 212.0 | -323.6 | 0.75 | -58.1 |  |
| 4 | 8 | 0.0 | 12 | 29 | -388.6 | 0.52 | 0.41 | -134.0 | 95 | -388.6 | 206.5 | 233.0 | 1.03 | 5.4 |  |
| 4 | 8 | 0.0 | 24 | 29 | -327.5 | 0.60 | 0.55 | -112.9 | 95 | -327.5 | 340.0 | 238.7 | 1.14 | 26.4 |  |
| 4 | 8 | 0.25 | 12 | 8 | -44.0 | 0.77 | 0.50 | -55.0 | 26 | -44.0 | 174.7 | 11.5 | 1.45 | 54.7 |  |
| 4 | 8 | 0.25 | 24 | 8 | -18.0 | 0.91 | 0.75 | -22.5 | 26 | -18.0 | 250.0 | -6.6 | 1.71 | 86.7 |  |
| 5 | 4 | 0.0 | 12 | 23 | -390.9 | 0.45 | 0.48 | -169.9 | 72 | -390.9 | -149.8 | -55.2 | 0.61 | -82.8 |  |
| 5 | 4 | 0.0 | 24 | 23 | -458.1 | 0.40 | 0.52 | -199.2 | 72 | -458.1 | -195.0 | 44.6 | 0.65 | -84.5 |  |
| 5 | 4 | 0.25 | 12 | 8 | -49.6 | 0.73 | 0.50 | -62.0 | 25 | -49.6 | 65.1 | -223.9 | 0.64 | -83.4 |  |
| 5 | 4 | 0.25 | 24 | 8 | -46.3 | 0.77 | 0.75 | -57.8 | 25 | -46.3 | 111.3 | -261.4 | 0.68 | -78.5 |  |
| 5 | 8 | 0.0 | 12 | 20 | -330.1 | 0.47 | 0.50 | -165.0 | 59 | -330.1 | -30.5 | 175.9 | 0.83 | -31.3 |  |
| 5 | 8 | 0.0 | 24 | 20 | -410.2 | 0.40 | 0.55 | -205.1 | 59 | -410.2 | -40.4 | 276.8 | 0.86 | -29.5 |  |
| 5 | 8 | 0.25 | 12 | 6 | -62.1 | 0.63 | 0.50 | -103.5 | 18 | -62.1 | 110.7 | 8.9 | 1.22 | 31.9 |  |
| 5 | 8 | 0.25 | 24 | 6 | -78.3 | 0.60 | 0.67 | -130.5 | 18 | -78.3 | 156.8 | -9.2 | 1.23 | 38.5 |  |

OOS by exit reason:

| reason | n | net | avg bps |
|---|---|---|---|
| stop | 3 | -303.9 | -1013.1 |
| target | 12 | 342.0 | 285.0 |
| time | 11 | -179.6 | -163.2 |

OOS funding paid total = -12.64 USD; fees only = 11.84 USD; avg hold = 7.7 h

## 1h arm B  (data 2026-01-31 -> 2026-08-27; fold starts ['2026-01-31', '2026-04-10', '2026-06-19'])

**Walk-forward best (fold 1):** `{'Y': 3, 'V': 4, 'bid': 0.25, 'H': 24}`

**OOS folds 2+3:** n=  52 net=  -593.2 pf=0.67 wr=0.44 sharpe=-0.98 bps=-114.1 folds=[0.0, -217.6, -375.6] fold_n=[0, 27, 25]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets, full period)

| Y | V | bid | H | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 0.0 | 12 | 69 | -843.9 | 0.55 | 0.36 | -122.3 | 226 | -843.9 | 18.8 | 129.6 | 0.86 | -30.8 |  |
| 3 | 4 | 0.0 | 24 | 68 | -380.3 | 0.81 | 0.41 | -55.9 | 223 | -380.3 | -523.5 | -227.2 | 0.82 | -50.7 |  |
| 3 | 4 | 0.25 | 12 | 25 | -388.1 | 0.42 | 0.28 | -155.2 | 77 | -388.1 | 72.1 | -411.6 | 0.62 | -94.5 |  |
| 3 | 4 | 0.25 | 24 | 25 | 273.4 | 1.41 | 0.52 | 109.4 | 77 | 273.4 | -217.6 | -375.6 | 0.87 | -41.5 | * |
| 3 | 8 | 0.0 | 12 | 51 | -534.9 | 0.61 | 0.37 | -104.9 | 170 | -534.9 | 80.4 | 855.0 | 1.12 | 23.6 |  |
| 3 | 8 | 0.0 | 24 | 50 | 12.3 | 1.01 | 0.46 | 2.5 | 169 | 12.3 | -253.1 | 434.9 | 1.05 | 11.5 |  |
| 3 | 8 | 0.25 | 12 | 18 | -384.6 | 0.31 | 0.22 | -213.7 | 56 | -384.6 | 155.1 | 122.2 | 0.90 | -19.2 |  |
| 3 | 8 | 0.25 | 24 | 18 | -20.1 | 0.97 | 0.33 | -11.2 | 56 | -20.1 | -48.5 | 191.7 | 1.08 | 22.0 |  |
| 4 | 4 | 0.0 | 12 | 33 | -526.2 | 0.52 | 0.27 | -159.5 | 111 | -526.2 | 180.4 | 261.0 | 0.97 | -7.6 |  |
| 4 | 4 | 0.0 | 24 | 32 | -323.8 | 0.71 | 0.44 | -101.2 | 110 | -323.8 | 261.5 | -38.5 | 0.96 | -9.2 |  |
| 4 | 4 | 0.25 | 12 | 11 | -266.6 | 0.25 | 0.09 | -242.3 | 37 | -266.6 | 137.6 | -340.5 | 0.48 | -126.9 |  |
| 4 | 4 | 0.25 | 24 | 11 | -128.3 | 0.62 | 0.55 | -116.7 | 37 | -128.3 | 229.9 | -367.7 | 0.73 | -71.9 |  |
| 4 | 8 | 0.0 | 12 | 29 | -232.4 | 0.73 | 0.34 | -80.1 | 95 | -232.4 | 163.8 | 516.1 | 1.27 | 47.1 |  |
| 4 | 8 | 0.0 | 24 | 28 | 34.5 | 1.04 | 0.50 | 12.3 | 94 | 34.5 | 299.0 | 95.2 | 1.22 | 45.6 |  |
| 4 | 8 | 0.25 | 12 | 7 | -160.0 | 0.36 | 0.14 | -228.5 | 25 | -160.0 | 98.8 | -60.6 | 0.71 | -48.7 |  |
| 4 | 8 | 0.25 | 24 | 7 | -19.7 | 0.91 | 0.57 | -28.1 | 25 | -19.7 | 203.2 | -140.8 | 1.10 | 17.1 |  |
| 5 | 4 | 0.0 | 12 | 23 | -377.7 | 0.50 | 0.39 | -164.2 | 72 | -377.7 | -298.8 | 68.2 | 0.63 | -84.5 |  |
| 5 | 4 | 0.0 | 24 | 22 | -493.2 | 0.42 | 0.45 | -224.2 | 71 | -493.2 | -316.9 | -1.4 | 0.58 | -114.3 |  |
| 5 | 4 | 0.25 | 12 | 8 | -109.6 | 0.54 | 0.25 | -136.9 | 25 | -109.6 | 74.5 | -211.8 | 0.61 | -98.8 |  |
| 5 | 4 | 0.25 | 24 | 8 | -37.4 | 0.82 | 0.62 | -46.8 | 25 | -37.4 | 72.0 | -363.4 | 0.52 | -131.5 |  |
| 5 | 8 | 0.0 | 12 | 20 | -317.2 | 0.52 | 0.40 | -158.6 | 59 | -317.2 | -179.6 | 289.7 | 0.82 | -35.1 |  |
| 5 | 8 | 0.0 | 24 | 19 | -451.3 | 0.41 | 0.47 | -237.5 | 58 | -451.3 | -162.2 | 231.6 | 0.74 | -65.9 |  |
| 5 | 8 | 0.25 | 12 | 6 | -135.4 | 0.40 | 0.17 | -225.6 | 18 | -135.4 | 122.8 | 21.0 | 1.03 | 4.7 |  |
| 5 | 8 | 0.25 | 24 | 6 | -88.5 | 0.58 | 0.50 | -147.6 | 18 | -88.5 | 164.4 | -111.1 | 0.90 | -19.6 |  |

OOS by exit reason:

| reason | n | net | avg bps |
|---|---|---|---|
| stop | 12 | -1050.8 | -875.7 |
| time | 40 | 457.6 | 114.4 |

OOS funding paid total = -92.56 USD; fees only = 30.95 USD; avg hold = 21.2 h

## Controls (1h, arm A, selected params, OOS window folds 2+3)

### Neighbouring parameters (no re-selection)

| Y | V | bid | H | n | net | pf | wr | bps | f2 | f3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 0.25 | 12 | 53 | 266.5 | 1.29 | 0.60 | 50.3 | 291.1 | -24.6 |
| 5 | 4 | 0.25 | 12 | 17 | -158.8 | 0.60 | 0.53 | -93.4 | 65.1 | -223.9 |
| 4 | 6 | 0.25 | 12 | 18 | 146.2 | 2.15 | 0.56 | 81.2 | 139.7 | 6.5 |
| 4 | 8 | 0.25 | 12 | 18 | 186.2 | 2.53 | 0.67 | 103.4 | 174.7 | 11.5 |
| 4 | 4 | 0.0 | 12 | 78 | 114.5 | 1.09 | 0.55 | 14.7 | 218.2 | -103.8 |
| 4 | 4 | 0.5 | 12 | 10 | 30.9 | 1.34 | 0.80 | 30.9 | -30.4 | 61.3 |
| 4 | 4 | 0.25 | 6 | 26 | -23.2 | 0.94 | 0.58 | -8.9 | 177.5 | -200.7 |
| 4 | 4 | 0.25 | 24 | 26 | -111.7 | 0.80 | 0.69 | -42.9 | 212.0 | -323.6 |

neighbours positive: 5/8

### Shuffle test (random signal bars in the same coin inside the OOS window, same mechanics, 100 reps)

real OOS net=-141.5 (n=26); shuffled mean=-34.8 sd=53.0 p95=36.4; real percentile=0.03

### Beta control (random-hour longs in the same coin, hold H bars open->open, OOS window, 200 reps)

real: gross -50.7 bps / net -54.4 bps per trade; random-hour gross mean=0.7 sd=60.4 p95=104.7 (net ~ gross - 6 bps); real gross percentile=0.18

### BTC-hedged arm (short equal notional BTC, taker both sides, BTC funding received)

hedged OOS: n=  26 net=  -180.0 pf=0.64 wr=0.62 sharpe=-0.75 bps= -69.2 folds=[0.0, 95.1, -275.1] fold_n=[0, 11, 15]
mean alt leg -50.7 bps, mean hedge leg -7.0 bps
hedged full period: n=  38 net=  -209.7 pf=0.71 wr=0.61 sharpe=-0.74 bps= -55.2 folds=[-29.7, 95.1, -275.1] fold_n=[12, 11, 15]

### Diagnostics: market-wide flushes (>=3 other coins) and up-spike mirror, selected params, full period

- market-wide flush longs: n=  29 net=   289.1 pf=2.85 wr=0.76 sharpe= 2.68 bps=  99.7 folds=[289.3, 18.0, -18.1] fold_n=[18, 7, 4]
- up-spike mirror (long after +2% high-vol bar): n=  97 net=  -541.0 pf=0.77 wr=0.49 sharpe=-0.94 bps= -55.8 folds=[-154.8, -384.0, -2.3] fold_n=[24, 44, 29]
- up-spike mirror market-wide: n=  12 net=   134.2 pf=2.35 wr=0.67 sharpe= 1.36 bps= 111.8 folds=[60.7, 20.7, 52.8] fold_n=[4, 3, 5]

### Per-coin OOS (arm A) and liquidity split (24h vol < $5M = illiquid, current snapshot)

- liquid: n=10 net=108.6 bps=108.6
- illiquid: n=16 net=-250.1 bps=-156.3

| coin | n | net | dayNtlVlm |
|---|---|---|---|
| TAO | 2.0 | 71.8 | 50.8M |
| LIT | 1.0 | 44.7 | 46.9M |
| ASTER | 1.0 | 25.1 | 4.6M |
| INJ | 1.0 | 24.8 | 2.8M |
| kBONK | 1.0 | 21.8 | 2.0M |
| ZRO | 1.0 | 21.7 | 5.1M |
| ARB | 1.0 | 21.1 | 1.8M |
| ETHFI | 1.0 | 19.7 | 4.1M |
| GRASS | 1.0 | 16.9 | 2.2M |
| VIRTUAL | 1.0 | 14.4 | 1.9M |
| LINK | 1.0 | 13.2 | 20.8M |
| PAXG | 1.0 | 11.8 | 3.2M |
| BTC | 1.0 | -1.7 | 3699.5M |
| AVAX | 1.0 | -3.2 | 7.6M |
| WLFI | 2.0 | -4.4 | 0.7M |
| DOT | 1.0 | -4.5 | 1.2M |
| BCH | 1.0 | -5.6 | 1.2M |
| UNI | 2.0 | -7.9 | 14.3M |
| DOGE | 1.0 | -29.9 | 16.9M |
| MET | 1.0 | -69.0 | 1.1M |
| MORPHO | 1.0 | -73.9 | 1.8M |
| KAITO | 2.0 | -248.4 | 1.0M |

largest single-coin share of positive PnL = 0.23; coins net>0: 12/22

OOS by flush size (rng_pct quantiles):

- small: n=9 net=17.9 bps=19.9
- mid: n=8 net=-15.6 bps=-19.5
- large: n=9 net=-143.8 bps=-159.8

OOS monthly net:

- 2026-04: n=5 net=17.6
- 2026-05: n=2 net=78.3
- 2026-06: n=5 net=39.1
- 2026-07: n=4 net=-104.2
- 2026-08: n=10 net=-172.3

## 15m arm A (cached top-50 coins only, PIT membership applied)  (data 2026-07-06 -> 2026-08-27; fold starts ['2026-07-06', '2026-07-24', '2026-08-10'])

**Walk-forward best (fold 1):** `{'Y': 3, 'V': 8, 'bid': 0.0, 'H': 12}`

**OOS folds 2+3:** n=  98 net=  -425.0 pf=0.48 wr=0.51 sharpe=-2.11 bps= -43.4 folds=[0.0, -177.8, -247.3] fold_n=[0, 44, 54]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets, full period)

| Y | V | bid | H | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 0.0 | 12 | 61 | 30.6 | 1.12 | 0.62 | 5.0 | 167 | 30.6 | -187.2 | -181.6 | 0.69 | -20.3 |  |
| 3 | 4 | 0.0 | 24 | 61 | -26.1 | 0.92 | 0.59 | -4.3 | 167 | -26.1 | -162.5 | -198.5 | 0.68 | -23.2 |  |
| 3 | 4 | 0.25 | 12 | 19 | 1.9 | 1.03 | 0.53 | 1.0 | 46 | 1.9 | -25.1 | 118.7 | 1.62 | 20.8 |  |
| 3 | 4 | 0.25 | 24 | 19 | -8.3 | 0.89 | 0.58 | -4.4 | 46 | -8.3 | -39.9 | 133.0 | 1.43 | 18.4 |  |
| 3 | 8 | 0.0 | 12 | 46 | 100.1 | 1.63 | 0.67 | 21.8 | 144 | 100.1 | -177.8 | -247.3 | 0.66 | -22.6 | * |
| 3 | 8 | 0.0 | 24 | 46 | 22.4 | 1.09 | 0.63 | 4.9 | 144 | 22.4 | -164.7 | -421.0 | 0.55 | -39.1 |  |
| 3 | 8 | 0.25 | 12 | 13 | 3.9 | 1.08 | 0.54 | 3.0 | 38 | 3.9 | -23.9 | 96.1 | 1.54 | 20.1 |  |
| 3 | 8 | 0.25 | 24 | 13 | -7.5 | 0.87 | 0.54 | -5.7 | 38 | -7.5 | -38.7 | 105.8 | 1.33 | 15.7 |  |
| 4 | 4 | 0.0 | 12 | 29 | -50.2 | 0.74 | 0.48 | -17.3 | 82 | -50.2 | -2.4 | -165.8 | 0.66 | -26.6 |  |
| 4 | 4 | 0.0 | 24 | 29 | -123.9 | 0.51 | 0.45 | -42.7 | 82 | -123.9 | -7.8 | -103.6 | 0.65 | -28.7 |  |
| 4 | 4 | 0.25 | 12 | 10 | -31.9 | 0.45 | 0.30 | -31.9 | 19 | -31.9 | -1.8 | 52.0 | 1.19 | 9.6 |  |
| 4 | 4 | 0.25 | 24 | 10 | -40.7 | 0.41 | 0.40 | -40.7 | 19 | -40.7 | 1.6 | 74.0 | 1.34 | 18.4 |  |
| 4 | 8 | 0.0 | 12 | 24 | -17.5 | 0.88 | 0.50 | -7.3 | 71 | -17.5 | -2.4 | -211.4 | 0.61 | -32.6 |  |
| 4 | 8 | 0.0 | 24 | 24 | -91.7 | 0.57 | 0.46 | -38.2 | 71 | -91.7 | -7.8 | -156.1 | 0.59 | -36.0 |  |
| 4 | 8 | 0.25 | 12 | 7 | -22.8 | 0.49 | 0.29 | -32.6 | 14 | -22.8 | -1.8 | 30.7 | 1.07 | 4.3 |  |
| 4 | 8 | 0.25 | 24 | 7 | -34.2 | 0.39 | 0.29 | -48.9 | 14 | -34.2 | 1.6 | 49.7 | 1.19 | 12.2 |  |
| 5 | 4 | 0.0 | 12 | 16 | -21.5 | 0.80 | 0.38 | -13.5 | 44 | -21.5 | -23.9 | -98.5 | 0.57 | -32.7 |  |
| 5 | 4 | 0.0 | 24 | 16 | -78.8 | 0.52 | 0.44 | -49.3 | 44 | -78.8 | -6.5 | -33.9 | 0.65 | -27.1 |  |
| 5 | 4 | 0.25 | 12 | 5 | -15.2 | 0.38 | 0.20 | -30.5 | 11 | -15.2 | -1.8 | -14.8 | 0.49 | -29.0 |  |
| 5 | 4 | 0.25 | 24 | 5 | -26.6 | 0.26 | 0.20 | -53.3 | 11 | -26.6 | 1.6 | 3.8 | 0.70 | -19.3 |  |
| 5 | 8 | 0.0 | 12 | 15 | -26.8 | 0.75 | 0.33 | -17.9 | 41 | -26.8 | -23.9 | -92.5 | 0.56 | -34.9 |  |
| 5 | 8 | 0.0 | 24 | 15 | -84.1 | 0.49 | 0.40 | -56.1 | 41 | -84.1 | -6.5 | -31.9 | 0.64 | -29.9 |  |
| 5 | 8 | 0.25 | 12 | 5 | -15.2 | 0.38 | 0.20 | -30.5 | 10 | -15.2 | -1.8 | -14.0 | 0.49 | -31.0 |  |
| 5 | 8 | 0.25 | 24 | 5 | -26.6 | 0.26 | 0.20 | -53.3 | 10 | -26.6 | 1.6 | 1.6 | 0.67 | -23.4 |  |

OOS by exit reason:

| reason | n | net | avg bps |
|---|---|---|---|
| stop | 13 | -337.4 | -259.5 |
| target | 39 | 341.4 | 87.5 |
| time | 46 | -429.1 | -93.3 |

OOS funding paid total = 1.22 USD; fees only = 46.82 USD; avg hold = 2.0 h

1h-selected params {'Y': 4, 'V': 4, 'bid': 0.25, 'H': 12} applied to 15m OOS window: n=   9 net=    50.2 pf=2.33 wr=0.67 sharpe= 0.88 bps=  55.8 folds=[0.0, -1.8, 52.0] fold_n=[0, 2, 7]

## 5m arm A (cached top-50 coins only, PIT membership applied)  (data 2026-08-10 -> 2026-08-27; fold starts ['2026-08-10', '2026-08-16', '2026-08-22'])

**Walk-forward best (fold 1):** `{'Y': 4, 'V': 8, 'bid': 0.25, 'H': 12}`

**OOS folds 2+3:** n=  14 net=     8.7 pf=1.13 wr=0.64 sharpe= 0.16 bps=   6.2 folds=[0.0, -7.6, 16.4] fold_n=[0, 9, 5]

### In-sample grid (is_* = fold-1 metrics used for selection; f1/f2/f3 = fold nets, full period)

| Y | V | bid | H | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | pf_full | bps_full | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 0.0 | 12 | 66 | -231.5 | 0.38 | 0.45 | -35.1 | 193 | -231.5 | 30.3 | 176.7 | 0.97 | -1.3 |  |
| 3 | 4 | 0.0 | 24 | 66 | -217.0 | 0.41 | 0.50 | -32.9 | 192 | -217.0 | 135.8 | 210.4 | 1.15 | 6.7 |  |
| 3 | 4 | 0.25 | 12 | 25 | -39.7 | 0.46 | 0.44 | -15.9 | 74 | -39.7 | 19.7 | 38.9 | 1.07 | 2.6 |  |
| 3 | 4 | 0.25 | 24 | 25 | -35.9 | 0.54 | 0.60 | -14.3 | 73 | -35.9 | 83.7 | 52.4 | 1.36 | 13.7 |  |
| 3 | 8 | 0.0 | 12 | 55 | -216.6 | 0.36 | 0.44 | -39.4 | 153 | -216.6 | 5.1 | 103.4 | 0.85 | -7.1 |  |
| 3 | 8 | 0.0 | 24 | 55 | -214.1 | 0.38 | 0.45 | -38.9 | 153 | -214.1 | 111.0 | 120.9 | 1.02 | 1.2 |  |
| 3 | 8 | 0.25 | 12 | 22 | -45.0 | 0.39 | 0.41 | -20.4 | 58 | -45.0 | 3.4 | 15.7 | 0.89 | -4.5 |  |
| 3 | 8 | 0.25 | 24 | 22 | -43.3 | 0.44 | 0.55 | -19.7 | 58 | -43.3 | 67.4 | 60.5 | 1.42 | 14.6 |  |
| 4 | 4 | 0.0 | 12 | 41 | -188.0 | 0.36 | 0.44 | -45.8 | 100 | -188.0 | -25.8 | 202.5 | 0.98 | -1.1 |  |
| 4 | 4 | 0.0 | 24 | 41 | -181.7 | 0.39 | 0.49 | -44.3 | 100 | -181.7 | 48.6 | 259.2 | 1.26 | 12.6 |  |
| 4 | 4 | 0.25 | 12 | 11 | -30.2 | 0.29 | 0.27 | -27.5 | 26 | -30.2 | 12.7 | 16.4 | 0.99 | -0.4 |  |
| 4 | 4 | 0.25 | 24 | 11 | -33.0 | 0.36 | 0.55 | -30.0 | 26 | -33.0 | 73.5 | 74.1 | 2.76 | 44.1 |  |
| 4 | 8 | 0.0 | 12 | 38 | -194.0 | 0.34 | 0.42 | -51.0 | 90 | -194.0 | -40.4 | 71.8 | 0.71 | -18.1 |  |
| 4 | 8 | 0.0 | 24 | 38 | -190.7 | 0.36 | 0.45 | -50.2 | 90 | -190.7 | 38.1 | 85.0 | 0.87 | -7.5 |  |
| 4 | 8 | 0.25 | 12 | 10 | -29.5 | 0.30 | 0.30 | -29.5 | 24 | -29.5 | -7.6 | 16.4 | 0.81 | -8.7 | * |
| 4 | 8 | 0.25 | 24 | 10 | -34.4 | 0.33 | 0.50 | -34.4 | 24 | -34.4 | 53.1 | 74.1 | 2.43 | 38.7 |  |
| 5 | 4 | 0.0 | 12 | 29 | -95.0 | 0.48 | 0.48 | -32.8 | 59 | -95.0 | -54.0 | 106.6 | 0.86 | -7.2 |  |
| 5 | 4 | 0.0 | 24 | 29 | -86.2 | 0.54 | 0.52 | -29.7 | 59 | -86.2 | -9.6 | 82.5 | 0.96 | -2.3 |  |
| 5 | 4 | 0.25 | 12 | 8 | -14.5 | 0.47 | 0.38 | -18.1 | 17 | -14.5 | -13.4 | 32.4 | 1.10 | 2.7 |  |
| 5 | 4 | 0.25 | 24 | 8 | -13.5 | 0.56 | 0.62 | -16.9 | 17 | -13.5 | 5.5 | 37.0 | 1.72 | 17.1 |  |
| 5 | 8 | 0.0 | 12 | 29 | -95.0 | 0.48 | 0.48 | -32.8 | 57 | -95.0 | -54.0 | 75.8 | 0.76 | -12.9 |  |
| 5 | 8 | 0.0 | 24 | 29 | -86.2 | 0.54 | 0.52 | -29.7 | 57 | -86.2 | -9.6 | 37.3 | 0.82 | -10.3 |  |
| 5 | 8 | 0.25 | 12 | 8 | -14.5 | 0.47 | 0.38 | -18.1 | 17 | -14.5 | -13.4 | 32.4 | 1.10 | 2.7 |  |
| 5 | 8 | 0.25 | 24 | 8 | -13.5 | 0.56 | 0.62 | -16.9 | 17 | -13.5 | 5.5 | 37.0 | 1.72 | 17.1 |  |

OOS by exit reason:

| reason | n | net | avg bps |
|---|---|---|---|
| target | 5 | 62.0 | 123.9 |
| time | 9 | -53.2 | -59.1 |

OOS funding paid total = 0.07 USD; fees only = 6.89 USD; avg hold = 0.7 h

1h-selected params {'Y': 4, 'V': 4, 'bid': 0.25, 'H': 12} applied to 5m OOS window: n=  15 net=    29.1 pf=1.44 wr=0.67 sharpe= 0.50 bps=  19.4 folds=[0.0, 12.7, 16.4] fold_n=[0, 10, 5]

## Verdict: **none**

criteria: {'net_pos': False, 'pf': False, 'n': False, 'folds': False, 'shuffle': False, 'neigh': True, 'hedged_folds': False, 'beta': False}
## Interpretation

**Verdict: none.** The walk-forward OOS (1h, arm A, params selected on fold 1 = {Y:4, V:4, bid:0.25, H:12}) is
n=26, net -141.5 USD (-54 bps/trade), PF 0.72, folds 2/3 = +136.6 / -278.2. Arm B (time-stop only) is worse:
n=52, net -593 USD, PF 0.67, both OOS folds negative. The BTC-hedged arm is negative (-180 USD, fold 3 -275),
the shuffle percentile is 0.03 (the real strategy is WORSE than random bars with the same mechanics) and the
beta control percentile is 0.18. 15m and 5m walk-forwards are also negative (-425 and +8.7 USD).

Why the rationale's descriptive check did not survive:
1. **The +136/+50/+123 bps forward returns were mostly market-wide (BTC-beta) flushes.** Splitting the same
   Y=4/V=6/ret<-2% signal on a point-in-time top-50 universe: coin-specific flushes (<3 other coins flushing)
   give raw 12-bar returns of -123 / +72 / +158 bps by fold (n=31/32/43), while market-wide flushes give
   +339 / +65 / +111 bps (n=56/38/77). The fold-1 (Feb-Apr) positive number came entirely from buying
   market-wide capitulations that rebounded - that is the bull/beta-rebound effect the round-1 skeptics
   flagged, not a coin-specific forced-seller overshoot.
2. **Every cell of the 24-cell grid is negative in fold 1 for arm A** (and 22/24 for arm B), so walk-forward
   selection picks among losers; the only cells with positive full-period bps (Y=4,V=8,bid=0.25: +55/+87 bps)
   have n=26 and rely on fold 2, and lose in fold 3 at H=24.
3. **Adverse selection of the resting bid.** Requiring the next bar to trade 25% of the range below the close
   filters to signals where the flush continued: at bid=0.25 the filled subset earns -46 bps gross vs +50 bps
   for taker-at-open on all signals (fill diagnostic). Deeper bids (0.5x) fill only 11 of 106 signals.
4. **Fat left tail.** In arm B OOS, 40 time exits average +114 bps but 12 stops average -876 bps (stop is
   1.5x a 4xATR range, ~9%); coin-specific flushes continue often enough that the stop dominates. Illiquid
   names (<$5M/day) are where the losses concentrate (OOS illiquid -156 bps/trade vs liquid +109 bps, n=10).
5. Funding is immaterial (net -12.6 USD received over 26 OOS trades); fees are 3-6 bps, so costs are not
   the problem - the signal itself has no consistent sign.

Diagnostics: market-wide flush longs are +289 / +18 / -18 by fold (n=18/7/4) - regime-dependent, not an
edge; the up-spike mirror is -541 USD (PF 0.77), consistent with round 1.

Caveats: 208 days of 1h data (HL caps candleSnapshot at 5000 bars); the point-in-time universe was built
from 174 coins' 1h candles (KAS and INIT returned empty); 15m/5m runs use the cached 50 coins only with the
1h-derived membership applied.
