# funding_extreme - results

Data: Hyperliquid 1h candles + hourly funding, 50 coins, evaluation window 2026-03-02 -> 2026-08-27 (3 chronological folds of ~59d). $1,000 notional/trade, one position per coin. Trailing rank window 720h; signal requires |measure| > default 1.25e-05/h. Funding cash flows included (folded into exit_px). Fees: taker 4.5 bps/side; maker 1.5 bps entry (fill only if bar traded through the open) + taker exit.


### fixed-hold (taker)
best (fold-1 selected): `{'measure': 'm1', 'pct': 0.1, 'hold': 24}`

OOS (folds 2+3): n=1911 net=-2254.05 pf=0.94 wr=0.49 sharpe=-0.83 dd=6562.87 bps=-11.8 folds=[0.0, 822.67, -3076.72]

| variant | is_n | is_net | is_pf | is_wr | n | net | pf | f1 | f2 | f3 | oos23 | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| taker_m1_p10_h24 | 945 | 5695.99 | 1.46 | 0.53 | 2856 | 3441.94 | 1.07 | 5695.99 | 822.67 | -3076.72 | -2254.05 | True |
| taker_m1_p5_h24 | 713 | 4416.07 | 1.46 | 0.53 | 2277 | 1874.92 | 1.04 | 4416.07 | 1745.67 | -4286.83 | -2541.15 | False |
| taker_m1_p10_h48 | 643 | 3965.67 | 1.35 | 0.53 | 1928 | 4056.58 | 1.09 | 3965.67 | 1282.29 | -1191.38 | 90.91 | False |
| taker_m1_p5_h48 | 510 | 3679.11 | 1.40 | 0.54 | 1605 | 4431.95 | 1.11 | 3679.11 | 2891.70 | -2138.87 | 752.84 | False |
| taker_m8_p10_h48 | 407 | 3336.61 | 1.45 | 0.57 | 1225 | 99.76 | 1.00 | 3336.61 | 496.41 | -3733.26 | -3236.86 | False |
| taker_m8_p10_h24 | 555 | 3162.17 | 1.43 | 0.56 | 1736 | -1025.05 | 0.97 | 3162.17 | 662.59 | -4849.81 | -4187.22 | False |
| taker_m24_p10_h24 | 379 | 3136.44 | 1.62 | 0.57 | 1299 | -950.37 | 0.97 | 3136.44 | 641.27 | -4728.08 | -4086.80 | False |
| taker_m8_p5_h24 | 407 | 3013.11 | 1.55 | 0.55 | 1325 | 1088.83 | 1.04 | 3013.11 | 1120.87 | -3045.14 | -1924.27 | False |
| taker_m24_p10_h48 | 268 | 2755.56 | 1.61 | 0.61 | 856 | 20.65 | 1.00 | 2755.56 | 1789.40 | -4524.32 | -2734.91 | False |
| taker_m8_p5_h48 | 308 | 2742.56 | 1.49 | 0.57 | 975 | 386.36 | 1.01 | 2742.56 | 587.72 | -2943.91 | -2356.20 | False |
| taker_m24_p5_h24 | 281 | 2572.00 | 1.72 | 0.57 | 945 | -2289.17 | 0.90 | 2572.00 | 102.40 | -4963.56 | -4861.17 | False |
| taker_m24_p5_h8 | 619 | 2547.44 | 1.50 | 0.53 | 2140 | -2021.91 | 0.93 | 2547.44 | -278.11 | -4291.24 | -4569.35 | False |
| taker_m8_p5_h8 | 673 | 2236.98 | 1.39 | 0.52 | 2319 | -770.12 | 0.97 | 2236.98 | 173.09 | -3180.18 | -3007.09 | False |
| taker_m1_p5_h8 | 1131 | 2162.83 | 1.21 | 0.51 | 3745 | -1018.57 | 0.98 | 2162.83 | 906.37 | -4087.77 | -3181.40 | False |
| taker_m24_p5_h48 | 203 | 2128.12 | 1.61 | 0.59 | 665 | -2457.75 | 0.88 | 2128.12 | 656.40 | -5242.28 | -4585.87 | False |
| taker_m8_p10_h8 | 983 | 2102.96 | 1.25 | 0.51 | 3208 | -2399.68 | 0.94 | 2102.96 | -476.11 | -4026.53 | -4502.64 | False |
| taker_m24_p10_h8 | 880 | 2044.76 | 1.26 | 0.51 | 3016 | -2851.16 | 0.93 | 2044.76 | -177.90 | -4718.02 | -4895.92 | False |
| taker_m24_p5_h4 | 1024 | 2029.29 | 1.30 | 0.52 | 3613 | -2699.98 | 0.92 | 2029.29 | -229.63 | -4499.64 | -4729.27 | False |
| taker_m8_p5_h4 | 1057 | 1594.54 | 1.23 | 0.50 | 3681 | -1829.27 | 0.95 | 1594.54 | -577.55 | -2846.26 | -3423.81 | False |
| taker_m24_p10_h4 | 1476 | 1396.01 | 1.14 | 0.50 | 5153 | -4645.98 | 0.91 | 1396.01 | -861.67 | -5180.32 | -6041.99 | False |
| taker_m8_p10_h4 | 1570 | 1284.83 | 1.12 | 0.49 | 5215 | -4498.44 | 0.91 | 1284.83 | -1413.65 | -4369.63 | -5783.28 | False |
| taker_m1_p10_h8 | 1627 | 1166.52 | 1.08 | 0.48 | 4968 | -3590.04 | 0.94 | 1166.52 | 327.65 | -5084.21 | -4756.56 | False |
| taker_m1_p5_h4 | 1502 | 566.94 | 1.06 | 0.49 | 5029 | -1934.58 | 0.96 | 566.94 | 503.46 | -3004.98 | -2501.52 | False |
| taker_m1_p10_h4 | 2240 | 553.59 | 1.04 | 0.48 | 6914 | -318.41 | 0.99 | 553.59 | 988.98 | -1860.98 | -872.00 | False |

### fixed-hold (maker)
best (fold-1 selected): `{'measure': 'm1', 'pct': 0.1, 'hold': 24}`

OOS (folds 2+3): n=1887 net=-1689.35 pf=0.96 wr=0.50 sharpe=-0.62 dd=6666.95 bps=-9.0 folds=[0.0, 1366.89, -3056.24]

| variant | is_n | is_net | is_pf | is_wr | n | net | pf | f1 | f2 | f3 | oos23 | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| maker_m1_p10_h24 | 934 | 5525.37 | 1.45 | 0.52 | 2821 | 3836.02 | 1.07 | 5525.37 | 1366.89 | -3056.24 | -1689.35 | True |
| maker_m1_p5_h24 | 700 | 4330.81 | 1.46 | 0.54 | 2234 | 1972.79 | 1.05 | 4330.81 | 1970.58 | -4328.61 | -2358.03 | False |
| maker_m1_p10_h48 | 640 | 3770.98 | 1.33 | 0.53 | 1911 | 3868.96 | 1.08 | 3770.98 | 1178.96 | -1080.99 | 97.98 | False |
| maker_m1_p5_h48 | 506 | 3381.13 | 1.37 | 0.54 | 1585 | 4638.38 | 1.12 | 3381.13 | 3163.81 | -1906.55 | 1257.25 | False |
| maker_m8_p10_h48 | 407 | 3227.91 | 1.43 | 0.57 | 1224 | -163.13 | 1.00 | 3227.91 | 372.85 | -3763.88 | -3391.03 | False |
| maker_m24_p10_h24 | 377 | 3136.57 | 1.62 | 0.56 | 1295 | -1223.47 | 0.96 | 3136.57 | 472.18 | -4832.22 | -4360.03 | False |
| maker_m8_p10_h24 | 555 | 2869.79 | 1.39 | 0.55 | 1734 | -1452.05 | 0.96 | 2869.79 | 537.49 | -4859.34 | -4321.85 | False |
| maker_m8_p5_h24 | 406 | 2603.06 | 1.46 | 0.53 | 1321 | 558.73 | 1.02 | 2603.06 | 914.76 | -2959.08 | -2044.33 | False |
| maker_m24_p10_h48 | 267 | 2590.72 | 1.56 | 0.61 | 855 | -225.76 | 0.99 | 2590.72 | 1748.78 | -4565.26 | -2816.48 | False |
| maker_m8_p5_h48 | 307 | 2550.10 | 1.45 | 0.57 | 973 | 132.36 | 1.00 | 2550.10 | 433.25 | -2850.99 | -2417.74 | False |
| maker_m24_p5_h24 | 281 | 2546.81 | 1.71 | 0.57 | 943 | -2535.57 | 0.89 | 2546.81 | 11.49 | -5093.87 | -5082.38 | False |
| maker_m24_p5_h8 | 614 | 2352.81 | 1.46 | 0.54 | 2126 | -2310.98 | 0.92 | 2352.81 | -376.06 | -4287.73 | -4663.79 | False |
| maker_m8_p10_h8 | 980 | 2129.96 | 1.26 | 0.51 | 3197 | -2732.35 | 0.93 | 2129.96 | -438.18 | -4424.13 | -4862.31 | False |
| maker_m8_p5_h8 | 669 | 2094.64 | 1.37 | 0.53 | 2308 | -1235.82 | 0.96 | 2094.64 | 60.07 | -3390.53 | -3330.46 | False |
| maker_m24_p5_h48 | 203 | 2062.16 | 1.58 | 0.59 | 665 | -2679.76 | 0.87 | 2062.16 | 581.17 | -5323.09 | -4741.93 | False |
| maker_m1_p5_h8 | 1111 | 1998.59 | 1.20 | 0.50 | 3673 | -1385.76 | 0.97 | 1998.59 | 791.48 | -4175.82 | -3384.35 | False |
| maker_m24_p10_h8 | 874 | 1977.38 | 1.25 | 0.52 | 2998 | -3356.76 | 0.92 | 1977.38 | -279.80 | -5054.34 | -5334.14 | False |
| maker_m24_p5_h4 | 1022 | 1716.84 | 1.26 | 0.52 | 3589 | -4544.66 | 0.87 | 1716.84 | -1305.80 | -4955.70 | -6261.50 | False |
| maker_m8_p5_h4 | 1049 | 1390.97 | 1.20 | 0.51 | 3650 | -2686.48 | 0.92 | 1390.97 | -989.02 | -3088.43 | -4077.45 | False |
| maker_m24_p10_h4 | 1469 | 1008.99 | 1.10 | 0.50 | 5106 | -7443.44 | 0.85 | 1008.99 | -2435.88 | -6016.55 | -8452.43 | False |
| maker_m1_p10_h8 | 1604 | 844.80 | 1.06 | 0.48 | 4884 | -4462.57 | 0.92 | 844.80 | -201.48 | -5105.89 | -5307.37 | False |
| maker_m8_p10_h4 | 1557 | 842.36 | 1.08 | 0.49 | 5177 | -5788.16 | 0.88 | 842.36 | -2249.84 | -4380.68 | -6630.51 | False |
| maker_m1_p5_h4 | 1466 | 417.73 | 1.04 | 0.48 | 4913 | -2123.69 | 0.95 | 417.73 | 360.33 | -2901.74 | -2541.42 | False |
| maker_m1_p10_h4 | 2197 | 277.67 | 1.02 | 0.48 | 6766 | -1534.63 | 0.97 | 277.67 | 164.39 | -1976.69 | -1812.30 | False |

### carry (exit on normalisation) (carry_taker)
best (fold-1 selected): `{'measure': 'm24', 'pct': 0.1}`

OOS (folds 2+3): n=360 net=-4805.60 pf=0.70 wr=0.53 sharpe=-2.12 dd=6418.30 bps=-133.5 folds=[0.0, -410.79, -4394.8]

| variant | is_n | is_net | is_pf | is_wr | n | net | pf | f1 | f2 | f3 | oos23 | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carry_taker_m24_p10_carry | 189 | 3080.27 | 1.84 | 0.63 | 549 | -1725.32 | 0.91 | 3080.27 | -410.79 | -4394.80 | -4805.60 | True |
| carry_taker_m8_p10_carry | 398 | 2768.16 | 1.53 | 0.57 | 1134 | -2503.46 | 0.90 | 2768.16 | -1082.04 | -4189.57 | -5271.61 | False |
| carry_taker_m24_p5_carry | 156 | 2691.56 | 1.91 | 0.64 | 460 | -1755.74 | 0.90 | 2691.56 | 348.49 | -4795.79 | -4447.30 | False |
| carry_taker_m8_p5_carry | 302 | 2412.33 | 1.61 | 0.58 | 902 | -2000.31 | 0.91 | 2412.33 | -328.07 | -4084.56 | -4412.63 | False |
| carry_taker_m1_p5_carry | 906 | 2322.70 | 1.34 | 0.54 | 2827 | -2363.13 | 0.93 | 2322.70 | 83.20 | -4769.03 | -4685.83 | False |
| carry_taker_m1_p10_carry | 1324 | 1509.47 | 1.16 | 0.52 | 3927 | -3566.19 | 0.91 | 1509.47 | -3.90 | -5071.77 | -5075.66 | False |

### carry (exit on normalisation) (carry_maker)
best (fold-1 selected): `{'measure': 'm24', 'pct': 0.1}`

OOS (folds 2+3): n=360 net=-4882.25 pf=0.69 wr=0.53 sharpe=-2.16 dd=6425.89 bps=-135.6 folds=[0.0, -485.57, -4396.68]

| variant | is_n | is_net | is_pf | is_wr | n | net | pf | f1 | f2 | f3 | oos23 | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carry_maker_m24_p10_carry | 188 | 3089.92 | 1.85 | 0.63 | 548 | -1792.33 | 0.91 | 3089.92 | -485.57 | -4396.68 | -4882.25 | True |
| carry_maker_m24_p5_carry | 156 | 2686.25 | 1.91 | 0.64 | 460 | -1899.32 | 0.89 | 2686.25 | 286.59 | -4872.17 | -4585.57 | False |
| carry_maker_m8_p10_carry | 398 | 2653.95 | 1.51 | 0.57 | 1134 | -2648.38 | 0.90 | 2653.95 | -1100.99 | -4201.33 | -5302.33 | False |
| carry_maker_m8_p5_carry | 301 | 2277.19 | 1.57 | 0.58 | 901 | -2301.68 | 0.89 | 2277.19 | -482.05 | -4096.81 | -4578.86 | False |
| carry_maker_m1_p5_carry | 884 | 2092.64 | 1.31 | 0.53 | 2758 | -2823.62 | 0.91 | 2092.64 | -206.84 | -4709.42 | -4916.26 | False |
| carry_maker_m1_p10_carry | 1303 | 1217.71 | 1.13 | 0.52 | 3845 | -4147.59 | 0.90 | 1217.71 | -263.02 | -5102.29 | -5365.30 | False |

## Sanity checks (taker, fixed-hold best params)

(a) Shuffle test (200 reps, random entry hours, same coins/sides/hold in OOS window): actual OOS net=-2254.05, null mean=-1678.02, null sd=2444.20, null p95=2400.00, p(null >= actual)=0.625

(b) OOS folds 2/3 (taker): 822.67 / -3076.72, n=999/912; maker: 1366.89 / -3056.24

(c) Neighbouring parameters (full-period folds; oos23 = folds 2+3):

| variant | dist | n | f1 | f2 | f3 | oos23 | pf |
|---|---|---|---|---|---|---|---|
| taker_m1_p10_h24 | 0 | 2856 | 5695.99 | 822.67 | -3076.72 | -2254.05 | 1.07 |
| taker_m1_p10_h4 | 1 | 6914 | 553.59 | 988.98 | -1860.98 | -872.00 | 0.99 |
| taker_m1_p10_h48 | 1 | 1928 | 3965.67 | 1282.29 | -1191.38 | 90.91 | 1.09 |
| taker_m1_p10_h8 | 1 | 4968 | 1166.52 | 327.65 | -5084.21 | -4756.56 | 0.94 |
| taker_m1_p5_h24 | 1 | 2277 | 4416.07 | 1745.67 | -4286.83 | -2541.15 | 1.04 |
| taker_m24_p10_h24 | 1 | 1299 | 3136.44 | 641.27 | -4728.08 | -4086.80 | 0.97 |
| taker_m8_p10_h24 | 1 | 1736 | 3162.17 | 662.59 | -4849.81 | -4187.22 | 0.97 |

(d) OOS per-coin breakdown (taker best):

| coin | n | net | funding | wr | vol24 | illiquid |
|---|---|---|---|---|---|---|
| HYPE | 46 | 638.83 | 8.17 | 0.61 | 733833530.95 | False |
| SPX | 51 | 594.71 | 13.30 | 0.55 | 1966096.84 | True |
| AERO | 59 | 526.63 | 22.05 | 0.49 | 1689452.42 | True |
| TAO | 37 | 437.04 | 10.23 | 0.54 | 9235680.00 | False |
| XPL | 35 | 423.07 | 4.83 | 0.63 | 11878006.58 | False |
| JTO | 41 | 420.02 | 26.78 | 0.54 | 2696377.19 | True |
| CASHCAT | 13 | 357.59 | 37.41 | 0.69 | 14979453.27 | False |
| HEMI | 29 | 307.72 | 38.64 | 0.55 | 275459.78 | True |
| MON | 44 | 286.50 | 18.77 | 0.43 | 3398457.00 | True |
| LINK | 19 | 232.70 | 7.25 | 0.68 | 9743041.21 | False |
| ETH | 16 | 200.15 | 1.07 | 0.56 | 1122005944.77 | False |
| JUP | 51 | 169.39 | 16.21 | 0.47 | 1673287.18 | True |
| ONDO | 33 | 155.82 | 4.53 | 0.48 | 7637812.53 | False |
| UNI | 26 | 142.18 | 5.39 | 0.50 | 7418239.92 | False |
| LIT | 60 | 78.48 | 18.64 | 0.52 | 24128078.69 | False |
| BTC | 18 | 76.16 | 2.18 | 0.61 | 2410019693.96 | False |
| GRASS | 37 | 75.48 | 28.06 | 0.49 | 1950512.68 | True |
| XMR | 67 | 69.07 | 56.14 | 0.48 | 6316130.60 | False |
| BNB | 32 | 63.98 | 3.75 | 0.50 | 5521732.16 | False |
| ZRO | 56 | 45.41 | 37.10 | 0.59 | 2536605.57 | True |
| WIF | 30 | 38.49 | 14.62 | 0.57 | 1331804.82 | True |
| PAXG | 14 | 28.58 | -0.11 | 0.50 | 5111069.14 | False |
| ASTER | 20 | 26.37 | 9.00 | 0.60 | 3575576.64 | True |
| AVAX | 44 | 20.78 | 8.00 | 0.64 | 3996530.11 | True |
| GRAM | 14 | 2.27 | 7.70 | 0.36 | 3176846.03 | True |
| WLD | 44 | -24.31 | 18.39 | 0.57 | 13658054.96 | False |
| PURR | 59 | -32.40 | 63.34 | 0.58 | 609595.69 | True |
| LTC | 25 | -35.67 | 5.16 | 0.44 | 3410088.01 | True |
| TRX | 30 | -36.65 | 33.83 | 0.47 | 2748085.18 | True |
| SUI | 36 | -43.93 | 6.93 | 0.47 | 15537733.84 | False |
| PUMP | 38 | -57.95 | 9.86 | 0.55 | 19351660.83 | False |
| DOGE | 29 | -69.53 | 4.26 | 0.45 | 14560117.02 | False |
| SOL | 35 | -117.23 | 6.38 | 0.43 | 258254595.86 | False |
| CC | 50 | -129.51 | 12.29 | 0.52 | 707510.87 | True |
| FET | 35 | -170.85 | 12.11 | 0.54 | 1709907.80 | True |
| ETHFI | 27 | -202.79 | 12.52 | 0.41 | 2290916.93 | True |
| XRP | 38 | -227.19 | 6.52 | 0.34 | 38555353.89 | False |
| FARTCOIN | 46 | -278.03 | 26.35 | 0.50 | 10939305.64 | False |
| AAVE | 39 | -302.20 | 8.38 | 0.51 | 11145367.99 | False |
| ADA | 50 | -356.98 | 19.29 | 0.46 | 5225164.93 | False |
| TRUMP | 39 | -364.62 | 47.25 | 0.49 | 3136074.06 | True |
| CRV | 40 | -380.65 | 9.56 | 0.42 | 3809210.46 | True |
| CHIP | 33 | -422.32 | 50.91 | 0.36 | 2197226.47 | True |
| PENGU | 43 | -434.32 | 16.06 | 0.37 | 2434910.11 | True |
| kPEPE | 36 | -436.86 | 6.68 | 0.47 | 10450751.18 | False |
| NEAR | 38 | -527.56 | 13.21 | 0.47 | 29088398.92 | False |
| INJ | 51 | -592.94 | 21.92 | 0.33 | 2080448.36 | True |
| ZEC | 60 | -596.10 | 30.55 | 0.47 | 176526195.50 | False |
| ENA | 39 | -598.29 | 4.68 | 0.41 | 7897140.21 | False |
| VVV | 59 | -1232.59 | 57.47 | 0.37 | 12356060.84 | False |

Liquidity split (median 24h notional at signal < $5M = illiquid):

| illiquid | coins | n | net |
|---|---|---|---|
| False | 27 | 1003 | -1965.10 |
| True | 23 | 908 | -288.94 |

Attribution (OOS): price-only gross=-1433.40, funding=903.59, fees=1724.24, net=-2254.05

| side | n | net | funding |
|---|---|---|---|
| -1.00 | 780.00 | -5588.32 | 656.57 |
| 1.00 | 1131.00 | 3334.27 | 247.02 |

Liquid-only OOS (24h vol >= $5M at signal): n=1010 net=-2388.84 pf=0.90 wr=0.49 sharpe=-1.06 dd=5544.54 bps=-23.7 folds=[0.0, 438.2, -2827.04]


(e) Strict 1-bar-lag entry (fill at open[H+1h]) on best params, full period: n=2855 net=3301.68 pf=1.06 wr=0.51 sharpe=1.08 dd=6712.75 bps=11.6 folds=[4682.22, 1332.3, -2712.84]

(f) Price-only (funding NOT credited), best params, full period: n=2856 net=2050.57 pf=1.04 wr=0.50 sharpe=0.66 dd=6791.21 bps=7.2 folds=[5208.22, 352.81, -3510.45]


## Verdict: **none**

criteria: `{'net_pos': False, 'pf': False, 'n': True, 'folds': False, 'shuffle': False, 'neighbors': False}`

## Diagnostics (tests/h_funding_extreme_diag.py; taker, m1 / top-bottom 10% / 24h)

Funding per trade: **$0.49** collected on $1,000 notional (4.9 bps) vs **$0.90** taker fees (9 bps). Funding income can never pay the round trip at 4-48h holds; PnL is ~95% price.

Side x fold net (n): fold1 short +2786 (188) / long +2910 (757); fold2 short -115 (331) / long +938 (668); fold3 short -5473 (449) / long +2397 (463).
Universe mean 24h forward return per fold: +0.12% / +0.01% / +0.60% - fold 3 was a drifting-up market and the short side was run over.

|measure| bucket (bps/h) x fold net: <0.25: +1579/-1270/+810 ; 0.25-0.5: +2885/+1111/-1124 ; 0.5-1: +439/+242/-2384 ; 1-2: +866/+763/-1034 ; 2-5: -75/-133/-82 ; >5: +2/+111/+737 (n=6/8/8).
Absolute filters on top of rank: |m1|>1bps n=318 net=+1154 folds[+793,+740,-379]; >2bps n=94 net=+559 folds[-73,-22,+655]; >5bps n=22 net=+849 (too few to say anything).

Long-only OOS (folds 2+3): n=1131 net=+3334 pf=1.19 - but a shuffle of the same longs to random hours in the same coins gives null mean +1988, sd 1710, p=0.23 -> indistinguishable from market beta.
Short-only OOS: n=780 net=-5588 pf=0.76; random-hour shorts null mean -3776, p=0.84 -> worse than random.

## Interpretation

* No out-of-sample edge. The fold-1 selected cell (m1, 10%, 24h) loses -$2,254 on 1,911 OOS trades (PF 0.94); maker entry does not rescue it (-$1,689); the carry/exit-on-normalisation version is worse (-$4,806, PF 0.70).
* Every one of the 24 cells is profitable in fold 1 (Mar-Apr) and 22/24 lose in fold 3 (Jul-Aug). The sign flips with the calendar, not with parameters - the in-sample table is a regime artefact, and walk-forward exposed it.
* The shuffle test cannot separate the strategy from random-hour trades of the same coins/sides (p=0.63); neighbours are 1/7 positive OOS.
* Economic reason: on Hyperliquid the hourly funding clamp means "extreme" is usually only 0.25-2 bps/h. Over 24h that is 6-50 bps of carry against 9 bps of taker fees and 3-4% of daily price noise. The funding print is dominated by price, and the contrarian price bet has no edge on its own.
* Liquidity: OOS losses are larger in liquid names (-$1,965 across 27 coins with >=$5M/24h) than in illiquid ones (-$289 across 23) - the losses are not an artefact of thin books, and there is no hidden profit pocket in illiquid names either.
* Strict 1-bar-lag entry gives the same picture (full-period net +3302 with fold 3 -2713), so the result is not sensitive to the ms timestamp convention.
