# funding_xsec_carry - dollar-neutral cross-sectional funding carry, point-in-time HL universe

Data: 194 HL perps with 1h data in 2026-01-31 -> 2026-08-27 (listed + delisted), hourly funding for all but ['BIGTIME', 'BLAST', 'DYM', 'ENS', 'ETC', 'FOGO', 'FTT', 'GALA', 'GAS', 'GMX', 'GOAT', 'GRIFFAIN', 'HBAR', 'IMX', 'IO', 'IOTA', 'KAS', 'LINEA', 'MAV', 'MAVIA', 'MEME', 'MERL', 'MEW', 'MINA', 'MNT', 'MOODENG', 'MOVE', 'NEO', 'NOT', 'NXPC', 'PEOPLE', 'POLYX', 'POPCAT', 'PROMPT', 'REZ', 'RSR', 'RUNE', 'S', 'SAGA', 'SAND', 'SCR', 'SKY', 'SNX', 'SOPH', 'STBL', 'SUPER', 'SUSHI', 'SYRUP', 'TRB', 'TURBO', 'UMA', 'USTC', 'USUAL', 'VINE', 'W', 'WCT', 'XAI', 'YZY', 'ZEN', 'ZEREBRO', 'ZETA', 'kFLOKI', 'kLUNC', 'kNEIRO']. Folds: [('2026-01-31', '2026-04-10'), ('2026-04-10', '2026-06-19'), ('2026-06-19', '2026-08-27')] (~69d each).

Universe at each 00:00 signal: trailing-24h USD vol >= $5M, >= 30 daily closes, funding history present. Eligible/day min 0 mean 23.9 max 51; 117 coins ever eligible (50 in the snapshot-50). Mean trailing-24h funding of the top-3 / bottom-3 names: 0.29 / -1.83 bps/h.

Signal: trailing-W-hour mean hourly funding using rows paid <= 23:00 of D-1; LONG bottom-q, SHORT top-q, $1,000/name, hold while in decile, hard exit at H days, exit on 24h funding sign flip, settle at last close on delisting. Maker arm: limit at the 00:00 open filled only if the bar trades through by >= 1 tick (else entry skipped / exit taker at bar close). Taker arm: fill at the open, taker both sides. Funding accrued hourly on mark notional, folded into exit_px.

## Headline (walk-forward OOS, folds 2+3, maker arm)

Selected on fold 1: `{'q': 0.1, 'W': 72, 'H': 3, 'exec': 'maker'}`

| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 | price | funding | fees |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 348 | -1865.95 | 0.83 | 0.48 | -1.05 | 2616.0 | -53.6 | -469.74 | -1396.21 | -2486.9 | 728.4 | 107.5 |

Taker arm (own walk-forward): selected `{'q': 0.1, 'W': 72, 'H': 3, 'exec': 'taker'}` -> n=353 net=-1969.91 pf=0.83 wr=0.48 sharpe=-1.10 dd=2827.79 bps=-55.8 folds=[0.0, -612.23, -1357.68]

### Legs (OOS)

| leg | n | net | pf | wr | fold2 | fold3 | price | funding | fees |
|---|---|---|---|---|---|---|---|---|---|
| long | 205 | -1436.50 | 0.74 | 0.42 | -1028.03 | -408.47 | -1867.8 | 494.6 | 63.3 |
| short | 143 | -429.45 | 0.92 | 0.57 | 558.29 | -987.74 | -619.1 | 233.9 | 44.2 |

Ex-top-3 names (['ZRO', 'MEGA', 'WLD']): n=323 net=-2886.89 pf=0.74 wr=0.47 sharpe=-1.67 dd=3294.69 bps=-89.4 folds=[0.0, -1270.05, -1616.84]

Daily book (mark-to-market at 00:00 opens), OOS days: n=139 mean=-13.42 USD/day sd=156.48 t=-1.01; t by fold {0: 0.95, 1: -0.39, 2: -1.02}.

Alt-beta regression of daily book PnL on the EW liquid-alt basket (OOS, HAC): alpha=-12.10 USD/day (t=-1.10), beta=-12.99 USD per 1% basket move (t=-2.70), R2=0.077.

Exit reasons (OOS):

| exit_reason | n | net | hold |
|---|---|---|---|
| bucket | 202 | -1356.21 | 1.23 |
| delist | 1 | 45.12 | 2.00 |
| end | 3 | 89.95 | 1.00 |
| flip | 78 | 2162.34 | 1.15 |
| maxhold | 64 | -2807.15 | 3.00 |

Hold days (OOS):

| hold_days | n | net | funding |
|---|---|---|---|
| 1.00 | 224.00 | -534.04 | 173.05 |
| 2.00 | 60.00 | 1475.24 | 57.66 |
| 3.00 | 64.00 | -2807.15 | 497.71 |

## In-sample grid (fold 1) with fold 2/3 nets - maker arm

| name | is_n | is_net | is_pf | is_wr | oos_n | oos_net | oos_pf | f1 | f2 | f3 | full_net | oos_price | oos_fund | oos_fees | avg_elig | avg_long | avg_short | skip | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| maker_q0.1_W72_H3 | 155 | 1243.10 | 1.29 | 0.47 | 348 | -1865.95 | 0.83 | 1243.10 | -469.74 | -1396.21 | -622.85 | -2486.90 | 728.40 | 107.50 | 23.70 | 1.89 | 1.88 | 0.03 | True |
| maker_q0.1_W72_H7 | 139 | 1005.69 | 1.28 | 0.48 | 320 | -1975.23 | 0.82 | 1005.69 | -513.74 | -1461.48 | -969.53 | -2602.10 | 725.70 | 98.80 | 23.70 | 1.89 | 1.89 | 0.03 | False |
| maker_q0.1_W24_H3 | 177 | 565.55 | 1.11 | 0.53 | 396 | -1350.45 | 0.88 | 565.55 | -788.17 | -562.28 | -784.90 | -2046.00 | 816.00 | 120.40 | 23.90 | 1.92 | 1.92 | 0.02 | False |
| maker_q0.1_W24_H7 | 167 | 476.12 | 1.10 | 0.53 | 377 | -1231.16 | 0.89 | 476.12 | -757.20 | -473.97 | -755.04 | -1924.20 | 807.70 | 114.70 | 23.90 | 1.92 | 1.92 | 0.02 | False |
| maker_q0.2_W72_H3 | 311 | 435.52 | 1.05 | 0.49 | 763 | -4155.12 | 0.82 | 435.52 | -2711.72 | -1443.39 | -3719.59 | -4864.90 | 944.30 | 234.50 | 23.70 | 4.27 | 4.26 | 0.02 | False |
| maker_q0.2_W72_H7 | 270 | 341.11 | 1.05 | 0.50 | 681 | -4109.25 | 0.80 | 341.11 | -2668.33 | -1440.92 | -3768.14 | -4839.20 | 939.20 | 209.30 | 23.70 | 4.27 | 4.29 | 0.02 | False |
| maker_q0.2_W8_H3 | 374 | -121.34 | 0.99 | 0.49 | 904 | -5553.27 | 0.77 | -121.34 | -3322.24 | -2231.02 | -5674.60 | -6276.60 | 999.90 | 276.60 | 23.90 | 4.29 | 4.32 | 0.02 | False |
| maker_q0.2_W8_H7 | 352 | -257.82 | 0.97 | 0.50 | 859 | -5414.67 | 0.77 | -257.82 | -3205.94 | -2208.74 | -5672.50 | -6140.70 | 989.10 | 263.10 | 23.90 | 4.29 | 4.34 | 0.02 | False |
| maker_q0.1_W8_H7 | 176 | -282.36 | 0.95 | 0.51 | 398 | -2114.34 | 0.82 | -282.36 | -1176.16 | -938.18 | -2396.70 | -2825.40 | 832.00 | 121.00 | 23.90 | 1.90 | 1.92 | 0.02 | False |
| maker_q0.1_W8_H3 | 185 | -282.54 | 0.95 | 0.50 | 409 | -2154.94 | 0.82 | -282.54 | -1181.36 | -973.58 | -2437.47 | -2870.50 | 839.90 | 124.30 | 23.90 | 1.90 | 1.92 | 0.02 | False |
| maker_q0.2_W24_H3 | 364 | -787.60 | 0.93 | 0.47 | 821 | -4106.42 | 0.82 | -787.60 | -2214.29 | -1892.13 | -4894.02 | -4847.80 | 995.20 | 253.80 | 23.90 | 4.30 | 4.32 | 0.02 | False |
| maker_q0.2_W24_H7 | 338 | -1090.52 | 0.89 | 0.49 | 761 | -3924.31 | 0.81 | -1090.52 | -2127.37 | -1796.93 | -5014.83 | -4675.60 | 986.80 | 235.50 | 23.90 | 4.31 | 4.33 | 0.02 | False |

## In-sample grid (fold 1) with fold 2/3 nets - taker arm

| name | is_n | is_net | is_pf | is_wr | oos_n | oos_net | oos_pf | f1 | f2 | f3 | full_net | oos_price | oos_fund | oos_fees | avg_elig | avg_long | avg_short | skip | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| taker_q0.1_W72_H3 | 160 | 1194.99 | 1.28 | 0.47 | 353 | -1969.91 | 0.83 | 1194.99 | -612.23 | -1357.68 | -774.92 | -2381.60 | 728.80 | 317.10 | 23.70 | 1.92 | 1.92 | 0.00 | True |
| taker_q0.1_W72_H7 | 144 | 983.55 | 1.27 | 0.48 | 324 | -2089.07 | 0.81 | 983.55 | -647.25 | -1441.82 | -1105.52 | -2524.00 | 726.00 | 291.00 | 23.70 | 1.92 | 1.92 | 0.00 | False |
| taker_q0.1_W24_H3 | 179 | 531.26 | 1.11 | 0.53 | 403 | -1257.38 | 0.89 | 531.26 | -718.58 | -538.80 | -726.12 | -1714.00 | 818.40 | 361.80 | 23.90 | 1.95 | 1.95 | 0.00 | False |
| taker_q0.1_W24_H7 | 169 | 447.85 | 1.09 | 0.53 | 383 | -1214.58 | 0.89 | 447.85 | -682.20 | -532.38 | -766.73 | -1681.30 | 810.50 | 343.80 | 23.90 | 1.95 | 1.95 | 0.00 | False |
| taker_q0.2_W72_H3 | 317 | 399.96 | 1.05 | 0.48 | 777 | -3985.95 | 0.83 | 399.96 | -2648.16 | -1337.79 | -3585.99 | -4236.20 | 948.70 | 698.50 | 23.70 | 4.33 | 4.33 | 0.00 | False |
| taker_q0.2_W72_H7 | 275 | 260.34 | 1.03 | 0.49 | 692 | -3956.13 | 0.81 | 260.34 | -2586.29 | -1369.84 | -3695.79 | -4277.10 | 943.00 | 622.00 | 23.70 | 4.33 | 4.33 | 0.00 | False |
| taker_q0.2_W8_H3 | 381 | -149.00 | 0.99 | 0.49 | 925 | -5406.51 | 0.78 | -149.00 | -3120.53 | -2285.98 | -5555.50 | -5582.60 | 1007.30 | 831.20 | 23.90 | 4.38 | 4.38 | 0.00 | False |
| taker_q0.1_W8_H3 | 188 | -208.15 | 0.96 | 0.51 | 419 | -2195.11 | 0.82 | -208.15 | -1218.91 | -976.19 | -2403.26 | -2663.90 | 844.50 | 375.80 | 23.90 | 1.95 | 1.95 | 0.00 | False |
| taker_q0.1_W8_H7 | 179 | -212.02 | 0.96 | 0.51 | 408 | -2147.93 | 0.82 | -212.02 | -1210.11 | -937.81 | -2359.94 | -2618.70 | 836.60 | 365.90 | 23.90 | 1.95 | 1.95 | 0.00 | False |
| taker_q0.2_W8_H7 | 357 | -288.71 | 0.97 | 0.50 | 879 | -5300.29 | 0.77 | -288.71 | -3049.78 | -2250.51 | -5588.99 | -5506.80 | 996.30 | 789.80 | 23.90 | 4.38 | 4.38 | 0.00 | False |
| taker_q0.2_W24_H3 | 369 | -771.62 | 0.93 | 0.47 | 839 | -3873.73 | 0.83 | -771.62 | -2152.61 | -1721.11 | -4645.34 | -4119.80 | 1000.00 | 753.90 | 23.90 | 4.38 | 4.38 | 0.00 | False |
| taker_q0.2_W24_H7 | 342 | -1037.49 | 0.89 | 0.48 | 777 | -3771.35 | 0.82 | -1037.49 | -2049.32 | -1722.03 | -4808.84 | -4065.00 | 991.70 | 698.10 | 23.90 | 4.38 | 4.38 | 0.00 | False |

## Sanity checks

- (a) Shuffle (200 reps; each day the funding signals are permuted across the eligible coins, same book mechanics): null mean -538.50, sd 1145.85, p95 1348.39; actual -1865.95; P(null >= actual) = 0.895.
- (b) OOS folds: fold2 -469.74, fold3 -1396.21 (n 186/162).
- (c) Neighbours (one parameter changed): 0/4 positive OOS net.

| name | oos_n | oos_net | oos_pf | f2 | f3 |
|---|---|---|---|---|---|
| maker_q0.2_W72_H3 | 763 | -4155.12 | 0.82 | -2711.72 | -1443.39 |
| maker_q0.1_W8_H3 | 409 | -2154.94 | 0.82 | -1181.36 | -973.58 |
| maker_q0.1_W24_H3 | 396 | -1350.45 | 0.88 | -788.17 | -562.28 |
| maker_q0.1_W72_H7 | 320 | -1975.23 | 0.82 | -513.74 | -1461.48 |

- (d) Per-coin OOS (best maker):

| instrument | n | net | price | funding | wr | vol24 |
|---|---|---|---|---|---|---|
| ZRO | 7 | 460.36 | 458.59 | 4.37 | 0.71 | 6032309.25 |
| MEGA | 5 | 301.28 | 303.27 | -0.53 | 0.80 | 11023441.58 |
| WLD | 13 | 259.30 | 254.41 | 8.84 | 0.62 | 9230070.09 |
| kPEPE | 5 | 254.98 | 256.25 | 0.53 | 0.80 | 10072009.75 |
| SUI | 9 | 232.14 | 234.21 | 0.68 | 0.56 | 14631247.66 |
| TON | 7 | 206.19 | 207.29 | 1.32 | 0.71 | 24593473.72 |
| TAO | 5 | 187.56 | 187.05 | 1.99 | 0.60 | 11271488.21 |
| HYPE | 9 | 174.11 | 172.94 | 3.81 | 0.44 | 545890189.85 |
| BIO | 7 | 162.80 | 155.67 | 9.22 | 0.29 | 5976160.15 |
| XMR | 26 | 142.65 | 87.31 | 63.13 | 0.58 | 9025607.40 |
| LINK | 1 | 120.19 | 122.23 | -1.72 | 1.00 | 24981890.07 |
| GRASS | 1 | 105.53 | 105.28 | 0.54 | 1.00 | 6145093.39 |
| MON | 7 | 87.44 | 89.77 | 0.05 | 0.43 | 6187311.77 |
| EIGEN | 1 | 84.09 | 84.01 | 0.37 | 1.00 | 12900827.66 |
| WLFI | 6 | 80.70 | 80.68 | 1.84 | 0.67 | 6442831.44 |
| AZTEC | 1 | 71.39 | 70.36 | 1.32 | 1.00 | 8952992.32 |
| XPL | 1 | 70.84 | 70.92 | 0.21 | 1.00 | 16253243.46 |
| LIT | 13 | 63.58 | 58.32 | 9.16 | 0.38 | 24096677.47 |
| ARB | 5 | 39.50 | 41.56 | -0.55 | 0.80 | 5720350.50 |
| FET | 1 | 35.75 | 35.64 | 0.41 | 1.00 | 9313768.37 |
| JUP | 2 | 35.65 | 36.71 | -0.46 | 0.50 | 7123666.11 |
| TRX | 5 | 27.73 | 24.55 | 4.69 | 0.60 | 6824240.15 |
| SPX | 1 | 25.40 | 25.40 | 0.30 | 1.00 | 5323859.56 |
| NEAR | 7 | 23.53 | 20.23 | 5.40 | 0.57 | 19087329.56 |
| AVAX | 2 | 19.16 | 19.49 | 0.27 | 0.50 | 11656996.37 |
| APT | 1 | 9.51 | 10.12 | -0.31 | 1.00 | 5252323.33 |
| PYTH | 1 | 7.24 | 5.40 | 2.14 | 1.00 | 9854715.14 |
| AAVE | 3 | 5.16 | 5.54 | 0.52 | 0.67 | 13068650.33 |
| BCH | 7 | 3.78 | 6.40 | -0.52 | 0.43 | 5989331.15 |
| ASTER | 2 | 3.25 | 3.25 | 0.60 | 0.50 | 15426408.43 |
| BNB | 2 | 0.31 | 1.07 | -0.16 | 0.50 | 9372892.67 |
| AERO | 4 | -1.50 | -2.32 | 2.01 | 0.50 | 6318426.90 |
| LDO | 1 | -2.73 | -2.74 | 0.31 | 0.00 | 5195530.44 |
| MELANIA | 1 | -5.14 | -4.54 | -0.30 | 0.00 | 5079662.81 |
| STX | 1 | -5.28 | -5.54 | 0.55 | 0.00 | 6873900.97 |
| INJ | 2 | -5.83 | -5.12 | -0.11 | 0.50 | 13256119.87 |
| WIF | 1 | -7.41 | -6.88 | -0.23 | 0.00 | 15046194.87 |
| CRV | 1 | -9.55 | -8.97 | -0.28 | 0.00 | 11896277.87 |
| UNI | 2 | -14.66 | -14.66 | 0.60 | 0.50 | 10076912.38 |
| PENGU | 3 | -14.67 | -13.71 | -0.06 | 0.67 | 5738996.60 |
| BLUR | 2 | -15.20 | -28.97 | 14.37 | 0.50 | 9749520.07 |
| BTC | 7 | -15.78 | -12.26 | -1.43 | 0.43 | 2536882697.51 |
| DASH | 3 | -18.83 | -18.34 | 0.70 | 0.67 | 5568976.75 |
| CHIP | 1 | -24.33 | -23.86 | -0.17 | 0.00 | 5627428.35 |
| ONDO | 2 | -29.12 | -28.26 | 0.03 | 0.50 | 10157512.47 |
| XRP | 6 | -35.15 | -33.56 | 0.21 | 0.50 | 31534288.91 |
| kBONK | 6 | -42.42 | -47.58 | 7.23 | 0.33 | 8504755.01 |
| ACE | 3 | -43.33 | -193.37 | 150.92 | 0.33 | 8255230.30 |
| ETH | 4 | -47.46 | -46.11 | -0.16 | 0.50 | 1777393135.33 |
| MET | 1 | -47.80 | -47.27 | -0.24 | 0.00 | 13407887.40 |
| NIL | 2 | -54.76 | -57.50 | 3.27 | 0.50 | 10445169.84 |
| VIRTUAL | 2 | -60.50 | -59.31 | -0.60 | 0.00 | 9206611.52 |
| TNSR | 1 | -62.58 | -80.61 | 18.32 | 0.00 | 5826271.54 |
| BABY | 1 | -62.65 | -72.08 | 9.71 | 0.00 | 6236018.18 |
| DOT | 3 | -64.17 | -67.24 | 3.96 | 0.33 | 5808522.31 |
| GMT | 1 | -64.20 | -71.30 | 7.39 | 0.00 | 15816089.04 |
| LAYER | 1 | -73.75 | -78.73 | 5.27 | 0.00 | 5769211.35 |
| TRUMP | 10 | -73.77 | -86.02 | 15.23 | 0.20 | 8307587.96 |
| ZEC | 14 | -79.67 | -93.89 | 18.51 | 0.43 | 122633730.02 |
| HMSTR | 1 | -83.25 | -83.09 | 0.13 | 0.00 | 6183314.89 |
| SOL | 7 | -88.46 | -86.10 | -0.27 | 0.43 | 346351568.59 |
| kSHIB | 1 | -90.32 | -89.80 | -0.24 | 0.00 | 43176930.96 |
| STABLE | 3 | -106.29 | -115.90 | 10.49 | 0.33 | 5376548.51 |
| PUMP | 2 | -108.64 | -109.47 | 1.45 | 0.50 | 45556828.70 |
| JTO | 5 | -114.97 | -117.71 | 4.22 | 0.20 | 8381044.25 |
| FARTCOIN | 16 | -116.31 | -128.54 | 17.35 | 0.56 | 10830105.60 |
| XLM | 4 | -122.76 | -122.39 | 0.81 | 0.50 | 9317721.26 |
| PROVE | 1 | -139.97 | -153.30 | 13.61 | 0.00 | 7126869.35 |
| APE | 3 | -155.44 | -156.91 | 2.34 | 0.00 | 10934472.69 |
| ADA | 13 | -162.53 | -164.60 | 6.25 | 0.38 | 6616621.04 |
| KAITO | 7 | -305.49 | -459.16 | 155.66 | 0.43 | 12107001.99 |
| PURR | 6 | -355.76 | -377.37 | 23.46 | 0.50 | 5880445.72 |
| VVV | 23 | -481.35 | -518.27 | 43.83 | 0.48 | 9919004.05 |
| TST | 1 | -806.02 | -839.83 | 34.24 | 0.00 | 9626567.90 |
| CASHCAT | 6 | -947.30 | -987.63 | 42.62 | 0.33 | 12457895.84 |

Thin split (24h vol < $10M at entry; all >= $5M by construction): {'n': {False: 174, True: 174}, 'net': {False: -985.9977498925138, True: -879.9527174547156}}

Realised carry per name-hour (OOS): 0.57 bps/h = 13.6 bps per name-day vs 3 bps maker round trip.

Post-hoc diagnostic (not a result): OOS net by |entry funding| bucket (bps/h) x leg:

| score_bucket | leg | n | net | price | funding |
|---|---|---|---|---|---|
| <0.5 | long | 162 | 130.60 | 141.20 | 40.10 |
| <0.5 | short | 113 | 1749.40 | 1686.20 | 97.40 |
| 0.5-1 | long | 17 | -88.20 | -112.40 | 29.40 |
| 0.5-1 | short | 23 | -59.80 | -114.40 | 62.20 |
| 1-2 | long | 8 | -260.00 | -273.70 | 16.00 |
| 1-2 | short | 7 | -2119.00 | -2190.90 | 74.30 |
| 2-5 | long | 9 | -617.50 | -644.80 | 29.90 |
| >5 | long | 9 | -601.30 | -978.00 | 379.20 |
Universe controls (best params, OOS folds 2+3):

| universe | avg elig | n | net | pf | fold2 | fold3 | price | funding | fees |
|---|---|---|---|---|---|---|---|---|---|
| snap50 | 21.4 | 308 | -825.47 | 0.90 | -16.06 | -809.41 | -999.2 | 268.7 | 95.0 |
| liq2m | 40.2 | 566 | -3907.52 | 0.80 | -1610.98 | -2296.53 | -5175.7 | 1440.8 | 172.6 |
| liq20m | 9.3 | 144 | -102.90 | 0.97 | 503.11 | -606.01 | -321.3 | 261.9 | 43.5 |

## Verdict: **none**

criteria: `{'net_pos': False, 'pf': False, 'n': True, 'folds': False, 'shuffle': False, 'neighbors': False}`

## Interpretation

* **No out-of-sample edge, in either execution arm.** The fold-1-selected cell (q=0.1, W=72h, H=3d, maker) loses -$1,866 on 348 OOS trades (PF 0.83, both OOS folds negative, daily-book t = -1.01). All 24 grid cells (12 maker + 12 taker) lose in folds 2+3; the taker arm is within $100 of the maker arm because the maker entry rule (bar trades through the open by >= 1 tick) is almost always satisfied on hourly bars (skip rate 2-3%), so execution mode is not what decides this.
* **The carry/price decomposition kills the hypothesis on its own terms.** Realised carry is 0.57 bps per name-hour = 13.6 bps per name-day, comfortably above the 3 bps maker round trip (OOS funding +$728 vs fees $108), so the first condition holds. But the price component is -$2,487 (-$1,868 on the longs, -$619 on the shorts), i.e. **funding is fair compensation for price drift, not a free premium**: the names paying the most negative funding keep falling and the names with the highest positive funding keep rising, faster than the funding they pay. Every one of the 24 cells shows the same sign pattern OOS (funding +$0.7-1.0k, price -$1.7k to -$6.3k).
* The result is **not driven by three names** (ex-ZRO/MEGA/WLD is worse, -$2,887), not by illiquid names (thin < $10M: -$880 on 174 trades vs -$986 on 174 trades >= $10M; the $20M-gate version is only marginally less negative, -$103 on 144 trades, and the $2M-gate version is worse, -$3,999), and not by survivorship (snapshot-50 hindsight universe: -$825).
* **Beta**: the book is dollar-neutral but not factor-neutral: beta to the EW liquid-alt basket is -$13 per 1% basket move (t = -2.7), i.e. it is short the alt-momentum/positioning factor, which is exactly what buying the collapsing names and selling the squeezing names produces.
* **Where the losses live (post-hoc diagnostic, not a result)**: trades entered at mild funding (|f| < 0.5 bps/h, 275 trades) were slightly positive (+$1,880, almost all price on the short leg in fold 2); trades entered at |f| >= 1 bps/h (40 trades) lost -$3,600, i.e. -$90 per $1,000 position, with price running WITH the funding sign. Positions that survived to the 3-day hard exit (funding persisted) lost -$2,807 on 64 trades, whereas the 78 exits triggered by a 24h funding sign flip made +$2,162. Persistent extreme funding = persistent trend; the carry trade is the wrong side of it.
* Together with round 1 (funding_extreme, single-coin contrarian: 95% price) this closes the "funding as a payoff" family on Hyperliquid at 1-7 day horizons: the funding clamp keeps carry at ~10-15 bps/day while the associated price drift is several times larger and in the wrong direction for the carry receiver.
