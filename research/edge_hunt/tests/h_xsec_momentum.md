# h_xsec_momentum - cross-sectional momentum / reversal, Hyperliquid universe

Data: 50 HL perps, 1h candles 2026-01-31 -> 2026-08-27 (universe = current top-50 by volume snapshot -> **survivorship-biased toward today's winners**). Folds: [('2026-01-31', '2026-04-10'), ('2026-04-10', '2026-06-19'), ('2026-06-19', '2026-08-27')].

Execution: signal = trailing L-day return of the 23:00-bar close; fill at next (00:00) bar OPEN; equal $1000/name; long top q / short bottom q; hold to next rebalance; positions kept when bucket unchanged. Fees: HL taker 4.5 bps/side both legs. Funding: hourly history, longs pay positive funding, folded into exit price.

## Headline (walk-forward OOS, folds 2+3)

Selected on fold 1: `{'lookback_d': 30, 'rebal_d': 1, 'quantile': 0.1, 'mode': 'mom'}`

| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |
|---|---|---|---|---|---|---|---|---|
| 231 | -178.20 | 0.98 | 0.43 | -0.07 | 2321.2 | -7.7 | -49.15 | -129.05 |

Turnover per rebalance (fraction of book changed): 0.19; rebalances: 208; full-period net per rebalance: 4.04 USD on a ~$10000 gross book.

## In-sample grid (fold 1) with fold 2/3 nets for sensitivity

| name | is_n | is_net | is_pf | oos_n | oos_net | oos_pf | f1 | f2 | f3 | full_net | turnover | n_rebal | net_per_rebal | fees | funding | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1_R1_q0.1_mom | 464 | -1208.52 | 0.89 | 990 | 798.35 | 1.03 | -1208.52 | 1182.08 | -383.74 | -410.17 | 0.84 | 208 | -1.97 | 1311.69 | -8.32 | False |
| L1_R1_q0.1_rev | 464 | 372.34 | 1.04 | 990 | -2585.55 | 0.9 | 372.34 | -2014.99 | -570.56 | -2213.21 | 0.84 | 208 | -10.64 | 1311.69 | 8.32 | False |
| L1_R1_q0.2_mom | 934 | -2510.6 | 0.88 | 1931 | -611.16 | 0.99 | -2510.6 | 510.02 | -1121.18 | -3121.76 | 0.75 | 208 | -15.01 | 2584.72 | -113.82 | False |
| L1_R1_q0.2_rev | 934 | 827.47 | 1.04 | 1931 | -2875.14 | 0.93 | 827.47 | -2207.25 | -667.9 | -2047.68 | 0.75 | 208 | -9.84 | 2584.72 | 113.82 | False |
| L1_R7_q0.1_mom | 67 | -1132.09 | 0.73 | 157 | -1884.45 | 0.82 | -1132.09 | 388.03 | -2272.49 | -3016.54 | 0.91 | 30 | -100.55 | 203.76 | 8.26 | False |
| L1_R7_q0.1_rev | 67 | 1010.19 | 1.32 | 157 | 1598.83 | 1.18 | 1010.19 | -519.32 | 2118.15 | 2609.02 | 0.91 | 30 | 86.97 | 203.76 | -8.26 | False |
| L1_R7_q0.2_mom | 131 | -760.22 | 0.88 | 299 | -5567.57 | 0.73 | -760.22 | -1359.46 | -4208.11 | -6327.79 | 0.8 | 30 | -210.93 | 391.73 | -155.22 | False |
| L1_R7_q0.2_rev | 131 | 522.4 | 1.09 | 299 | 5021.93 | 1.33 | 522.4 | 1096.1 | 3925.83 | 5544.33 | 0.8 | 30 | 184.81 | 391.73 | 155.22 | False |
| L7_R1_q0.1_mom | 185 | -392.96 | 0.93 | 435 | -2304.23 | 0.85 | -392.96 | -1323.46 | -980.78 | -2697.2 | 0.37 | 208 | -12.97 | 560.14 | 62.68 | False |
| L7_R1_q0.1_rev | 185 | 59.3 | 1.01 | 435 | 1517.63 | 1.11 | 59.3 | 956.24 | 561.39 | 1576.92 | 0.37 | 208 | 7.58 | 560.14 | -62.68 | False |
| L7_R1_q0.2_mom | 332 | 714.01 | 1.07 | 769 | -1036.9 | 0.96 | 714.01 | 93.82 | -1130.72 | -322.9 | 0.3 | 208 | -1.55 | 995.9 | -52.37 | False |
| L7_R1_q0.2_rev | 332 | -1314.31 | 0.88 | 769 | -354.6 | 0.99 | -1314.31 | -766.66 | 412.06 | -1668.91 | 0.3 | 208 | -8.02 | 995.9 | 52.37 | False |
| L7_R7_q0.1_mom | 60 | 531.29 | 1.14 | 149 | -2823.81 | 0.75 | 531.29 | -1755.51 | -1068.29 | -2292.52 | 0.85 | 30 | -76.42 | 190.75 | 130.03 | False |
| L7_R7_q0.1_rev | 60 | -640.94 | 0.85 | 149 | 2551.97 | 1.3 | -640.94 | 1622.82 | 929.15 | 1911.03 | 0.85 | 30 | 63.7 | 190.75 | -130.03 | False |
| L7_R7_q0.2_mom | 121 | 290.31 | 1.04 | 284 | -2724.81 | 0.85 | 290.31 | -600.73 | -2124.07 | -2434.5 | 0.76 | 30 | -81.15 | 369.99 | 51.46 | False |
| L7_R7_q0.2_rev | 121 | -510.25 | 0.93 | 284 | 2204.76 | 1.14 | -510.25 | 355.69 | 1849.07 | 1694.51 | 0.76 | 30 | 56.48 | 369.99 | -51.46 | False |
| L30_R1_q0.1_mom | 53 | 1017.8 | 1.58 | 231 | -178.2 | 0.98 | 1017.8 | -49.15 | -129.05 | 839.6 | 0.19 | 208 | 4.04 | 256.43 | -111.94 | True |
| L30_R1_q0.1_rev | 53 | -1114.24 | 0.6 | 231 | -238.22 | 0.97 | -1114.24 | -119.88 | -118.34 | -1352.45 | 0.19 | 208 | -6.5 | 256.43 | 111.94 | False |
| L30_R1_q0.2_mom | 112 | 797.95 | 1.19 | 372 | 2447.64 | 1.18 | 797.95 | 1143.84 | 1303.81 | 3245.6 | 0.15 | 208 | 15.6 | 439.56 | -209.65 | False |
| L30_R1_q0.2_rev | 112 | -1001.61 | 0.81 | 372 | -3123.12 | 0.81 | -1001.61 | -1435.47 | -1687.65 | -4124.73 | 0.15 | 208 | -19.83 | 439.56 | 209.65 | False |
| L30_R7_q0.1_mom | 19 | -316.23 | 0.72 | 82 | 2311.93 | 1.4 | -316.23 | 1051.45 | 1260.48 | 1995.7 | 0.48 | 30 | 66.52 | 92.95 | -99.72 | False |
| L30_R7_q0.1_rev | 19 | 280.84 | 1.34 | 82 | -2462.44 | 0.7 | 280.84 | -1115.67 | -1346.78 | -2181.6 | 0.48 | 30 | -72.72 | 92.95 | 99.72 | False |
| L30_R7_q0.2_mom | 42 | 55.78 | 1.02 | 134 | 2238.61 | 1.26 | 55.78 | 217.05 | 2021.55 | 2294.39 | 0.38 | 30 | 76.48 | 162.69 | -157.54 | False |
| L30_R7_q0.2_rev | 42 | -134.38 | 0.96 | 134 | -2485.39 | 0.78 | -134.38 | -324.94 | -2160.45 | -2619.77 | 0.38 | 30 | -87.33 | 162.69 | 157.54 | False |

## Sanity checks

- (a) Shuffle (random long/short bucket assignment, 40 trials, OOS period): mean -432.2, sd 1292.2, P(shuffle >= real) = 0.45; real = -178.2.
- (b) OOS folds: fold2 -49.15, fold3 -129.05.
- (c) Neighbors of best (one param changed): 3/4 positive OOS net.

| name | oos_n | oos_net | oos_pf | f2 | f3 |
|---|---|---|---|---|---|
| L1_R1_q0.1_mom | 990 | 798.35 | 1.03 | 1182.08 | -383.74 |
| L7_R1_q0.1_mom | 435 | -2304.23 | 0.85 | -1323.46 | -980.78 |
| L30_R1_q0.2_mom | 372 | 2447.64 | 1.18 | 1143.84 | 1303.81 |
| L30_R7_q0.1_mom | 82 | 2311.93 | 1.4 | 1051.45 | 1260.48 |

- (d) Liquidity split (illiquid = 24h vol < $5M): {False: {'size': 142, 'sum': 3152.6320028583177}, True: {'size': 89, 'sum': -3330.828977651818}}
- Side split: {-1.0: {'size': 125, 'sum': -325.6974705566974}, 1.0: {'size': 106, 'sum': 147.50049576319714}}

Per-coin OOS:

| instrument | n | net | funding | illiq |
|---|---|---|---|---|
| PURR | 13 | -852.9 | 1.3 | True |
| GRASS | 9 | -769.8 | 12.6 | True |
| XPL | 14 | -447.5 | 4.4 | False |
| JUP | 9 | -405.8 | -1.2 | False |
| HEMI | 11 | -405.4 | 8.8 | True |
| JTO | 10 | -313.8 | 6.6 | True |
| AERO | 11 | -285.2 | -7.1 | True |
| FET | 9 | -261.9 | 5.2 | True |
| ZEC | 8 | -257.4 | -2.3 | False |
| INJ | 6 | -224.7 | 5.5 | True |
| CC | 6 | -219.9 | 1.0 | True |
| ONDO | 4 | -145.5 | 1.4 | False |
| CHIP | 5 | -105.1 | -23.9 | False |
| AVAX | 4 | -71.5 | -1.5 | False |
| WLD | 10 | -43.9 | -16.3 | False |
| kPEPE | 2 | -43.8 | -1.5 | False |
| TAO | 3 | -39.4 | 0.8 | False |
| AAVE | 4 | -38.8 | -3.3 | False |
| ETHFI | 7 | -34.2 | -1.9 | True |
| NEAR | 6 | -30.2 | -5.0 | False |
| ADA | 3 | -16.5 | -9.9 | True |
| LINK | 1 | -1.2 | 0.1 | False |
| TRX | 2 | 24.3 | -0.0 | True |
| SUI | 3 | 25.4 | 0.9 | False |
| UNI | 2 | 27.3 | -4.8 | False |
| GRAM | 2 | 29.1 | 5.4 | True |
| HYPE | 3 | 35.8 | -4.0 | False |
| XMR | 2 | 65.7 | -16.9 | False |
| SPX | 5 | 85.4 | -3.8 | False |
| ENA | 5 | 120.0 | -6.5 | False |
| FARTCOIN | 2 | 123.8 | 5.2 | False |
| CRV | 4 | 125.1 | -5.4 | False |
| TRUMP | 6 | 146.2 | -34.4 | False |
| PENGU | 3 | 234.8 | -4.0 | False |
| ZRO | 8 | 274.5 | 21.2 | False |
| MON | 4 | 290.6 | 0.2 | False |
| VVV | 7 | 494.8 | -16.9 | False |
| LIT | 10 | 558.6 | -17.3 | False |
| CASHCAT | 4 | 767.0 | -33.1 | False |
| PUMP | 4 | 1407.8 | -16.0 | False |

## Criteria

`{'net_pos': False, 'pf': False, 'n': True, 'folds': False, 'shuffle': False, 'neighbors': True}`

## Verdict: **none**

## Interpretation

- Walk-forward selection on fold 1 picked 30d momentum / daily rebalance / top-bottom 10% (fold-1 net +1018, PF 1.58, n=53). It lost OOS in both folds (-49, -129; PF 0.98), so the headline is negative and the verdict is **none**.
- Selection was knife-edge: `L1_R7_q0.1_rev` had fold-1 net +1010 (vs +1018) — a $7 difference decided the pick. That is itself evidence that fold 1 does not discriminate between variants.
- The grid shows sign flips everywhere: 1d-lookback reversal wins on fold 1 but loses badly in folds 2/3 at daily rebalance; 30d momentum loses fold 1 at weekly rebalance but wins folds 2/3. No (lookback, rebalance, direction) cell is positive in all three folds except `L1_R7_q0.2_rev` (+522 / +1096 / +3926, PF 1.26, shuffle p=0.00 over 40 random-bucket trials) — which is an in-sample observation across the whole period (not WF-selected) and is long-side dominated (longs +7840 vs shorts -2296), i.e. it is mostly "buy last day's losers once a week", not a market-neutral spread. Recorded to quant-lab as post-hoc/suspect.
- The headline OOS book is driven by the illiquid names: coins with <$5M/24h volume contributed -3331 vs +3153 from liquid names. PURR/GRASS/HEMI/JTO/AERO/FET are the worst — the short leg in thin names is where the losses sit. Funding cost the momentum book -156 USD OOS (longs in high-momentum names pay funding), fees 208 USD; gross ex-funding was only +186.
- Universe is a today's-top-50-by-volume snapshot -> survivorship bias favours long-momentum results (PUMP, CASHCAT, LIT, VVV are the best long-side contributors). Any positive long-momentum cell in this grid should be discounted for that reason.
- Turnover at daily rebalance with 30d lookback is low (19% of the book per day) so fees are not the killer here; the signal simply does not carry.
