# h_xsec_mom30_rev1_hedged - long-only z(30d) - z(1d) book, point-in-time HL universe

Data: 194 HL perps with 1h data in 2026-01-31 -> 2026-08-27 (176 listed + delisted perps; 1d candles for the lookbacks, 1h 00:00 bar for fills). Folds: [('2026-01-31', '2026-04-10'), ('2026-04-10', '2026-06-19'), ('2026-06-19', '2026-08-27')].

Universe (point-in-time, at each 23:00 signal): trailing-24h USD vol >= $5M, top-50 by trailing-30d USD vol, >= 31 daily closes. Size/day: min 8, mean 24.1, max 50; 116 coins ever eligible (50 of them in the round-1 snapshot-50). Fraction of the PIT universe that is in the snapshot-50 by fold: [0.91, 0.89, 0.92].

Execution: score = z(30d ret) - z(1d ret) at the 23:00 close; long top-q, $1000/name, fill at the 00:00 bar (taker at open, or maker limit at open filled only if the bar trades through, else taker at that bar's close); keep names that stay in the bucket; optional equal-notional BTC short hedge resized at each rebalance (fee on the adjustment only). Hourly funding folded into exit_px.

## Headline (walk-forward OOS, folds 2+3)

Selected on fold 1: `{'rebal_d': 7, 'quantile': 0.2, 'hedge': 1, 'exec': 'taker', 'signal': 'combo'}`

| n | net USD | PF | WR | Sharpe | maxDD | net bps | fold2 | fold3 |
|---|---|---|---|---|---|---|---|---|
| 73 | 3737.66 | 1.74 | 0.48 | 1.39 | 1008.6 | 278.9 | 602.97 | 3134.69 |

Hedged arm of the selected structure (combo_R7_q0.2_h1_taker) OOS: n=73 net=3737.66 pf=1.74 fold2=602.97 fold3=3134.69. BTC return by fold: [-0.089, -0.137, 0.244].

## In-sample grid (fold 1) with fold 2/3 nets (combo signal)

| name | is_n | is_net | is_pf | oos_n | oos_net | oos_pf | f1 | f2 | f3 | full_net | long_net | hedge_net | fees | funding | turnover | n_rebal | avg_univ | avg_long | maker_fill | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| combo_R1_q0.1_h0_taker | 87 | -113.65 | 0.95 | 174 | 1478.17 | 1.26 | -113.65 | -617.75 | 2095.92 | 1364.52 | 1364.52 | 0.0 | 235.52 | 214.43 | 0.64 | 208 | 24.1 | 1.96 | 0.0 | False |
| combo_R1_q0.1_h0_maker_fb | 87 | -95.97 | 0.96 | 174 | 1421.62 | 1.25 | -95.97 | -623.4 | 2045.01 | 1325.65 | 1325.65 | 0.0 | 82.28 | 214.43 | 0.64 | 208 | 24.1 | 1.96 | 0.98 | False |
| combo_R1_q0.1_h1_taker | 155 | -37.13 | 0.99 | 312 | 1436.78 | 1.18 | -37.13 | -138.65 | 1575.42 | 1399.65 | 1364.52 | 35.13 | 274.67 | 260.45 | 0.64 | 208 | 24.1 | 1.96 | 0.27 | False |
| combo_R1_q0.1_h1_maker_fb | 155 | -9.85 | 1.0 | 312 | 1390.88 | 1.18 | -9.85 | -140.78 | 1531.66 | 1381.04 | 1325.65 | 55.39 | 96.23 | 260.45 | 0.64 | 208 | 24.1 | 1.96 | 0.99 | False |
| combo_R1_q0.2_h0_taker | 168 | -205.01 | 0.95 | 298 | 945.12 | 1.1 | -205.01 | -2007.91 | 2953.03 | 740.12 | 740.12 | 0.0 | 419.79 | 283.52 | 0.51 | 208 | 24.1 | 4.41 | 0.0 | False |
| combo_R1_q0.2_h0_maker_fb | 168 | -174.84 | 0.96 | 298 | 880.13 | 1.09 | -174.84 | -1990.29 | 2870.42 | 705.29 | 705.29 | 0.0 | 146.68 | 283.52 | 0.51 | 208 | 24.1 | 4.41 | 0.98 | False |
| combo_R1_q0.2_h1_taker | 236 | -156.76 | 0.98 | 436 | 860.67 | 1.06 | -156.76 | -948.02 | 1808.69 | 703.91 | 740.12 | -36.21 | 500.34 | 387.09 | 0.51 | 208 | 24.1 | 4.41 | 0.11 | False |
| combo_R1_q0.2_h1_maker_fb | 236 | -103.5 | 0.99 | 436 | 815.57 | 1.06 | -103.5 | -923.37 | 1738.95 | 712.07 | 705.29 | 6.79 | 175.03 | 387.09 | 0.51 | 208 | 24.1 | 4.41 | 0.98 | False |
| combo_R7_q0.1_h0_taker | 10 | 393.07 | 1.6 | 31 | 1426.93 | 1.63 | 393.07 | -754.35 | 2181.28 | 1820.0 | 1820.0 | 0.0 | 37.47 | 584.77 | 0.79 | 30 | 21.13 | 1.7 | 0.0 | False |
| combo_R7_q0.1_h0_maker_fb | 10 | 373.69 | 1.56 | 31 | 1432.31 | 1.63 | 373.69 | -753.13 | 2185.44 | 1806.0 | 1806.0 | 0.0 | 13.68 | 584.77 | 0.79 | 30 | 21.13 | 1.7 | 1.0 | False |
| combo_R7_q0.1_h1_taker | 19 | 665.66 | 1.78 | 51 | 1495.29 | 1.5 | 665.66 | -426.81 | 1922.1 | 2160.95 | 1820.0 | 340.95 | 50.97 | 622.59 | 0.79 | 30 | 21.13 | 1.7 | 0.19 | False |
| combo_R7_q0.1_h1_maker_fb | 19 | 649.58 | 1.76 | 51 | 1503.88 | 1.5 | 649.58 | -423.49 | 1927.37 | 2153.46 | 1806.0 | 347.46 | 18.48 | 622.59 | 0.79 | 30 | 21.13 | 1.7 | 0.99 | False |
| combo_R7_q0.2_h0_taker | 23 | 222.43 | 1.19 | 53 | 3999.35 | 2.28 | 222.43 | 67.24 | 3932.11 | 4221.78 | 4221.78 | 0.0 | 70.12 | 477.38 | 0.65 | 30 | 21.13 | 3.87 | 0.0 | False |
| combo_R7_q0.2_h0_maker_fb | 23 | 199.39 | 1.17 | 53 | 3985.03 | 2.26 | 199.39 | 71.37 | 3913.66 | 4184.42 | 4184.42 | 0.0 | 25.81 | 477.38 | 0.65 | 30 | 21.13 | 3.87 | 1.0 | False |
| combo_R7_q0.2_h1_taker | 32 | 841.91 | 1.52 | 73 | 3737.66 | 1.74 | 841.91 | 602.97 | 3134.69 | 4579.58 | 4221.78 | 357.8 | 98.92 | 565.4 | 0.65 | 30 | 21.13 | 3.87 | 0.04 | True |
| combo_R7_q0.2_h1_maker_fb | 32 | 826.37 | 1.51 | 73 | 3732.73 | 1.74 | 826.37 | 612.21 | 3120.52 | 4559.1 | 4184.42 | 374.68 | 35.71 | 565.4 | 0.65 | 30 | 21.13 | 3.87 | 0.99 | False |

## Momentum-only / reversal-only arms (selected exec mode), full-period folds

| name | is_n | is_net | is_pf | oos_n | oos_net | oos_pf | f1 | f2 | f3 | full_net | long_net | hedge_net | fees | funding | turnover | n_rebal | avg_univ | avg_long | maker_fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mom_R1_q0.1_h0_taker | 52 | 686.95 | 1.38 | 95 | -642.93 | 0.88 | 686.95 | -2040.83 | 1397.91 | 44.02 | 44.02 | 0.0 | 132.26 | 267.63 | 0.36 | 208 | 24.1 | 1.96 | 0.0 |
| mom_R1_q0.1_h1_taker | 120 | 763.47 | 1.23 | 233 | -684.32 | 0.91 | 763.47 | -1561.73 | 877.41 | 79.15 | 44.02 | 35.13 | 171.41 | 313.65 | 0.36 | 208 | 24.1 | 1.96 | 0.36 |
| mom_R1_q0.2_h0_taker | 94 | -118.24 | 0.97 | 172 | 1167.92 | 1.15 | -118.24 | -1692.06 | 2859.98 | 1049.68 | 1049.68 | 0.0 | 239.8 | 411.57 | 0.29 | 208 | 24.1 | 4.41 | 0.0 |
| mom_R1_q0.2_h1_taker | 162 | -69.99 | 0.99 | 310 | 1083.46 | 1.09 | -69.99 | -632.17 | 1715.64 | 1013.47 | 1049.68 | -36.21 | 320.35 | 515.15 | 0.29 | 208 | 24.1 | 4.41 | 0.16 |
| mom_R7_q0.1_h0_taker | 10 | -162.21 | 0.8 | 24 | -164.53 | 0.93 | -162.21 | -913.57 | 749.04 | -326.74 | -326.74 | 0.0 | 30.33 | 294.43 | 0.65 | 30 | 21.13 | 1.7 | 0.0 |
| mom_R7_q0.1_h1_taker | 19 | 110.38 | 1.11 | 44 | -96.17 | 0.97 | 110.38 | -586.04 | 489.87 | 14.21 | -326.74 | 340.95 | 43.83 | 332.25 | 0.65 | 30 | 21.13 | 1.7 | 0.21 |
| mom_R7_q0.2_h0_taker | 21 | -803.05 | 0.54 | 49 | 1565.7 | 1.41 | -803.05 | -1549.68 | 3115.37 | 762.65 | 762.65 | 0.0 | 63.26 | 244.03 | 0.6 | 30 | 21.13 | 3.87 | 0.0 |
| mom_R7_q0.2_h1_taker | 30 | -183.56 | 0.92 | 69 | 1304.01 | 1.23 | -183.56 | -1013.94 | 2317.95 | 1120.45 | 762.65 | 357.8 | 92.06 | 332.05 | 0.6 | 30 | 21.13 | 3.87 | 0.04 |
| rev_R1_q0.1_h0_taker | 117 | 48.31 | 1.02 | 232 | -460.7 | 0.93 | 48.31 | -830.23 | 369.53 | -412.39 | -412.39 | 0.0 | 313.9 | 356.28 | 0.86 | 208 | 24.1 | 1.96 | 0.0 |
| rev_R1_q0.1_h1_taker | 185 | 124.83 | 1.03 | 370 | -502.09 | 0.94 | 124.83 | -351.13 | -150.96 | -377.26 | -412.39 | 35.13 | 353.05 | 402.3 | 0.86 | 208 | 24.1 | 1.96 | 0.23 |
| rev_R1_q0.2_h0_taker | 242 | 10.8 | 1.0 | 484 | 353.62 | 1.03 | 10.8 | -996.7 | 1350.32 | 364.42 | 364.42 | 0.0 | 653.7 | 344.71 | 0.8 | 208 | 24.1 | 4.41 | 0.0 |
| rev_R1_q0.2_h1_taker | 310 | 59.05 | 1.01 | 622 | 269.16 | 1.02 | 59.05 | 63.18 | 205.98 | 328.21 | 364.42 | -36.21 | 734.25 | 448.29 | 0.8 | 208 | 24.1 | 4.41 | 0.08 |
| rev_R7_q0.1_h0_taker | 13 | -209.85 | 0.74 | 36 | 855.49 | 1.38 | -209.85 | -735.58 | 1591.07 | 645.64 | 645.64 | 0.0 | 44.17 | 541.66 | 0.94 | 30 | 21.13 | 1.7 | 0.0 |
| rev_R7_q0.1_h1_taker | 22 | 62.74 | 1.06 | 56 | 923.85 | 1.31 | 62.74 | -408.04 | 1331.89 | 986.59 | 645.64 | 340.95 | 57.67 | 579.48 | 0.94 | 30 | 21.13 | 1.7 | 0.17 |
| rev_R7_q0.2_h0_taker | 32 | -517.02 | 0.69 | 78 | 1344.01 | 1.32 | -517.02 | -1098.77 | 2442.78 | 826.99 | 826.99 | 0.0 | 99.19 | 495.54 | 0.94 | 30 | 21.13 | 3.87 | 0.0 |
| rev_R7_q0.2_h1_taker | 41 | 102.47 | 1.05 | 98 | 1082.33 | 1.18 | 102.47 | -563.04 | 1645.36 | 1184.79 | 826.99 | 357.8 | 127.99 | 583.56 | 0.94 | 30 | 21.13 | 3.87 | 0.03 |

## Sanity checks

- (a) Shuffle (random long bucket, 40 reps, OOS): mean -162.8, sd 1097.5, P(shuffle >= real) = 0.00; real = 3737.7.
- (b) OOS folds: fold2 602.97, fold3 3134.69.
- (c) Neighbours of best (one param changed): 4/4 positive OOS net.

| name | oos_n | oos_net | oos_pf | f2 | f3 |
|---|---|---|---|---|---|
| combo_R1_q0.2_h1_taker | 436 | 860.67 | 1.06 | -948.02 | 1808.69 |
| combo_R7_q0.1_h1_taker | 51 | 1495.29 | 1.5 | -426.81 | 1922.1 |
| combo_R7_q0.2_h0_taker | 53 | 3999.35 | 2.28 | 67.24 | 3932.11 |
| combo_R7_q0.2_h1_maker_fb | 73 | 3732.73 | 1.74 | 612.21 | 3120.52 |

- Survivorship: same params on the hindsight snapshot-50 universe, OOS: n=64 net=2377.01 pf=1.54 folds=[0.0, 560.4, 1816.7]; full-period folds hindsight [462.7, 560.4, 1816.7] vs PIT [841.9, 603.0, 3134.7].

- (d) Long-leg liquidity split (thin = 24h vol < $10M at entry; all names >= $5M by construction): {False: {'size': 32, 'sum': 542.35107049025}, True: {'size': 21, 'sum': 3456.9990792645476}}
- Leg split: {'hedge': {'size': 20, 'sum': -261.6871965499256}, 'long': {'size': 53, 'sum': 3999.3501497547973}}
- Maker-entry split: {False: {'size': 69, 'sum': 4017.252050441433}, True: {'size': 4, 'sum': -279.58909723656075}}
- OOS funding 312.4, fees 67.0, delisting exits 0

Per-coin OOS:

| instrument | n | net | funding | vol24 |
|---|---|---|---|---|
| BIO | 1 | -305.0 | 1.4 | 6141700.0 |
| PENDLE | 1 | -291.4 | 0.2 | 5086994.7 |
| BTC | 20 | -261.7 | 80.8 | nan |
| TON | 1 | -252.5 | 1.2 | 84525185.8 |
| XPL | 4 | -241.7 | -8.6 | 13794173.4 |
| STRK | 1 | -206.0 | -1.5 | 9303746.7 |
| ONDO | 2 | -94.3 | -4.3 | 16209666.9 |
| SPX | 1 | -92.2 | -1.5 | 5323859.6 |
| CRV | 2 | -88.2 | -3.6 | 22716002.5 |
| MEGA | 1 | -83.2 | 6.5 | 12826167.4 |
| ORDI | 1 | -76.2 | -2.1 | 5207753.1 |
| XLM | 1 | -75.3 | 2.3 | 41014735.7 |
| ENA | 1 | -73.0 | -1.4 | 5161191.8 |
| EIGEN | 1 | -57.6 | -1.5 | 19744180.2 |
| KAITO | 2 | -39.6 | 248.8 | 17973202.4 |
| BCH | 1 | -32.9 | -1.2 | 9090729.7 |
| INJ | 1 | -32.4 | 0.8 | 6637416.8 |
| NEAR | 1 | -31.9 | -5.9 | 69805691.6 |
| UNI | 1 | -21.6 | -1.2 | 6014737.7 |
| kPEPE | 2 | -20.6 | -2.5 | 30715733.4 |
| LINK | 1 | -6.6 | -2.0 | 36864354.3 |
| AAVE | 1 | 4.7 | -0.6 | 16435289.4 |
| WLD | 1 | 23.6 | -4.2 | 103895983.2 |
| VIRTUAL | 1 | 41.8 | 1.1 | 9379906.3 |
| JTO | 2 | 48.1 | -1.1 | 8109262.4 |
| ZEC | 3 | 67.5 | -15.7 | 66258586.7 |
| ARB | 1 | 117.7 | 0.8 | 7745116.9 |
| PENGU | 1 | 138.4 | -3.4 | 10725021.8 |
| APE | 1 | 149.7 | 9.3 | 16344708.5 |
| VVV | 1 | 255.4 | -11.4 | 9404105.5 |
| FARTCOIN | 3 | 263.8 | -10.3 | 15345382.6 |
| PURR | 1 | 360.3 | -8.7 | 5705941.2 |
| LIT | 3 | 394.5 | -13.5 | 23592242.7 |
| ACE | 1 | 682.5 | 118.9 | 8255230.3 |
| HYPE | 4 | 812.1 | -8.1 | 314160871.8 |
| CASHCAT | 1 | 1034.7 | -31.2 | 7609127.5 |
| PUMP | 1 | 1726.5 | -14.5 | 8925868.8 |

- (e) Weekly-anchor phase robustness (rebalance day shifted by 0..R-1 days), OOS:

| phase | oos_n | oos_net | oos_pf | f2 | f3 |
|---|---|---|---|---|---|
| 0.0 | 73.0 | 3737.66 | 1.74 | 602.97 | 3134.69 |
| 1.0 | 68.0 | 117.24 | 1.02 | -1017.12 | 1134.37 |
| 2.0 | 80.0 | 1431.88 | 1.26 | 741.5 | 690.37 |
| 3.0 | 73.0 | 1350.67 | 1.27 | 654.71 | 695.96 |
| 4.0 | 70.0 | 2178.95 | 1.44 | 1257.68 | 921.27 |
| 5.0 | 71.0 | 1551.01 | 1.32 | 552.21 | 998.8 |
| 6.0 | 75.0 | 2289.03 | 1.39 | -382.56 | 2671.59 |

- Concentration: long trades n=53, net 3999.4, ex-top-1 2272.8, ex-top-3 555.6, median long trade -6.6; per-rebalance book PnL n=20, mean 186.9, sd 600.6, t=1.39, positive 13/20.

## Criteria

`{'net_pos': True, 'pf': True, 'n': False, 'folds': True, 'shuffle': True, 'neighbors': True, 'hedged_both_folds': True, 'phase': True, 'not_tail_driven': False}` (n = long-leg trades only; hedge rows excluded)

## Verdict: **weak**

## Interpretation

- Walk-forward pick on fold 1: weekly rebalance, top-20% of the ~21-name liquid PIT universe (~4 longs), BTC-hedged, taker fills. OOS (folds 2+3) net +3738 on 73 rows (53 long trades + 20 hedge intervals), PF 1.74, both OOS folds positive (+603 / +3135). Shuffle p=0.00 (random-bucket mean -163, sd 1098), all 4 one-param neighbours positive OOS, and the point-in-time universe is *better* than the hindsight snapshot-50 (+3738 vs +2377), so the two round-1 refutations (beta, survivorship) do not explain this result.
- BUT the result is a lottery-ticket distribution, not a steady edge: the median long trade is -6.6 USD and WR 48%; three trades (PUMP +1727 held 07-26 -> 08-27 as it 2.7x'd, CASHCAT +1035, ACE +683 of which +119 is negative-funding income) make 3444 of the 3999 long-leg net. Ex-top-3 the remaining 50 long trades net +556. Per-rebalance book PnL: 20 OOS decisions, mean +187, sd 601, t = 1.39, 13/20 positive. That is not significant at 20 independent weekly bets.
- Fold 3 (BTC +24%, alt bull) carries 84% of OOS net; the BTC hedge cost only -262 net (funding +81), i.e. the hedge does not remove alt-beta, and the long book's winners were $5-10M/day names (thin bucket: +3457 on 21 trades vs +542 on 32 liquid trades).
- Weekly-anchor phase test: all 7 phases positive OOS (range +117 .. +3738, median ~+1550, PF 1.02-1.74), but the selected phase 0 is the best of the seven; mean-over-phases (~+1800, PF ~1.3) is the fairer expectation. Fold 2 is negative for phases 1 and 6.
- Momentum-only and reversal-only arms at the same structure lose fold 2 (-1014 / -563) and only the combination is positive in both OOS folds; combined > each arm in both folds, which supports the hypothesis qualitatively, but with 4-name books it is hard to distinguish from noise.
- Execution: maker_fb fills at 98-100% (the 00:00 hourly bar almost always trades through its open), so the maker arm is nearly a fee discount on the taker arm; headline uses taker fees anyway. Fees are small (99 USD full period) - fees are not what limits this idea.
- Verdict **weak**: positive OOS after fees with PF 1.74 and both folds positive, but fails n (53 signal trades < 60) and is tail-driven (t=1.39 per rebalance, ex-top-3 barely positive). Needs a larger, more diversified book before it can be trusted.
