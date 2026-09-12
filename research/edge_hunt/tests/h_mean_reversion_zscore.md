# mean_reversion_zscore — results

Entry MAKER limit at signal close (fill only if next bar trades through), exit TAKER. $1000 notional/trade, one position per coin.


## 15m  (data 2026-07-06 -> 2026-08-27, folds ['2026-07-06', '2026-07-24', '2026-08-10'])

**Walk-forward best (fold 1):** `{'K': 12, 'thr': 2.0, 'H': 8, 'tgt': 0.5, 'vol_filter': 1.0}`

**OOS folds 2+3:** n=1699 net=  -869.07 pf=0.92 wr=0.52 sharpe=-0.96 bps=-5.1 folds=[0.0, -237.9, -631.1]


### In-sample grid (fold 1 metrics; fold nets over full period for transparency)

| K | thr | is_n | is_net | is_pf | is_wr | is_bps | f1 | f2 | f3 | sel |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 2.0 | 1453 | 147.8 | 1.02 | 0.60 | 1.0 | 147.8 | -1281.7 | -1565.2 |  |
| 3 | 2.5 | 789 | -27.0 | 0.99 | 0.58 | -0.3 | -27.0 | -689.3 | -1118.1 |  |
| 3 | 3.0 | 411 | -253.3 | 0.89 | 0.55 | -6.2 | -253.3 | -269.0 | 162.6 |  |
| 6 | 2.0 | 994 | -173.8 | 0.97 | 0.57 | -1.7 | -173.8 | 223.3 | -579.5 |  |
| 6 | 2.5 | 514 | -274.0 | 0.91 | 0.54 | -5.3 | -274.0 | 266.1 | 213.6 |  |
| 6 | 3.0 | 243 | 153.6 | 1.11 | 0.51 | 6.3 | 153.6 | 209.9 | 615.2 |  |
| 12 | 2.0 | 657 | 633.8 | 1.20 | 0.58 | 9.6 | 633.8 | -237.9 | -631.1 | * |
| 12 | 2.5 | 307 | 54.7 | 1.03 | 0.57 | 1.8 | 54.7 | -103.9 | -78.6 |  |
| 12 | 3.0 | 149 | -33.8 | 0.96 | 0.52 | -2.3 | -33.8 | -403.2 | 276.8 |  |

### Shuffle test (random signal timing, same fill/exit mechanics, OOS window, 30 reps)
real OOS net=-869.1; shuffled mean=-2740.4 sd=510.9 p95=-1914.4; real percentile=1.00


### Neighbouring parameters (OOS window folds 2+3, no re-selection)
| K | thr | H | tgt | volf | n | net | pf | bps | f2 | f3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 1.75 | 8 | 0.5 | 1.0 | 2654 | -299.6 | 0.98 | -1.1 | 158.0 | -457.5 |
| 9 | 2.0 | 8 | 0.5 | 1.0 | 1915 | 66.8 | 1.01 | 0.3 | 172.1 | -105.3 |
| 9 | 2.25 | 8 | 0.5 | 1.0 | 1372 | 636.9 | 1.07 | 4.6 | -57.6 | 694.5 |
| 12 | 1.75 | 8 | 0.5 | 1.0 | 2391 | -901.4 | 0.94 | -3.8 | -248.2 | -653.3 |
| 12 | 2.0 | 8 | 0.5 | 1.0 | 1699 | -869.1 | 0.92 | -5.1 | -237.9 | -631.1 |
| 12 | 2.25 | 8 | 0.5 | 1.0 | 1203 | 90.6 | 1.01 | 0.8 | -204.7 | 295.3 |
| 15 | 1.75 | 8 | 0.5 | 1.0 | 2182 | -1886.0 | 0.87 | -8.6 | -502.2 | -1383.8 |
| 15 | 2.0 | 8 | 0.5 | 1.0 | 1554 | -1055.7 | 0.90 | -6.8 | -378.9 | -676.8 |
| 15 | 2.25 | 8 | 0.5 | 1.0 | 1080 | -978.4 | 0.88 | -9.1 | -444.5 | -533.9 |
| 12 | 2.0 | 4 | 0.5 | 1.0 | 2175 | -907.3 | 0.92 | -4.2 | -650.4 | -257.0 |
| 12 | 2.0 | 16 | 0.5 | 1.0 | 1441 | -1390.3 | 0.89 | -9.6 | -331.3 | -1059.1 |
| 12 | 2.0 | 8 | None | 1.0 | 1672 | -370.6 | 0.97 | -2.2 | -19.1 | -351.6 |
| 12 | 2.0 | 8 | 1.0 | 1.0 | 1678 | -205.3 | 0.98 | -1.2 | 26.5 | -231.9 |
| 12 | 2.0 | 8 | 0.5 | 0.0 | 2101 | -1223.7 | 0.91 | -5.8 | -328.2 | -895.6 |
| 12 | 2.0 | 8 | 0.5 | 1.5 | 1494 | -678.3 | 0.93 | -4.5 | -98.7 | -579.5 |

### Per-coin OOS
liquid (24h vol >= $5M) net=-646.8 n=1191; illiquid (< $5M) net=-222.3 n=508

| coin | n | net | dayNtlVlm | illiquid |
|---|---|---|---|---|
| CASHCAT | 33 | 371.4 | 30.9M | False |
| HEMI | 39 | 329.1 | 2.0M | True |
| PUMP | 34 | 227.0 | 174.8M | False |
| CHIP | 45 | 144.7 | 6.1M | False |
| XPL | 38 | 137.2 | 11.8M | False |
| JUP | 36 | 128.7 | 5.9M | False |
| MON | 32 | 103.9 | 7.5M | False |
| ONDO | 26 | 95.0 | 6.3M | False |
| GRAM | 25 | 81.7 | 3.1M | True |
| SUI | 35 | 72.0 | 18.1M | False |
| SPX | 35 | 61.1 | 6.9M | False |
| NEAR | 42 | 59.6 | 25.9M | False |
| kPEPE | 32 | 54.4 | 16.6M | False |
| GRASS | 33 | 54.1 | 2.2M | True |
| TAO | 39 | 52.5 | 50.8M | False |
| ADA | 29 | 46.2 | 4.0M | True |
| XMR | 31 | 45.4 | 16.9M | False |
| VVV | 31 | 17.8 | 7.1M | False |
| INJ | 28 | 5.7 | 2.8M | True |
| AVAX | 42 | 4.9 | 7.6M | False |
| LTC | 26 | 1.5 | 2.1M | True |
| DOGE | 30 | -3.6 | 16.9M | False |
| AERO | 32 | -4.1 | 3.4M | True |
| SOL | 45 | -5.0 | 1243.4M | False |
| ASTER | 27 | -13.4 | 4.6M | True |
| FET | 33 | -22.6 | 2.5M | True |
| TRX | 33 | -24.6 | 3.6M | True |
| ZEC | 40 | -34.8 | 289.2M | False |
| FARTCOIN | 39 | -38.3 | 37.1M | False |
| PENGU | 33 | -39.1 | 12.0M | False |
| LINK | 28 | -44.8 | 20.8M | False |
| XRP | 44 | -47.1 | 117.8M | False |
| PAXG | 37 | -52.2 | 3.2M | True |
| CC | 37 | -56.5 | 2.4M | True |
| BNB | 28 | -58.5 | 14.7M | False |
| BTC | 39 | -73.0 | 3699.5M | False |
| UNI | 27 | -77.4 | 14.3M | False |
| JTO | 35 | -83.1 | 3.1M | True |
| ETH | 32 | -85.2 | 1679.4M | False |
| WLD | 35 | -98.3 | 9.0M | False |
| CRV | 32 | -106.8 | 9.5M | False |
| ETHFI | 35 | -120.5 | 4.1M | True |
| WIF | 30 | -164.9 | 2.3M | True |
| ENA | 42 | -172.3 | 120.2M | False |
| LIT | 32 | -182.5 | 46.9M | False |
| AAVE | 31 | -193.5 | 14.7M | False |
| PURR | 29 | -198.6 | 3.6M | True |
| HYPE | 34 | -203.8 | 969.9M | False |
| ZRO | 35 | -261.9 | 5.1M | False |
| TRUMP | 34 | -496.7 | 41.4M | False |

## 1h  (data 2026-01-31 -> 2026-08-27, folds ['2026-01-31', '2026-04-10', '2026-06-19'])

**Walk-forward best (fold 1):** `{'K': 2, 'thr': 3.0, 'H': 4, 'tgt': 0.5, 'vol_filter': 1.0}`

**OOS folds 2+3:** n=1754 net=  1214.17 pf=1.08 wr=0.57 sharpe=0.97 bps=6.9 folds=[0.0, 1525.6, -311.4]


### In-sample grid (fold 1 metrics; fold nets over full period for transparency)

| K | thr | is_n | is_net | is_pf | is_wr | is_bps | f1 | f2 | f3 | sel |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2.0 | 2410 | -9353.3 | 0.61 | 0.56 | -38.8 | -9353.3 | 848.8 | -4168.2 |  |
| 1 | 2.5 | 1458 | -6197.9 | 0.61 | 0.54 | -42.5 | -6197.9 | 514.6 | -2483.6 |  |
| 1 | 3.0 | 868 | -4379.5 | 0.58 | 0.51 | -50.5 | -4379.5 | 1064.6 | -1951.9 |  |
| 2 | 2.0 | 2102 | -6387.1 | 0.71 | 0.53 | -30.4 | -6387.1 | 1259.4 | -2160.1 |  |
| 2 | 2.5 | 1207 | -2916.8 | 0.77 | 0.53 | -24.2 | -2916.8 | 2207.7 | -1025.8 |  |
| 2 | 3.0 | 707 | -1691.3 | 0.78 | 0.55 | -23.9 | -1691.3 | 1525.6 | -311.4 | * |
| 4 | 2.0 | 1639 | -5997.8 | 0.66 | 0.50 | -36.6 | -5997.8 | 695.4 | -672.6 |  |
| 4 | 2.5 | 874 | -4369.5 | 0.60 | 0.49 | -50.0 | -4369.5 | -28.1 | -281.3 |  |
| 4 | 3.0 | 445 | -2829.5 | 0.57 | 0.47 | -63.6 | -2829.5 | 912.5 | -164.0 |  |

### Shuffle test (random signal timing, same fill/exit mechanics, OOS window, 30 reps)
real OOS net=1214.2; shuffled mean=-4681.9 sd=572.4 p95=-3860.0; real percentile=1.00


### Neighbouring parameters (OOS window folds 2+3, no re-selection)
| K | thr | H | tgt | volf | n | net | pf | bps | f2 | f3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2.75 | 4 | 0.5 | 1.0 | 2812 | -1136.5 | 0.95 | -4.0 | 1061.7 | -2198.2 |
| 1 | 3.0 | 4 | 0.5 | 1.0 | 2211 | -887.2 | 0.95 | -4.0 | 1064.6 | -1951.9 |
| 1 | 3.25 | 4 | 0.5 | 1.0 | 1747 | -200.4 | 0.99 | -1.1 | 1575.2 | -1775.5 |
| 2 | 2.75 | 4 | 0.5 | 1.0 | 2286 | 1245.4 | 1.06 | 5.4 | 2211.4 | -966.0 |
| 2 | 3.0 | 4 | 0.5 | 1.0 | 1754 | 1214.2 | 1.08 | 6.9 | 1525.6 | -311.4 |
| 2 | 3.25 | 4 | 0.5 | 1.0 | 1286 | 714.1 | 1.06 | 5.6 | 1247.9 | -533.8 |
| 3 | 2.75 | 4 | 0.5 | 1.0 | 1811 | 122.5 | 1.01 | 0.7 | 1045.0 | -922.5 |
| 3 | 3.0 | 4 | 0.5 | 1.0 | 1329 | 408.7 | 1.03 | 3.1 | 553.1 | -144.5 |
| 3 | 3.25 | 4 | 0.5 | 1.0 | 993 | 1037.6 | 1.10 | 10.4 | 657.5 | 380.0 |
| 2 | 3.0 | 2 | 0.5 | 1.0 | 1811 | 608.8 | 1.05 | 3.4 | 983.0 | -374.2 |
| 2 | 3.0 | 8 | 0.5 | 1.0 | 1650 | -1299.8 | 0.94 | -7.9 | -134.1 | -1165.7 |
| 2 | 3.0 | 4 | None | 1.0 | 1685 | 803.2 | 1.05 | 4.8 | 293.6 | 509.6 |
| 2 | 3.0 | 4 | 1.0 | 1.0 | 1732 | 1559.8 | 1.09 | 9.0 | 1158.7 | 401.1 |
| 2 | 3.0 | 4 | 0.5 | 0.0 | 1842 | 903.3 | 1.05 | 4.9 | 1236.8 | -333.4 |
| 2 | 3.0 | 4 | 0.5 | 1.5 | 1646 | 1702.2 | 1.11 | 10.3 | 1676.6 | 25.6 |

### Per-coin OOS
liquid (24h vol >= $5M) net=1109.8 n=1223; illiquid (< $5M) net=104.4 n=531

| coin | n | net | dayNtlVlm | illiquid |
|---|---|---|---|---|
| PURR | 33 | 347.0 | 3.6M | True |
| ZEC | 39 | 344.7 | 289.2M | False |
| XMR | 30 | 225.8 | 16.9M | False |
| SOL | 45 | 201.2 | 1243.4M | False |
| LIT | 28 | 185.1 | 46.9M | False |
| kPEPE | 43 | 181.3 | 16.6M | False |
| CHIP | 29 | 154.7 | 6.1M | False |
| FARTCOIN | 39 | 147.9 | 37.1M | False |
| AVAX | 41 | 142.8 | 7.6M | False |
| LTC | 36 | 140.0 | 2.1M | True |
| CC | 39 | 139.5 | 2.4M | True |
| TAO | 34 | 122.0 | 50.8M | False |
| JUP | 33 | 112.0 | 5.9M | False |
| ASTER | 37 | 100.1 | 4.6M | True |
| PUMP | 35 | 98.2 | 174.8M | False |
| XRP | 47 | 95.8 | 117.8M | False |
| CASHCAT | 12 | 89.2 | 30.9M | False |
| VVV | 36 | 78.0 | 7.1M | False |
| WLD | 33 | 75.3 | 9.0M | False |
| WIF | 39 | 69.5 | 2.3M | True |
| GRAM | 18 | 63.4 | 3.1M | True |
| ONDO | 28 | 62.9 | 6.3M | False |
| LINK | 41 | 57.9 | 20.8M | False |
| HEMI | 39 | 50.5 | 2.0M | True |
| SUI | 34 | 28.5 | 18.1M | False |
| FET | 22 | 28.2 | 2.5M | True |
| PENGU | 29 | 27.5 | 12.0M | False |
| SPX | 36 | 18.1 | 6.9M | False |
| ADA | 39 | 15.8 | 4.0M | True |
| CRV | 44 | 13.2 | 9.5M | False |
| DOGE | 38 | 12.9 | 16.9M | False |
| INJ | 26 | 7.3 | 2.8M | True |
| BTC | 47 | -9.9 | 3699.5M | False |
| XPL | 37 | -12.5 | 11.8M | False |
| TRX | 28 | -14.5 | 3.6M | True |
| BNB | 39 | -20.9 | 14.7M | False |
| AERO | 31 | -24.9 | 3.4M | True |
| MON | 33 | -38.3 | 7.5M | False |
| ENA | 36 | -44.1 | 120.2M | False |
| ETH | 49 | -71.7 | 1679.4M | False |
| PAXG | 44 | -75.9 | 3.2M | True |
| UNI | 41 | -77.1 | 14.3M | False |
| GRASS | 35 | -79.5 | 2.2M | True |
| AAVE | 38 | -83.9 | 14.7M | False |
| NEAR | 30 | -95.4 | 25.9M | False |
| HYPE | 23 | -181.8 | 969.9M | False |
| ETHFI | 39 | -195.7 | 4.1M | True |
| ZRO | 34 | -329.8 | 5.1M | False |
| TRUMP | 42 | -399.9 | 41.4M | False |
| JTO | 26 | -466.4 | 3.1M | True |

## Interpretation

**Verdict: weak (1h) / none (15m).** Headline = 1h walk-forward OOS (folds 2+3): n=1754, net +$1,214 on $1,000 notional/trade (+6.9 bps/trade), PF 1.08, WR 0.57, folds [+1,526, -311]. 15m OOS: n=1699, net -$869, PF 0.92, both OOS folds negative.

What the data says:
- The z-score does contain information. The shuffle baseline (random signal timing, identical maker-fill-through + exit mechanics) loses heavily (1h: -$4,682 +/- 572; 15m: -$2,740 +/- 511) because a resting limit that only fills when price trades through it is adversely selected. The real signal sits far above that baseline (percentile 1.00 in both timeframes), so contrarian entries after |z|>thr moves genuinely recover most of the adverse selection. But "recovering adverse selection" is not the same as a tradeable edge: after fees the residual is ~5-10 bps/trade on 1h and negative on 15m.
- Fees dominate: maker-in/taker-out = 6 bps round trip, and gross edge per trade on 1h is ~13 bps. Thin.
- Regime dependence: 1h fold 1 (Feb-Apr 2026) was negative for EVERY grid cell (best -$1,691); fold 2 (Apr-Jun) positive for nearly all; fold 3 mixed. The fold-1 selection picked the least-bad cell, not a good one, so the "OOS" gain is partly luck of regime change.
- Neighbour robustness (1h): 11/15 neighbours positive in the OOS window, but effect sizes are all PF 1.01-1.11. H=8 flips negative (-$1,300); K=1 flips negative. Only K=2-3 with thr>=2.75 and H<=4 hold up. Larger target (tgt=1.0) and pure time-stop (tgt=None) both keep both OOS folds positive (+$1,560 and +$803), which is mildly encouraging: the result is not an artefact of the half-retrace target.
- Liquidity: 1h OOS profit is NOT concentrated in illiquid names (liquid >= $5M: +$1,110 on 1223 trades; illiquid: +$104 on 531). Per-coin dispersion is large (PURR +347 ... JTO -466) with 20/50 coins negative; single-coin contributions are noise-sized.
- 15m: every grid cell is within +/-10 bps of zero in-sample, and OOS is negative; the fold-1 winner (K=12, thr=2.0) was an overfit cell (its fold 2/3 nets were -238/-631).

Fails 'edge' on: PF < 1.2, fold 3 negative on 1h, 15m negative outright. Passes shuffle only against an adverse-selection baseline, which is the wrong bar for a live edge.

## Next tests
1. Keep 1h, K=2-3, thr>=3, H<=4 but condition on funding/premium: contrarian shorts only when funding is positive/premium > 0 (crowded longs) and longs only when funding negative. The z-score alone is too weak; a positioning conditioner may sharpen it.
2. Make the entry price better than the signal close: place the limit a fraction of sigma beyond the close (e.g. close +/- 0.5*sigma_1bar) so the fill captures more of the overshoot; test whether the fill-rate drop is compensated.
3. Restrict to the top-15 by 24h volume and exit MAKER (limit at target, no time-stop taker exit) to cut the 4.5 bps taker leg; measure fill rate honestly (touch-through rule).
4. Drop 15m entirely; the bar-level noise at 15m does not clear fees.
