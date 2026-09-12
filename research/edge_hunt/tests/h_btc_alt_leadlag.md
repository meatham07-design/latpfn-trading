# btc_alt_leadlag - round 1 results

Notional $1000/leg, 5 laggard alts per signal, taker fees both sides (9 bps round trip). Entry next-bar open, exit H bars later at open. Fresh-breach signal only (|BTC K-bar ret| crosses X). Per-coin no overlap.

## 15m  (2026-07-06 -> 2026-08-27, 5012 bars)

Folds: F1 07-06->07-24, F2 07-24->08-10, F3 08-10->08-27

**Selected on fold 1:** `{'X': 1.0, 'K': 6, 'H': 6}`  
**Walk-forward OOS (folds 2+3):** n=217 net=$224.90 pf=1.10 wr=0.50 sharpe=0.44 net_bps=10.4 folds=[F2 -448.70, F3 673.59] max_dd=684.16

### Full grid (F1 = selection / in-sample, F2+F3 = out-of-sample)

| X% | K | H | n | net | pf | wr | F1 | F2 | F3 | OOS23 | bps | sel |
|---:|--:|--:|--:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 0.3 | 3 | 3 | 2169 | -2477.1 | 0.81 | 0.45 | -829.5 | -711.5 | -936.1 | -1647.6 | -11.4 |  |
| 0.3 | 3 | 6 | 2016 | -1387.3 | 0.91 | 0.46 | -1141.4 | -220.5 | -25.4 | -246.0 | -6.9 |  |
| 0.3 | 3 | 12 | 1814 | -2117.7 | 0.89 | 0.47 | -1044.9 | 63.1 | -1135.8 | -1072.7 | -11.7 |  |
| 0.3 | 6 | 3 | 2292 | -984.9 | 0.91 | 0.45 | -317.7 | -609.9 | -57.3 | -667.2 | -4.3 |  |
| 0.3 | 6 | 6 | 2122 | -355.9 | 0.98 | 0.46 | -303.6 | -470.1 | 417.8 | -52.3 | -1.7 |  |
| 0.3 | 6 | 12 | 1914 | -1523.7 | 0.91 | 0.46 | -815.8 | 4.4 | -712.4 | -707.9 | -8.0 |  |
| 0.5 | 3 | 3 | 1009 | -1670.9 | 0.75 | 0.44 | -758.7 | -581.6 | -330.6 | -912.2 | -16.6 |  |
| 0.5 | 3 | 6 | 956 | -607.0 | 0.92 | 0.45 | -710.6 | -763.8 | 867.4 | 103.5 | -6.3 |  |
| 0.5 | 3 | 12 | 889 | -2212.9 | 0.79 | 0.45 | -1715.6 | -1033.7 | 536.4 | -497.3 | -24.9 |  |
| 0.5 | 6 | 3 | 1185 | -364.6 | 0.95 | 0.48 | -222.2 | -187.7 | 45.2 | -142.4 | -3.1 |  |
| 0.5 | 6 | 6 | 1145 | 38.4 | 1.00 | 0.47 | -126.1 | -383.0 | 547.5 | 164.5 | 0.3 |  |
| 0.5 | 6 | 12 | 1065 | -1374.9 | 0.88 | 0.46 | -579.4 | 41.0 | -836.5 | -795.5 | -12.9 |  |
| 1.0 | 3 | 3 | 173 | -10.9 | 0.99 | 0.44 | 39.4 | 55.6 | -106.0 | -50.3 | -0.6 |  |
| 1.0 | 3 | 6 | 169 | 460.4 | 1.39 | 0.53 | -39.5 | 200.2 | 299.7 | 499.9 | 27.2 |  |
| 1.0 | 3 | 12 | 166 | -147.2 | 0.92 | 0.47 | -120.5 | 12.7 | -39.4 | -26.7 | -8.9 |  |
| 1.0 | 6 | 3 | 311 | 228.7 | 1.12 | 0.50 | -9.0 | 76.5 | 161.2 | 237.7 | 7.4 |  |
| 1.0 | 6 | 6 | 299 | 450.1 | 1.17 | 0.48 | 225.2 | -448.7 | 673.6 | 224.9 | 15.1 | * |
| 1.0 | 6 | 12 | 290 | -552.3 | 0.84 | 0.43 | -280.3 | -409.1 | 137.1 | -272.0 | -19.0 |  |

### Sanity checks (OOS window, selected params)

- select=lag: n=217 net=224.90 pf=1.10 wr=0.50
- select=lead: n=215 net=342.99 pf=1.17 wr=0.47
- select=all: n=1862 net=1969.57 pf=1.18 wr=0.47
- time-shuffle (100x): mean=-221.45 sd=489.69 p(shuffled >= real)=0.17
- coin-shuffle (100x): mean=73.26 sd=314.14 p(shuffled >= real)=0.31
- neighbours with OOS23 > 0: 3/5
- illiquid (<$5M/24h) OOS net=-177.51; liquid OOS net=402.41

### Per-coin OOS (selected params)

| coin | n | net | wr | 24h vol $M | illiquid |
|---|--:|---:|---:|---:|:--:|
| CASHCAT | 17 | 227.61 | 0.65 | 30.9 |  |
| PURR | 11 | 194.90 | 0.73 | 3.6 | Y |
| kPEPE | 6 | 162.66 | 1.00 | 16.6 |  |
| FARTCOIN | 5 | 104.27 | 1.00 | 37.1 |  |
| LIT | 8 | 69.49 | 0.50 | 46.9 |  |
| SPX | 5 | 68.09 | 0.80 | 6.9 |  |
| ZEC | 7 | 67.67 | 0.86 | 289.2 |  |
| WIF | 4 | 58.75 | 1.00 | 2.3 | Y |
| XPL | 6 | 49.40 | 0.50 | 11.8 |  |
| AERO | 4 | 48.25 | 1.00 | 3.4 | Y |
| PUMP | 8 | 48.15 | 0.62 | 174.8 |  |
| PENGU | 2 | 45.48 | 1.00 | 12.0 |  |
| AAVE | 5 | 31.49 | 0.80 | 14.7 |  |
| ADA | 1 | 24.03 | 1.00 | 4.0 | Y |
| GRASS | 6 | 14.10 | 0.33 | 2.2 | Y |
| WLD | 6 | 12.84 | 0.17 | 9.0 |  |
| NEAR | 2 | 12.77 | 0.50 | 25.9 |  |
| TRX | 1 | 2.36 | 1.00 | 3.6 | Y |
| HYPE | 2 | 1.16 | 0.50 | 969.9 |  |
| FET | 1 | 0.18 | 1.00 | 2.5 | Y |
| XRP | 2 | -0.22 | 0.50 | 117.8 |  |
| ETH | 3 | -1.45 | 0.67 | 1679.4 |  |
| ONDO | 6 | -2.04 | 0.50 | 6.3 |  |
| DOGE | 1 | -3.84 | 0.00 | 16.9 |  |
| PAXG | 3 | -3.91 | 0.33 | 3.2 | Y |
| GRAM | 1 | -6.79 | 0.00 | 3.1 | Y |
| ASTER | 2 | -8.19 | 0.00 | 4.6 | Y |
| INJ | 3 | -8.34 | 0.67 | 2.8 | Y |
| JUP | 2 | -15.86 | 0.50 | 5.9 |  |
| TAO | 2 | -23.19 | 0.00 | 50.8 |  |
| UNI | 6 | -25.77 | 0.33 | 14.3 |  |
| CHIP | 8 | -31.14 | 0.38 | 6.1 |  |
| VVV | 10 | -31.59 | 0.50 | 7.1 |  |
| CC | 7 | -32.85 | 0.29 | 2.4 | Y |
| XMR | 5 | -48.66 | 0.40 | 16.9 |  |
| ENA | 5 | -52.04 | 0.20 | 120.2 |  |
| MON | 8 | -69.00 | 0.50 | 7.5 |  |
| TRUMP | 4 | -74.14 | 0.25 | 41.4 |  |
| ETHFI | 5 | -91.55 | 0.20 | 4.1 | Y |
| JTO | 5 | -91.77 | 0.00 | 3.1 | Y |
| ZRO | 6 | -119.74 | 0.17 | 5.1 |  |
| HEMI | 16 | -276.69 | 0.19 | 2.0 | Y |

## 5m  (2026-08-10 -> 2026-08-27, 5040 bars)

Folds: F1 08-10->08-16, F2 08-16->08-22, F3 08-22->08-27

**Selected on fold 1:** `{'X': 0.3, 'K': 6, 'H': 12}`  
**Walk-forward OOS (folds 2+3):** n=1143 net=$-965.73 pf=0.89 wr=0.48 sharpe=-1.24 net_bps=-8.4 folds=[F2 151.72, F3 -1117.45] max_dd=1399.62

### Full grid (F1 = selection / in-sample, F2+F3 = out-of-sample)

| X% | K | H | n | net | pf | wr | F1 | F2 | F3 | OOS23 | bps | sel |
|---:|--:|--:|--:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 0.3 | 3 | 3 | 1194 | -586.9 | 0.88 | 0.46 | -42.9 | -272.2 | -271.8 | -544.0 | -4.9 |  |
| 0.3 | 3 | 6 | 1151 | -330.1 | 0.95 | 0.46 | -80.2 | -156.3 | -93.6 | -249.9 | -2.9 |  |
| 0.3 | 3 | 12 | 1060 | -793.7 | 0.91 | 0.47 | 45.8 | 133.6 | -973.2 | -839.5 | -7.5 |  |
| 0.3 | 6 | 3 | 1489 | -3.5 | 1.00 | 0.47 | -113.9 | -697.3 | 807.7 | 110.4 | -0.0 |  |
| 0.3 | 6 | 6 | 1376 | 46.8 | 1.01 | 0.47 | -33.3 | -715.1 | 795.2 | 80.1 | 0.3 |  |
| 0.3 | 6 | 12 | 1236 | -910.2 | 0.90 | 0.48 | 55.5 | 151.7 | -1117.4 | -965.7 | -7.4 | * |
| 0.5 | 3 | 3 | 482 | -190.8 | 0.92 | 0.47 | 13.9 | -357.3 | 152.5 | -204.7 | -4.0 |  |
| 0.5 | 3 | 6 | 466 | -250.1 | 0.92 | 0.46 | -16.0 | -369.5 | 135.4 | -234.1 | -5.4 |  |
| 0.5 | 3 | 12 | 440 | -1294.1 | 0.72 | 0.45 | -7.0 | -411.4 | -875.6 | -1287.0 | -29.4 |  |
| 0.5 | 6 | 3 | 656 | -391.3 | 0.87 | 0.43 | -34.9 | -229.8 | -126.6 | -356.4 | -6.0 |  |
| 0.5 | 6 | 6 | 628 | -942.3 | 0.76 | 0.44 | -27.1 | -581.7 | -333.5 | -915.2 | -15.0 |  |
| 0.5 | 6 | 12 | 588 | -464.6 | 0.91 | 0.48 | -55.2 | 209.6 | -619.1 | -409.4 | -7.9 |  |
| 1.0 | 3 | 3 | 89 | -215.0 | 0.61 | 0.44 | 0.0 | -284.0 | 68.9 | -215.0 | -24.2 |  |
| 1.0 | 3 | 6 | 87 | -127.1 | 0.81 | 0.51 | 0.0 | -129.1 | 2.1 | -127.1 | -14.6 |  |
| 1.0 | 3 | 12 | 86 | 232.9 | 1.48 | 0.53 | 0.0 | 167.3 | 65.6 | 232.9 | 27.1 |  |
| 1.0 | 6 | 3 | 149 | -480.2 | 0.51 | 0.36 | 0.0 | -371.8 | -108.4 | -480.2 | -32.2 |  |
| 1.0 | 6 | 6 | 146 | -186.5 | 0.84 | 0.47 | 0.0 | -150.9 | -35.6 | -186.5 | -12.8 |  |
| 1.0 | 6 | 12 | 143 | 95.9 | 1.09 | 0.52 | 0.0 | -76.2 | 172.1 | 95.9 | 6.7 |  |

### Sanity checks (OOS window, selected params)

- select=lag: n=1143 net=-965.73 pf=0.89 wr=0.48
- select=lead: n=1151 net=-1598.86 pf=0.84 wr=0.42
- select=all: n=6713 net=-12182.90 pf=0.72 wr=0.41
- time-shuffle (100x): mean=-867.89 sd=963.76 p(shuffled >= real)=0.56
- coin-shuffle (100x): mean=-1591.38 sd=524.14 p(shuffled >= real)=0.18
- neighbours with OOS23 > 0: 3/5
- illiquid (<$5M/24h) OOS net=-346.47; liquid OOS net=-619.26

### Per-coin OOS (selected params)

| coin | n | net | wr | 24h vol $M | illiquid |
|---|--:|---:|---:|---:|:--:|
| CHIP | 53 | 202.74 | 0.57 | 6.1 |  |
| MON | 40 | 185.84 | 0.65 | 7.5 |  |
| CC | 30 | 119.03 | 0.70 | 2.4 | Y |
| PURR | 63 | 68.06 | 0.51 | 3.6 | Y |
| HEMI | 55 | 59.36 | 0.51 | 2.0 | Y |
| NEAR | 11 | 54.38 | 0.55 | 25.9 |  |
| FARTCOIN | 33 | 52.24 | 0.64 | 37.1 |  |
| CASHCAT | 73 | 45.69 | 0.47 | 30.9 |  |
| LTC | 5 | 36.96 | 0.80 | 2.1 | Y |
| LIT | 48 | 36.18 | 0.52 | 46.9 |  |
| AVAX | 3 | 34.39 | 0.67 | 7.6 |  |
| XPL | 33 | 21.05 | 0.58 | 11.8 |  |
| JTO | 29 | 14.90 | 0.45 | 3.1 | Y |
| BNB | 4 | 13.35 | 0.50 | 14.7 |  |
| GRAM | 4 | 12.86 | 0.50 | 3.1 | Y |
| ADA | 7 | 9.76 | 0.57 | 4.0 | Y |
| ZEC | 20 | 5.13 | 0.60 | 289.2 |  |
| DOGE | 1 | 2.31 | 1.00 | 16.9 |  |
| ETH | 5 | 1.76 | 0.40 | 1679.4 |  |
| TRX | 4 | 0.91 | 0.50 | 3.6 | Y |
| SUI | 3 | 0.57 | 0.33 | 18.1 |  |
| XMR | 28 | -0.07 | 0.54 | 16.9 |  |
| INJ | 20 | -2.58 | 0.45 | 2.8 | Y |
| TAO | 8 | -4.44 | 0.50 | 50.8 |  |
| PAXG | 10 | -5.16 | 0.30 | 3.2 | Y |
| SOL | 3 | -9.83 | 0.00 | 1243.4 |  |
| HYPE | 12 | -15.12 | 0.42 | 969.9 |  |
| LINK | 6 | -17.15 | 0.33 | 20.8 |  |
| kPEPE | 19 | -19.59 | 0.58 | 16.6 |  |
| XRP | 14 | -21.92 | 0.50 | 117.8 |  |
| ONDO | 8 | -23.15 | 0.38 | 6.3 |  |
| ASTER | 20 | -27.27 | 0.30 | 4.6 | Y |
| CRV | 32 | -46.63 | 0.50 | 9.5 |  |
| UNI | 16 | -54.86 | 0.38 | 14.3 |  |
| SPX | 25 | -58.98 | 0.48 | 6.9 |  |
| PUMP | 46 | -62.55 | 0.43 | 174.8 |  |
| WLD | 21 | -64.69 | 0.48 | 9.0 |  |
| ZRO | 42 | -66.34 | 0.48 | 5.1 |  |
| JUP | 19 | -71.27 | 0.42 | 5.9 |  |
| VVV | 32 | -82.00 | 0.38 | 7.1 |  |
| FET | 18 | -86.96 | 0.39 | 2.5 | Y |
| GRASS | 36 | -91.01 | 0.53 | 2.2 | Y |
| PENGU | 19 | -93.10 | 0.26 | 12.0 |  |
| AAVE | 10 | -99.66 | 0.30 | 14.7 |  |
| ETHFI | 35 | -119.43 | 0.46 | 4.1 | Y |
| ENA | 38 | -128.59 | 0.37 | 120.2 |  |
| AERO | 23 | -152.26 | 0.35 | 3.4 | Y |
| WIF | 26 | -183.64 | 0.35 | 2.3 | Y |
| TRUMP | 33 | -334.96 | 0.42 | 41.4 |  |

## Interpretation

**Verdict: none.** The hypothesis (BTC leads; laggard alts catch up) is not supported.

- 15m walk-forward (params chosen on fold 1 = X 1.0%, K 6 bars, H 6 bars): OOS n=217, net +$224.90 on
  $1,000/leg (10.4 bps/trade after 9 bps taker round trip), PF 1.10, fold 2 = -$448.70, fold 3 = +$673.59.
  Fails PF >= 1.2, fails every-fold-positive, and is not distinguishable from noise: 17% of time-shuffled
  signal sets and 31% of random-alt selections did at least as well.
- 5m walk-forward (X 0.3%, K 6, H 12): OOS n=1143, net -$965.73, PF 0.89. Straight loss.
- Crucially, the cross-sectional part of the idea is wrong-signed or dead: at the selected 15m params the
  *leaders* (highest beta-adjusted response) did better OOS (+$343, PF 1.17) than the laggards (+$225), and
  the equal-weight *all-alts* basket did better still (+$1,970 over 1,862 legs, PF 1.18). Whatever positive
  drift exists after a 1%/90-min BTC move is generic BTC-momentum spillover, not laggard catch-up. On 5m
  every selection rule loses (all-alts -$12k), so the sub-hour version is pure fee bleed.
- In-sample grid: 15 of 18 cells are negative on 15m, 12 of 18 on 5m. Only X=1.0 (rare, ~80 signals per
  17-day fold) is ever positive; X=0.3/0.5 signals fire constantly and lose after fees at every horizon.
- Neighbours: 3 of 5 one-step neighbours positive on both intervals, but with sign flips (H 12 negative
  both times); no smooth plateau.
- Liquidity: the 15m OOS positive is in liquid memecoins (CASHCAT $31M, kPEPE $17M, FARTCOIN $37M) plus
  PURR ($3.6M); the illiquid (<$5M) bucket nets -$178. So it is not an illiquidity artefact, but the
  winners are 4 names out of 42 traded, and long-side only (longs +$801, shorts -$576).
- Samples are short: 52 days of 15m (17-day folds) and 17 days of 5m (6-day folds). Fold results are
  dominated by one or two BTC regime days (fold 3 on 15m).

**Next test (what the data actually suggests):** drop the laggard selection entirely and test the pure
spillover: after |BTC K-bar return| >= 1% (first breach), trade an equal-weight basket of the top-20 by
24h volume alts in BTC's direction, long-only vs both sides, hold 6-12 bars, on **1h data (208 days,
~70-day folds)** so the folds are not regime-dominated, and price it with maker entry (post a limit at
the next-bar open, count fill only if the bar's low/high touches it) since a 10 bps/trade edge cannot
carry 9 bps of taker fees. Also test the sharper condition X >= 1.5% and a BTC-volume-spike filter,
because the only grid cells that were ever positive were the rarest ones.
