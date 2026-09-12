# crypto_seasonality -- results

Data: yfinance BTC-USD + ETH-USD 1h, 2024-08-28 -> 2026-08-27 (729d). Folds: F1 2024-08-28->2025-04-28, F2 2025-04-28->2025-12-27, F3 2025-12-27->2026-08-27
Execution: decide at close of bar t-1, fill at open of bar t; exit at open after last held bar; HL taker fee both sides (9 bps RT); $10,000 notional/position.

## Descriptive: mean next-open return (bps) by UTC hour, pooled BTC+ETH, per fold
```
h    0    1    2    3    4    5    6    7    8    9    10   11   12   13   14   15   16   17   18   19   20   21   22   23
F1 -3.6  3.5  1.0  2.4  0.3  3.1 -2.5  1.5 -0.0  6.8 -1.2 -0.3 -0.4 -5.1  2.6  3.8 -0.3  2.6 -2.1 -3.2 -2.2  1.2  3.0 -2.0
F2 -4.5  1.0  6.1  3.8  2.1  0.2  0.4 -1.0  1.6 -1.6  0.5  2.0 -1.0 -0.9 -2.3 -5.5 -1.3  5.1 -3.5 -2.9  1.6  5.8  9.4 -2.8
F3  3.8 -0.3 -5.7  2.3 -1.0 -2.6 -5.2  1.1  2.5  0.7 -4.4  3.7  0.1 -6.9 -0.5  8.4 -2.2 -1.5 -4.7  7.8  3.8  6.0 -3.4 -3.2
```
Fold-to-fold rank correlation of hour means: F1vF2=0.24, F2vF3=-0.17, F1vF3=0.14

Mean next-open return (bps/hour) by weekday (0=Mon), per fold:
```
dow      0     1     2     3     4     5     6
fold                                          
0     0.14 -0.63  4.18 -2.04  2.62  1.05 -2.78
1    -0.41  0.31  3.02 -1.49 -1.93  0.48  3.71
2     3.71 -1.35  1.02 -3.96  1.27 -0.51 -0.55
```
BTC: mean bps hour-before 00/08/16 = 0.25, hour-after = -0.28, other hours = 0.39 (hourly std 48 bps, SE per hour-bucket ~1.8 bps)
ETH: mean bps hour-before 00/08/16 = -0.14, hour-after = -0.60, other hours = 0.47 (hourly std 71 bps, SE per hour-bucket ~2.6 bps)
Reference: round-trip taker fee = 9 bps; maker = 3 bps.

Hour ranking fitted on fold 1 only (worst->best): [13, 0, 19, 6, 20, 18, 23, 10, 12, 11, 16, 8, 4, 2, 21, 7, 3, 14, 17, 22, 5, 1, 15, 9]

## Walk-forward headline (select on F1 by net; OOS = F2+F3)
best_params = {'rule': 'weekend', 'dir': 'short'}
OOS: n= 138 net= -2979.59 pf=0.77 wr=0.33 sharpe= -0.98 net_bps=-21.59 folds=[0.0, -4671.3, 1691.7]
OOS folds (F2, F3) = [-4671.33, 1691.74], n per fold = [70, 68]

## In-sample grid (fold 1 metrics) plus each cell's per-fold net over the full period
```
 idx                   params  is_n   is_net  is_pf  is_net_bps       F1       F2       F3  all_n  all_pf  selected
   0  dir=long_k=1_rule=hours   486  -1083.2   0.88       -2.23  -1083.2  -5135.8  -4029.6   1456    0.65     False
   1 dir=short_k=1_rule=hours   484  -1955.7   0.87       -4.04  -1955.7  -3943.2  -1006.9   1454    0.83     False
   2  dir=both_k=1_rule=hours   970  -3038.9   0.87       -3.13  -3038.9  -9079.0  -5036.5   2910    0.76     False
   3  dir=long_k=2_rule=hours   972  -3589.9   0.86       -3.69  -3589.9 -12167.0  -4330.7   2914    0.74     False
   4 dir=short_k=2_rule=hours   972  -4605.6   0.83       -4.74  -4605.6  -6093.3  -7220.1   2911    0.76     False
   5  dir=both_k=2_rule=hours  1944  -8195.6   0.85       -4.22  -8195.6 -18260.4 -11550.8   5825    0.75     False
   6  dir=long_k=3_rule=hours  1460  -6283.6   0.84       -4.30  -6283.6 -16034.5  -8690.6   4370    0.73     False
   7 dir=short_k=3_rule=hours  1458  -7399.5   0.82       -5.08  -7399.5  -9074.2 -15425.1   4371    0.72     False
   8  dir=both_k=3_rule=hours  2918 -13683.1   0.83       -4.69 -13683.1 -25108.7 -24115.7   8741    0.72     False
   9  dir=long_k=4_rule=hours  1948  -9165.4   0.82       -4.71  -9165.4 -20258.9 -14331.9   5826    0.70     False
  10 dir=short_k=4_rule=hours  1946 -10555.4   0.79       -5.42 -10555.4 -13646.1 -17275.7   5826    0.71     False
  11  dir=both_k=4_rule=hours  3894 -19720.8   0.80       -5.06 -19720.8 -33905.0 -31607.6  11652    0.70     False
  12    dir=long_rule=weekend    70  -1730.7   0.80      -24.72  -1730.7   3407.7  -2913.7    208    0.94     False
  13   dir=short_rule=weekend    70    471.7   1.06        6.74    471.7  -4671.3   1691.7    208    0.88      True
  14    dir=long_rule=us_sess   346  -5322.6   0.84      -15.38  -5322.6  -8680.4  -2313.5   1044    0.83     False
  15   dir=short_rule=us_sess   346   -903.4   0.97       -2.61   -903.4   2385.4  -3951.2   1044    0.97     False
  16  dir=long_rule=asia_sess   348     18.9   1.00        0.05     18.9  -1771.7  -4599.9   1041    0.90     False
  17 dir=short_rule=asia_sess   348  -6285.8   0.76      -18.06  -6285.8  -4439.5  -1662.8   1041    0.81     False
  18   dir=long_rule=fund_pre  1460 -11500.5   0.71       -7.88 -11500.5 -17528.4 -10045.1   4368    0.65     False
  19  dir=short_rule=fund_pre  1460 -14781.0   0.64      -10.12 -14781.0  -8531.6 -16237.7   4368    0.64     False
  20  dir=long_rule=fund_post  1460 -15037.6   0.63      -10.30 -15037.6 -15069.0 -11147.6   4370    0.62     False
  21 dir=short_rule=fund_post  1460 -11240.7   0.71       -7.70 -11240.7 -11029.2 -15134.2   4370    0.65     False
```

## Per-family walk-forward (best cell of each family chosen on F1; OOS F2+F3)
```
   family                     best  oos_n  oos_net  oos_pf  oos_net_bps       F2       F3
    hours  dir=long_k=1_rule=hours    970  -9165.4    0.54        -9.45  -5135.8  -4029.6
  weekend   dir=short_rule=weekend    138  -2979.6    0.77       -21.59  -4671.3   1691.7
  us_sess   dir=short_rule=us_sess    698  -1565.8    0.97        -2.24   2385.4  -3951.2
asia_sess  dir=long_rule=asia_sess    693  -6371.6    0.84        -9.19  -1771.7  -4599.9
 fund_pre   dir=long_rule=fund_pre   2908 -27573.5    0.61        -9.48 -17528.4 -10045.1
fund_post dir=short_rule=fund_post   2910 -26163.5    0.62        -8.99 -11029.2 -15134.2
```

## Headline rule OOS per symbol
BTC: n=  69 net=  -926.64 pf=0.79 wr=0.30 sharpe= -0.65 net_bps=-13.43 folds=[0.0, -1557.5, 630.9]
ETH: n=  69 net= -2052.95 pf=0.76 wr=0.35 sharpe= -0.76 net_bps=-29.75 folds=[0.0, -3113.8, 1060.9]

Maker-both-sides sensitivity (best case, NOT verifiable fills): n= 138 net= -2151.07 pf=0.83 wr=0.36 sharpe= -0.70 net_bps=-15.59 folds=[0.0, -4250.1, 2099.0]
Zero-fee OOS (gross signal only): n= 138 net= -1736.81 pf=0.86 wr=0.36 sharpe= -0.57 net_bps=-12.59 folds=[0.0, -4039.5, 2302.7]

## Sanity (a): shuffle test -- random circular shift of the clock (1..167h), 300 draws, OOS net
actual OOS net = -2979.6; null mean = -3176.4, sd = 5620.0, 5/50/95 pct = -11896.4/-3654.5/7553.1; actual percentile in null = 0.540

## Sanity (c): neighbouring parameters of the selected rule (OOS F2+F3)
```
                                    params  oos_n  oos_net  oos_pf      F2     F3
dir=short_end_h=21_rule=weekend_start_h=19    138  -3767.9    0.74 -4834.5 1066.6
dir=short_end_h=21_rule=weekend_start_h=23    138  -2449.4    0.81 -5246.6 2797.2
dir=short_end_h=19_rule=weekend_start_h=21    138  -4741.6    0.66 -5446.3  704.8
dir=short_end_h=23_rule=weekend_start_h=21    138  -7114.2    0.58 -7030.9  -83.3
dir=short_end_h=20_rule=weekend_start_h=20    138  -3216.0    0.78 -4404.9 1188.9
dir=short_end_h=22_rule=weekend_start_h=22    138  -2330.1    0.82 -4429.0 2098.9
```

## Sanity (d): Hyperliquid 1h universe (208d, fully inside yf fold 3 => OOS for the F1-selected rule)
```
    coin  dayNtlVlm_m  n      net   pf  net_bps                       folds
     BTC       3699.5 30    448.7 1.31    14.96      [785.0, 149.0, -486.0]
     ETH       1679.4 30    917.3 1.39    30.58    [1763.0, 169.0, -1015.0]
     SOL       1243.4 30    863.3 1.32    28.78    [1872.0, 520.0, -1529.0]
    HYPE        969.9 30  -3266.3 0.48  -108.88  [-465.0, -1632.0, -1169.0]
     ZEC        289.2 30  -4364.7 0.56  -145.49  [1032.0, -2870.0, -2526.0]
    PUMP        174.8 30  -6617.5 0.36  -220.58    [217.0, 1082.0, -7916.0]
     ENA        120.2 30   4750.5 2.34   158.35   [3526.0, 2680.0, -1455.0]
     XRP        117.8 30   -480.3 0.83   -16.01     [900.0, 167.0, -1548.0]
     TAO         50.8 30  -6164.9 0.39  -205.50 [-1392.0, -2897.0, -1876.0]
     LIT         46.9 30   1475.9 1.23    49.20    [3625.0, 821.0, -2970.0]
   TRUMP         41.4 30     80.1 1.01     2.67   [2044.0, 2567.0, -4531.0]
FARTCOIN         37.1 30   2865.3 1.77    95.51   [3004.0, 1301.0, -1439.0]
 CASHCAT         30.9  7  -5057.6 0.48  -722.51  [-2773.0, -4524.0, 2240.0]
    NEAR         25.9 30   -108.4 0.97    -3.61    [1027.0, -262.0, -874.0]
    LINK         20.8 30   1328.5 1.53    44.28    [2039.0, 524.0, -1234.0]
     SUI         18.1 30    818.0 1.17    27.27   [3143.0, -1721.0, -604.0]
    DOGE         16.9 30   1944.7 1.79    64.82    [1628.0, 1229.0, -912.0]
     XMR         16.9 30  -1341.7 0.75   -44.72   [1324.0, -928.0, -1738.0]
   kPEPE         16.6 30   1335.6 1.30    44.52   [1832.0, 2019.0, -2514.0]
    AAVE         14.7 30   1161.4 1.25    38.71   [1339.0, 2180.0, -2358.0]
     BNB         14.7 30   -225.8 0.93    -7.53   [1583.0, -737.0, -1072.0]
     UNI         14.3 30   1049.2 1.30    34.97    [1689.0, 680.0, -1320.0]
   PENGU         12.0 30     88.1 1.01     2.94   [3086.0, 1160.0, -4158.0]
     XPL         11.8 30   7113.2 3.69   237.11    [2311.0, 2763.0, 2039.0]
     CRV          9.5 30   3542.7 2.11   118.09   [3060.0, 1820.0, -1337.0]
     WLD          9.0 30    686.6 1.10    22.89  [3258.0, -1155.0, -1417.0]
    AVAX          7.6 30   2501.2 2.17    83.37    [1810.0, 1535.0, -843.0]
     MON          7.5 30   3584.0 2.21   119.47     [1644.0, 1793.0, 147.0]
     VVV          7.1 30 -17750.6 0.25  -591.69 [-9102.0, -7257.0, -1391.0]
     SPX          6.9 30   2114.0 1.53    70.47     [757.0, 1763.0, -407.0]
    ONDO          6.3 30   3944.4 2.26   131.48      [2433.0, 558.0, 953.0]
    CHIP          6.1 18    193.7 1.03    10.76  [4295.0, -1848.0, -2253.0]
     JUP          5.9 30   1113.5 1.21    37.12    [2352.0, 256.0, -1494.0]
     ZRO          5.1 30   -394.7 0.95   -13.16  [-2148.0, 2977.0, -1224.0]
   ASTER          4.6 30  -1457.1 0.64   -48.57     [-295.0, -1223.0, 61.0]
   ETHFI          4.1 30   2628.7 1.59    87.62   [2593.0, 2188.0, -2153.0]
     ADA          4.0 30   2973.0 2.21    99.10   [2508.0, 1525.0, -1059.0]
    PURR          3.6 30  -5683.2 0.50  -189.44  [1360.0, -2782.0, -4261.0]
     TRX          3.6 30  -3604.3 0.07  -120.14  [-1397.0, -1364.0, -843.0]
    AERO          3.4 30   2420.5 1.58    80.68      [1794.0, 308.0, 319.0]
    PAXG          3.2 30   -474.4 0.54   -15.81      [-316.0, 74.0, -233.0]
    GRAM          3.1  8   -877.1 0.29  -109.63    [-137.0, -527.0, -214.0]
     JTO          3.1 30   4657.9 1.90   155.26    [3615.0, -976.0, 2019.0]
     INJ          2.8 30   2817.7 1.75    93.92      [1932.0, 305.0, 581.0]
     FET          2.5 30    141.9 1.02     4.73    [851.0, -2015.0, 1306.0]
      CC          2.4 30  -2475.2 0.59   -82.51  [1254.0, -1714.0, -2016.0]
     WIF          2.3 30   4026.1 2.16   134.20   [4195.0, 2111.0, -2280.0]
   GRASS          2.2 30  -3050.2 0.68  -101.67   [176.0, -1879.0, -1348.0]
     LTC          2.1 30   1100.7 1.45    36.69   [1949.0, 1049.0, -1897.0]
    HEMI          2.0 30    393.1 1.05    13.10   [3095.0, -730.0, -1972.0]
```
liquid (>=$5M/d): 34 coins, 23 positive, sum net=-1853, median net_bps=28.02
illiquid (<$5M/d): 16 coins, 9 positive, sum net=3538, median net_bps=8.91
HL majors: BTC n=30 net=448.7 pf=1.31; ETH n=30 net=917.3 pf=1.39; SOL n=30 net=863.3 pf=1.32

## Secondary: independent walk-forward on HL BTC+ETH+SOL 1h (208d; own fold-1 hour ranking)
best_params = {'rule': 'hours', 'k': 4, 'dir': 'both'}; OOS: n=3336 net=-28693.08 pf=0.58 wr=0.38 sharpe=-10.10 net_bps= -8.60 folds=[0.0, -15733.2, -12959.9]
HL fold-1 hour ranking (worst->best): [6, 10, 23, 17, 14, 2, 5, 12, 13, 16, 11, 4, 18, 22, 3, 8, 20, 21, 1, 0, 9, 7, 19, 15]; Spearman vs yf-F1 ranking = 0.21

## Verdict
criteria = {'net_pos': False, 'pf': False, 'n': True, 'folds': False, 'shuffle': False, 'neighbors': False}
**none**

## Interpretation

- Hour-of-day means are ~+/-5 bps/hour with an hourly return std of 48 bps (BTC) / 71 bps (ETH). With ~243 observations per hour per fold the standard error per hour bucket is ~2-3 bps, so the fold tables are indistinguishable from noise; fold-to-fold Spearman correlation of the 24 hour means is 0.24 / -0.17 / 0.14. Even IN-SAMPLE (fold 1, hour set fitted on itself) every 'hours' cell loses money because the fitted 5-7 bps/hour edge is smaller than the 9 bps taker round trip. Zero-fee OOS for the hours family is also negative, so it is not just a fee problem.
- Funding clock (legacy 00/08/16 UTC): hour-before vs hour-after means are +0.25/-0.28 bps (BTC), -0.14/-0.60 bps (ETH) -- nothing. HL settles hourly so there is no settlement clock left to trade on the venue anyway.
- Sessions: US-open long/short and Asia-open long/short all lose OOS; the sign flips between folds (us_sess short: F2 +2385, F3 -3951).
- Weekend (Fri 21 -> Sun 21 UTC): the selected cell (short) was picked on a fold-1 net of +472 (pf 1.06, 70 trades), which is a coin flip. OOS: F2 -4671, F3 +1692, net -2980, pf 0.77. The weekend P&L simply tracks the fold's BTC/ETH trend (long weekend: F1 -1731, F2 +3408, F3 -2914). Shuffle null percentile 0.54; all six neighbouring windows are negative OOS. Zero-fee OOS is also negative (-1737), so fees are not the reason it fails.
- HL universe (208d, coincides with yf fold 3, where weekend-short happened to be positive): 32/50 coins positive, concentrated in a 2026 alt-drawdown period; BTC/ETH/SOL sub-fold 3 all negative. Liquid vs illiquid split shows no liquidity concentration (liquid median 28 bps/trade, illiquid 9 bps/trade); this is one regime, not evidence of seasonality. Independent walk-forward on HL BTC+ETH+SOL picks hours k=4 both and loses -28.7k OOS (pf 0.58).

Verdict: none. No clock-based rule survives fees or even beats a random clock shift.
