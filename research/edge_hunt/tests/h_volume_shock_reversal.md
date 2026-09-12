# volume_shock_reversal — results

Volume shock (usd vol > X x trailing-100 median) + range > Y x ATR14 + long wick against the move -> fade at next open. All TAKER fills. Stop at wick extreme (stop assumed first when stop & target touch in the same bar), target = tgt x candle range, time stop 12 bars (exit at open of bar t+13). $1000 notional per trade, one position per coin. Headline timeframe = 15m (52d, folds ~17d); 5m (17d, folds ~6d) is secondary.


## 15m  (data 2026-07-06 -> 2026-08-27, fold starts ['2026-07-06', '2026-07-24', '2026-08-10'])

**Walk-forward best (fold 1):** `{'vol_x': 8, 'rng_y': 2.0, 'wick_w': 0.5, 'tgt': 0.5, 'H': 12}`

**OOS folds 2+3 (HEADLINE):** n= 704 net=  -694.51 pf=0.82 wr=0.50 sharpe=-1.44 bps=-9.9 folds=[0.0, -246.4, -448.1] fold_n=[0, 339, 365]


### In-sample grid (fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period, n=full-period trades)

| vol_x | rng_y | wick_w | tgt | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 2.0 | 0.3 | 0.5 | 1264 | -931.2 | 0.81 | 0.50 | -7.4 | 3769 | -931.2 | -1007.8 | -530.8 |  |
| 4 | 2.0 | 0.3 | 1.0 | 1249 | -1404.1 | 0.77 | 0.38 | -11.2 | 3697 | -1404.1 | -686.6 | -437.5 |  |
| 4 | 2.0 | 0.5 | 0.5 | 584 | -181.7 | 0.92 | 0.58 | -3.1 | 1707 | -181.7 | -489.7 | -584.0 |  |
| 4 | 2.0 | 0.5 | 1.0 | 579 | -467.8 | 0.84 | 0.45 | -8.1 | 1689 | -467.8 | -404.7 | -300.1 |  |
| 4 | 3.0 | 0.3 | 0.5 | 492 | -960.1 | 0.62 | 0.45 | -19.5 | 1375 | -960.1 | -148.2 | 594.7 |  |
| 4 | 3.0 | 0.3 | 1.0 | 490 | -859.8 | 0.68 | 0.38 | -17.5 | 1365 | -859.8 | -110.5 | 628.6 |  |
| 4 | 3.0 | 0.5 | 0.5 | 221 | -309.2 | 0.72 | 0.56 | -14.0 | 604 | -309.2 | -237.0 | 247.1 |  |
| 4 | 3.0 | 0.5 | 1.0 | 221 | -295.2 | 0.76 | 0.47 | -13.4 | 603 | -295.2 | -280.1 | 168.2 |  |
| 8 | 2.0 | 0.3 | 0.5 | 735 | -651.0 | 0.79 | 0.50 | -8.9 | 2232 | -651.0 | -402.3 | -300.3 |  |
| 8 | 2.0 | 0.3 | 1.0 | 726 | -805.8 | 0.78 | 0.38 | -11.1 | 2198 | -805.8 | -259.3 | -221.5 |  |
| 8 | 2.0 | 0.5 | 0.5 | 356 | -107.3 | 0.92 | 0.59 | -3.0 | 1060 | -107.3 | -246.4 | -448.1 | * |
| 8 | 2.0 | 0.5 | 1.0 | 354 | -327.9 | 0.82 | 0.46 | -9.3 | 1054 | -327.9 | -223.1 | -278.9 |  |
| 8 | 3.0 | 0.3 | 0.5 | 333 | -663.0 | 0.63 | 0.45 | -19.9 | 990 | -663.0 | -58.4 | 548.3 |  |
| 8 | 3.0 | 0.3 | 1.0 | 332 | -590.4 | 0.69 | 0.39 | -17.8 | 985 | -590.4 | -85.7 | 562.0 |  |
| 8 | 3.0 | 0.5 | 0.5 | 159 | -251.3 | 0.70 | 0.56 | -15.8 | 461 | -251.3 | -224.0 | 371.1 |  |
| 8 | 3.0 | 0.5 | 1.0 | 159 | -241.4 | 0.74 | 0.47 | -15.2 | 460 | -241.4 | -311.5 | 299.3 |  |

### OOS breakdown
By exit reason:

| reason | n | net |
|---|---|---|
| stop | 272 | -3367.9 |
| target | 307 | 2172.9 |
| time | 125 | 500.4 |

By side:

| side | n | net |
|---|---|---|
| short | 352 | -1178.9 |
| long | 352 | 484.4 |

### Shuffle test (random signal bars, random side, same mechanics, OOS window, 30 reps)
real OOS net=-694.5 (n=704); shuffled mean=-777.5 sd=144.6 p95=-566.0; real percentile among shuffles=0.80


### Neighbouring parameters (OOS window folds 2+3, no re-selection)
| vol_x | rng_y | wick_w | tgt | H | n | net | pf | wr | bps | f2 | f3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6.0 | 2.0 | 0.5 | 0.5 | 12 | 863 | -831.3 | 0.82 | 0.51 | -9.6 | -322.5 | -508.8 |
| 12.0 | 2.0 | 0.5 | 0.5 | 12 | 490 | -412.8 | 0.86 | 0.50 | -8.4 | -187.5 | -225.3 |
| 8 | 1.5 | 0.5 | 0.5 | 12 | 1159 | -871.5 | 0.84 | 0.53 | -7.5 | -251.7 | -619.8 |
| 8 | 2.5 | 0.5 | 0.5 | 12 | 445 | -172.7 | 0.94 | 0.50 | -3.9 | -116.5 | -56.2 |
| 8 | 2.0 | 0.4 | 0.5 | 12 | 1046 | -765.6 | 0.87 | 0.50 | -7.3 | -365.1 | -400.5 |
| 8 | 2.0 | 0.6 | 0.5 | 12 | 423 | -799.9 | 0.70 | 0.52 | -18.9 | -242.9 | -557.0 |
| 8 | 2.0 | 0.5 | 0.25 | 12 | 709 | -135.4 | 0.95 | 0.61 | -1.9 | -59.4 | -76.0 |
| 8 | 2.0 | 0.5 | 0.75 | 12 | 702 | -779.6 | 0.82 | 0.44 | -11.1 | -351.5 | -428.2 |
| 8 | 2.0 | 0.5 | 0.5 | 8 | 707 | -517.0 | 0.86 | 0.49 | -7.3 | -278.2 | -238.8 |
| 8 | 2.0 | 0.5 | 0.5 | 16 | 704 | -1059.1 | 0.75 | 0.51 | -15.0 | -520.2 | -538.9 |

### Per-coin OOS
liquid(>=5M) net=-415.3 n=424; illiquid(<5M) net=-279.2 n=280

| coin | n | net | dayNtlVlm | illiquid |
|---|---|---|---|---|
| XPL | 14 | 54.3 | 11.8M | False |
| LIT | 11 | 54.1 | 46.9M | False |
| NEAR | 5 | 51.4 | 25.9M | False |
| AAVE | 6 | 47.0 | 14.7M | False |
| DOGE | 13 | 41.4 | 16.9M | False |
| UNI | 11 | 40.0 | 14.3M | False |
| GRAM | 27 | 35.0 | 3.1M | True |
| JTO | 10 | 33.0 | 3.1M | True |
| CASHCAT | 16 | 31.4 | 30.9M | False |
| FET | 8 | 27.4 | 2.5M | True |
| VVV | 19 | 25.9 | 7.1M | False |
| GRASS | 16 | 20.6 | 2.2M | True |
| LTC | 6 | 13.1 | 2.1M | True |
| WLD | 11 | 9.9 | 9.0M | False |
| PUMP | 11 | 7.9 | 174.8M | False |
| XRP | 9 | 6.8 | 117.8M | False |
| JUP | 11 | 5.3 | 5.9M | False |
| ETHFI | 19 | 5.2 | 4.1M | True |
| XMR | 7 | 4.0 | 16.9M | False |
| PENGU | 18 | 3.3 | 12.0M | False |
| FARTCOIN | 10 | 1.4 | 37.1M | False |
| ETH | 17 | -1.2 | 1679.4M | False |
| ADA | 11 | -8.8 | 4.0M | True |
| INJ | 13 | -9.2 | 2.8M | True |
| MON | 13 | -9.7 | 7.5M | False |
| WIF | 12 | -11.5 | 2.3M | True |
| AVAX | 20 | -13.2 | 7.6M | False |
| kPEPE | 14 | -13.3 | 16.6M | False |
| LINK | 10 | -13.8 | 20.8M | False |
| SUI | 14 | -15.1 | 18.1M | False |
| TAO | 12 | -15.4 | 50.8M | False |
| ONDO | 7 | -16.9 | 6.3M | False |
| SOL | 12 | -19.4 | 1243.4M | False |
| PAXG | 18 | -20.7 | 3.2M | True |
| ZRO | 6 | -22.6 | 5.1M | False |
| TRX | 22 | -25.1 | 3.6M | True |
| BTC | 12 | -25.6 | 3699.5M | False |
| CC | 20 | -27.4 | 2.4M | True |
| AERO | 16 | -29.2 | 3.4M | True |
| BNB | 7 | -29.3 | 14.7M | False |
| ASTER | 25 | -37.9 | 4.6M | True |
| ZEC | 13 | -40.2 | 289.2M | False |
| HYPE | 4 | -41.9 | 969.9M | False |
| TRUMP | 20 | -62.4 | 41.4M | False |
| CRV | 10 | -62.5 | 9.5M | False |
| PURR | 42 | -85.1 | 3.6M | True |
| ENA | 9 | -93.2 | 120.2M | False |
| CHIP | 29 | -115.9 | 6.1M | False |
| HEMI | 15 | -158.4 | 2.0M | True |
| SPX | 23 | -187.6 | 6.9M | False |

### Signal hour (UTC) concentration, WF-best params, FULL period (descriptive only)
| hour | n | net |
|---|---|---|
| 00 | 48 | -61.2 |
| 01 | 38 | -55.4 |
| 02 | 30 | -184.2 |
| 03 | 33 | -2.0 |
| 04 | 24 | 64.1 |
| 05 | 66 | 533.0 |
| 06 | 38 | -15.1 |
| 07 | 27 | -56.5 |
| 08 | 35 | -86.6 |
| 09 | 35 | 28.2 |
| 10 | 40 | -165.4 |
| 11 | 24 | -13.8 |
| 12 | 63 | -15.1 |
| 13 | 82 | -183.9 |
| 14 | 107 | -155.7 |
| 15 | 67 | -248.8 |
| 16 | 36 | -39.0 |
| 17 | 45 | -154.4 |
| 18 | 43 | 61.2 |
| 19 | 26 | -37.3 |
| 20 | 24 | -130.2 |
| 21 | 59 | 67.8 |
| 22 | 42 | -24.7 |
| 23 | 28 | 73.4 |

## 5m  (data 2026-08-10 -> 2026-08-27, fold starts ['2026-08-10', '2026-08-16', '2026-08-22'])

**Walk-forward best (fold 1):** `{'vol_x': 8, 'rng_y': 3.0, 'wick_w': 0.5, 'tgt': 1.0, 'H': 12}`

**OOS folds 2+3 (HEADLINE):** n= 443 net=  -265.05 pf=0.88 wr=0.42 sharpe=-0.86 bps=-6.0 folds=[0.0, 59.8, -324.9] fold_n=[0, 224, 219]


### In-sample grid (fold-1 metrics used for selection; f1/f2/f3 = fold nets over the full period, n=full-period trades)

| vol_x | rng_y | wick_w | tgt | is_n | is_net | is_pf | is_wr | is_bps | n_full | f1 | f2 | f3 | sel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 2.0 | 0.3 | 0.5 | 1180 | -1747.6 | 0.43 | 0.40 | -14.8 | 3885 | -1747.6 | -1143.7 | -1545.6 |  |
| 4 | 2.0 | 0.3 | 1.0 | 1152 | -1636.6 | 0.52 | 0.34 | -14.2 | 3792 | -1636.6 | -833.4 | -697.3 |  |
| 4 | 2.0 | 0.5 | 0.5 | 605 | -1153.7 | 0.34 | 0.41 | -19.1 | 1922 | -1153.7 | -497.9 | -939.0 |  |
| 4 | 2.0 | 0.5 | 1.0 | 593 | -1121.6 | 0.42 | 0.35 | -18.9 | 1894 | -1121.6 | -409.9 | -824.5 |  |
| 4 | 3.0 | 0.3 | 0.5 | 488 | -880.4 | 0.43 | 0.36 | -18.0 | 1558 | -880.4 | -339.9 | -493.8 |  |
| 4 | 3.0 | 0.3 | 1.0 | 483 | -778.9 | 0.52 | 0.31 | -16.1 | 1544 | -778.9 | -38.1 | -7.3 |  |
| 4 | 3.0 | 0.5 | 0.5 | 244 | -732.5 | 0.23 | 0.31 | -30.0 | 772 | -732.5 | -111.1 | -548.2 |  |
| 4 | 3.0 | 0.5 | 1.0 | 241 | -686.0 | 0.30 | 0.27 | -28.5 | 769 | -686.0 | 104.5 | -456.0 |  |
| 8 | 2.0 | 0.3 | 0.5 | 841 | -1411.7 | 0.40 | 0.39 | -16.8 | 2665 | -1411.7 | -689.5 | -947.8 |  |
| 8 | 2.0 | 0.3 | 1.0 | 824 | -1301.6 | 0.49 | 0.34 | -15.8 | 2615 | -1301.6 | -521.2 | -229.5 |  |
| 8 | 2.0 | 0.5 | 0.5 | 448 | -909.6 | 0.31 | 0.40 | -20.3 | 1388 | -909.6 | -360.2 | -641.4 |  |
| 8 | 2.0 | 0.5 | 1.0 | 441 | -810.5 | 0.43 | 0.37 | -18.4 | 1371 | -810.5 | -312.5 | -396.0 |  |
| 8 | 3.0 | 0.3 | 0.5 | 393 | -731.8 | 0.43 | 0.37 | -18.6 | 1235 | -731.8 | -230.9 | -353.7 |  |
| 8 | 3.0 | 0.3 | 1.0 | 387 | -641.3 | 0.52 | 0.33 | -16.6 | 1223 | -641.3 | 76.3 | 7.7 |  |
| 8 | 3.0 | 0.5 | 0.5 | 207 | -616.0 | 0.23 | 0.30 | -29.8 | 650 | -616.0 | -111.1 | -431.8 |  |
| 8 | 3.0 | 0.5 | 1.0 | 204 | -555.9 | 0.32 | 0.28 | -27.2 | 647 | -555.9 | 59.8 | -324.9 | * |

### OOS breakdown
By exit reason:

| reason | n | net |
|---|---|---|
| stop | 158 | -1636.5 |
| target | 70 | 778.8 |
| time | 215 | 592.6 |

By side:

| side | n | net |
|---|---|---|
| short | 167 | -429.5 |
| long | 276 | 164.5 |

### Shuffle test (random signal bars, random side, same mechanics, OOS window, 30 reps)
real OOS net=-265.0 (n=443); shuffled mean=-365.7 sd=109.6 p95=-175.7; real percentile among shuffles=0.77


### Neighbouring parameters (OOS window folds 2+3, no re-selection)
| vol_x | rng_y | wick_w | tgt | H | n | net | pf | wr | bps | f2 | f3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6.0 | 3.0 | 0.5 | 1.0 | 12 | 478 | -317.2 | 0.87 | 0.41 | -6.6 | 29.0 | -346.2 |
| 12.0 | 3.0 | 0.5 | 1.0 | 12 | 377 | -227.9 | 0.89 | 0.42 | -6.0 | 46.3 | -274.2 |
| 8 | 2.5 | 0.5 | 1.0 | 12 | 621 | -409.2 | 0.86 | 0.41 | -6.6 | -7.1 | -402.1 |
| 8 | 3.5 | 0.5 | 1.0 | 12 | 328 | -162.7 | 0.91 | 0.42 | -5.0 | 104.3 | -266.9 |
| 8 | 3.0 | 0.4 | 1.0 | 12 | 618 | 87.4 | 1.03 | 0.44 | 1.4 | 207.3 | -120.0 |
| 8 | 3.0 | 0.6 | 1.0 | 12 | 278 | -270.7 | 0.83 | 0.44 | -9.7 | 63.8 | -334.5 |
| 8 | 3.0 | 0.5 | 0.75 | 12 | 443 | -341.4 | 0.85 | 0.43 | -7.7 | 19.6 | -361.0 |
| 8 | 3.0 | 0.5 | 1.25 | 12 | 443 | -191.8 | 0.92 | 0.41 | -4.3 | 99.8 | -291.5 |
| 8 | 3.0 | 0.5 | 1.0 | 8 | 443 | -107.1 | 0.94 | 0.43 | -2.4 | -41.5 | -65.7 |
| 8 | 3.0 | 0.5 | 1.0 | 16 | 442 | -667.0 | 0.75 | 0.40 | -15.1 | 137.7 | -804.7 |

### Per-coin OOS
liquid(>=5M) net=-259.9 n=245; illiquid(<5M) net=-5.1 n=198

| coin | n | net | dayNtlVlm | illiquid |
|---|---|---|---|---|
| CASHCAT | 4 | 116.5 | 30.9M | False |
| XPL | 8 | 85.6 | 11.8M | False |
| ETHFI | 12 | 55.9 | 4.1M | True |
| MON | 11 | 52.0 | 7.5M | False |
| PUMP | 4 | 51.8 | 174.8M | False |
| GRASS | 5 | 40.4 | 2.2M | True |
| CC | 27 | 36.2 | 2.4M | True |
| FET | 11 | 34.5 | 2.5M | True |
| NEAR | 7 | 31.3 | 25.9M | False |
| INJ | 6 | 28.1 | 2.8M | True |
| JTO | 6 | 23.6 | 3.1M | True |
| PENGU | 7 | 22.5 | 12.0M | False |
| HYPE | 5 | 17.4 | 969.9M | False |
| UNI | 6 | 14.5 | 14.3M | False |
| FARTCOIN | 3 | 10.1 | 37.1M | False |
| GRAM | 14 | 8.6 | 3.1M | True |
| SOL | 11 | 6.0 | 1243.4M | False |
| WIF | 3 | 5.1 | 2.3M | True |
| AAVE | 4 | 1.1 | 14.7M | False |
| JUP | 12 | -0.1 | 5.9M | False |
| VVV | 12 | -0.6 | 7.1M | False |
| BNB | 3 | -5.9 | 14.7M | False |
| ONDO | 5 | -7.4 | 6.3M | False |
| ASTER | 15 | -8.8 | 4.6M | True |
| ADA | 7 | -10.6 | 4.0M | True |
| kPEPE | 7 | -10.9 | 16.6M | False |
| XRP | 4 | -12.2 | 117.8M | False |
| PAXG | 8 | -12.6 | 3.2M | True |
| CHIP | 6 | -13.1 | 6.1M | False |
| LIT | 2 | -15.9 | 46.9M | False |
| LINK | 4 | -16.7 | 20.8M | False |
| CRV | 9 | -20.6 | 9.5M | False |
| ETH | 9 | -20.7 | 1679.4M | False |
| WLD | 2 | -22.3 | 9.0M | False |
| TRX | 15 | -23.0 | 3.6M | True |
| LTC | 5 | -24.5 | 2.1M | True |
| TAO | 7 | -27.4 | 50.8M | False |
| AERO | 10 | -28.3 | 3.4M | True |
| XMR | 13 | -29.0 | 16.9M | False |
| ENA | 10 | -34.2 | 120.2M | False |
| BTC | 8 | -35.9 | 3699.5M | False |
| AVAX | 12 | -35.9 | 7.6M | False |
| ZEC | 6 | -41.2 | 289.2M | False |
| SPX | 14 | -46.3 | 6.9M | False |
| SUI | 9 | -53.5 | 18.1M | False |
| HEMI | 5 | -56.6 | 2.0M | True |
| TRUMP | 6 | -66.5 | 41.4M | False |
| ZRO | 7 | -67.3 | 5.1M | False |
| PURR | 49 | -73.4 | 3.6M | True |
| DOGE | 8 | -85.2 | 16.9M | False |

### Signal hour (UTC) concentration, WF-best params, FULL period (descriptive only)
| hour | n | net |
|---|---|---|
| 00 | 26 | -13.1 |
| 01 | 14 | 34.2 |
| 02 | 30 | -98.1 |
| 03 | 16 | -3.5 |
| 04 | 14 | 4.7 |
| 05 | 70 | -76.2 |
| 06 | 27 | -9.2 |
| 07 | 23 | 18.8 |
| 08 | 21 | -40.1 |
| 09 | 22 | 55.7 |
| 10 | 20 | 20.6 |
| 11 | 15 | -16.5 |
| 12 | 72 | -261.0 |
| 13 | 27 | -101.4 |
| 14 | 35 | 72.6 |
| 15 | 22 | -87.2 |
| 16 | 14 | -12.8 |
| 17 | 14 | -15.5 |
| 18 | 17 | -24.8 |
| 19 | 20 | 64.3 |
| 20 | 33 | -200.8 |
| 21 | 47 | -103.5 |
| 22 | 19 | 17.3 |
| 23 | 29 | -45.4 |

## Diagnostics (WF-best params, OOS window, folds 2+3)

| tf | OOS gross | OOS fees | OOS net | stop exits (n/net) | target exits (n/net) | time exits (n/net) | stopped inside entry bar |
|---|---|---|---|---|---|---|---|
| 15m | -60.2 | 634.3 | -694.5 | 272 / -3367.9 | 307 / +2172.9 | 125 / +500.4 | 74 of 272 |
| 5m | +134.0 | 399.0 | -265.0 | 158 / -1636.5 | 70 / +778.8 | 215 / +592.6 | 28 of 158 |

Raw forward return from the t+1 open, signed in the fade direction, no stop/target (bps; round-trip taker = 9 bps):

| tf | h bars | all | long fades (after down cascade) | short fades (after up spike) |
|---|---|---|---|---|
| 15m | 1 | +3.9 | +15.1 | -7.5 |
| 15m | 3 | -4.1 | +14.8 | -23.1 |
| 15m | 12 | -3.2 | +36.0 | -42.7 |
| 15m | 24 | -21.0 | +22.4 | -64.8 |
| 5m | 3 | +8.5 | +23.0 | -15.9 |
| 5m | 12 | -3.8 | +21.3 | -46.1 |
| 5m | 24 | +4.4 | +43.9 | -61.9 |

Quartile splits of OOS net by signal strength (15m): range/ATR top quartile (mean 7.1x) = +335 vs the three lower quartiles -328/-441/-261. Volume-ratio quartiles show no monotone pattern (top quartile -408). Same shape on 5m: top range quartile +107, others negative.

## Interpretation

* The pattern as specified (symmetric fade, taker in/out, stop at wick extreme, 0.5-1x range target, 12-bar time stop) has **no gross edge** in either timeframe. OOS gross is ~0; fees make it clearly negative. Every grid cell is negative in fold 1 and on the full period on 15m (except a few 3x-ATR cells that turn positive only in fold 3), and every one of the 16 cells is negative in fold 1 on 5m.
* Shuffle test: real OOS net is at the 77-80th percentile of random-timing runs, i.e. the signal is barely distinguishable from random entries with the same mechanics, and both are negative. Neighbours: 0/10 positive on 15m, 1/10 on 5m (wick 0.4, +87 = noise).
* The stop-at-wick-extreme is the killer: stops are the largest PnL bucket (-3.4k on 15m), a quarter of them are hit inside the entry bar because a 5-8x volume bar's wick extreme is often retested immediately.
* The only sub-structure with a positive sign is directional: fading **downside** cascades (going long) earns +20-40 bps over 12 bars raw in both timeframes, while fading **upside** spikes loses 40-60 bps (upside volume spikes on HL perps continue, they do not revert). Also only the most extreme range bars (>5x ATR) are net positive. Neither is enough to call an edge here (long-only OOS: 15m +484 on 352 trades before considering that the selection was made after seeing the split).
* Concentration: on 15m the signals cluster at 13-15h UTC (US open, 256 of 1170 signals, all net negative) and 05h UTC (66 signals, +533, the only large positive hour - one Asia-session cluster). On 5m they cluster at 12h and 05h UTC, both negative. No coin group explains the loss: liquid (>=$5M/day) coins lose -415 (15m) / -260 (5m) and illiquid coins lose -279 / -5; the worst names are SPX, HEMI, CHIP, PURR, ENA, DOGE - a mix of liquidity tiers.

**Verdict: none.**
