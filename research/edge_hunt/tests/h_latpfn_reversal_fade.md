# latpfn_reversal_fade - round 4

## Part A - CME mirror test (saved lagged-mode backtests, 60 days of 5m bars to 2026-08-26)

trades loaded: 300  by mode {'lagged': 192, 'lagged-bc': 108}  by instrument {'MYM': 114, 'MES': 77, 'MNQ': 76, 'MBT': 33}
tiers: {'layup': 122, 'three_pointer': 61, 'short_range': 60, 'free_throw': 46, 'half_court': 11}  exit reasons: {'timeout': 144, 'stop_loss': 95, 'take_profit': 61}
model (RAW) gross P&L per instrument/mode, as saved:
                       n    gross    wr
mode      instrument                   
lagged    MBT         29    26.06  0.59
          MES         51  -336.96  0.47
          MNQ         47 -3625.73  0.26
          MYM         65  -206.52  0.49
lagged-bc MBT          4    89.29  0.75
          MES         26   101.28  0.65
          MNQ         29   -98.77  0.48
          MYM         49  -297.29  0.53

model-side hit rate by tier (gross pnl > 0), pooled, and by order-third:
- free_throw     n= 46 wr=0.52 gross=  -263.6 | folds ['0.69(n=13)', '0.43(n=14)', '0.47(n=19)']
- half_court     n= 11 wr=0.45 gross=  -286.3 | folds ['0.25(n=4)', '0.67(n=3)', '0.50(n=4)']
- layup          n=122 wr=0.43 gross= -3250.3 | folds ['0.35(n=43)', '0.51(n=37)', '0.43(n=42)']
- short_range    n= 60 wr=0.48 gross=  -664.7 | folds ['0.32(n=25)', '0.74(n=19)', '0.44(n=16)']
- three_pointer  n= 61 wr=0.57 gross=   116.2 | folds ['0.69(n=16)', '0.60(n=25)', '0.45(n=20)']

## Part A walk-forward: select on order-third 1 (pooled across instruments), OOS = thirds 2+3

| arm | modes | f1 n | f1 net | f1 pf | OOS n | OOS net | OOS pf | OOS wr | f1 | f2 | f3 | sel |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RAW | lagged | 65 | -2366.1 | 0.29 | 127 | -2327.1 | 0.51 | 0.45 | -2366.1 | -397.2 | -1929.9 |  |
| INV | lagged | 65 | 1993.9 | 2.78 | 127 | 1599.2 | 1.57 | 0.53 | 1993.9 | 41.5 | 1557.7 |  |
| INV_LAYUP | lagged | 39 | 1152.8 | 2.86 | 74 | 1120.7 | 1.64 | 0.53 | 1152.8 | 0.3 | 1120.4 |  |
| INV_CONF60 | lagged | 39 | 1152.8 | 2.86 | 74 | 1120.7 | 1.64 | 0.53 | 1152.8 | 0.3 | 1120.4 |  |
| INV_CONF52 | lagged | 53 | 2124.9 | 3.55 | 87 | 787.0 | 1.35 | 0.51 | 2124.9 | -178.5 | 965.6 |  |
| INV_LOW | lagged | 12 | -131.0 | 0.54 | 40 | 812.1 | 2.47 | 0.57 | -131.0 | 220.0 | 592.1 |  |
| RAW_LOW | lagged | 12 | 65.3 | 1.38 | 40 | -1042.3 | 0.30 | 0.40 | 65.3 | -333.6 | -708.7 |  |
| RAW | lagged-bc | 36 | -490.5 | 0.72 | 72 | -1.9 | 1.00 | 0.56 | -490.5 | 774.0 | -776.0 |  |
| INV | lagged-bc | 36 | 299.2 | 1.22 | 72 | -380.6 | 0.86 | 0.40 | 299.2 | -965.3 | 584.7 |  |
| INV_LAYUP | lagged-bc | 4 | 375.0 | inf | 5 | 246.1 | 3.37 | 0.60 | 375.0 | 35.1 | 211.0 |  |
| INV_CONF60 | lagged-bc | 4 | 375.0 | inf | 5 | 246.1 | 3.37 | 0.60 | 375.0 | 35.1 | 211.0 |  |
| INV_CONF52 | lagged-bc | 15 | 298.8 | 1.68 | 27 | 184.1 | 1.23 | 0.37 | 298.8 | -278.8 | 462.9 |  |
| INV_LOW | lagged-bc | 21 | 0.4 | 1.00 | 45 | -564.7 | 0.72 | 0.42 | 0.4 | -686.5 | 121.8 |  |
| RAW_LOW | lagged-bc | 21 | -106.4 | 0.89 | 45 | 333.1 | 1.22 | 0.58 | -106.4 | 573.0 | -239.9 |  |
| RAW | both | 101 | -2856.6 | 0.44 | 199 | -2329.1 | 0.68 | 0.49 | -2856.6 | 376.8 | -2705.8 |  |
| INV | both | 101 | 2293.1 | 1.92 | 199 | 1218.5 | 1.22 | 0.48 | 2293.1 | -923.8 | 2142.4 |  |
| INV_LAYUP | both | 43 | 1527.8 | 3.47 | 79 | 1366.8 | 1.74 | 0.53 | 1527.8 | 35.4 | 1331.4 |  |
| INV_CONF60 | both | 43 | 1527.8 | 3.47 | 79 | 1366.8 | 1.74 | 0.53 | 1527.8 | 35.4 | 1331.4 |  |
| INV_CONF52 | both | 68 | 2423.8 | 2.90 | 114 | 971.1 | 1.32 | 0.47 | 2423.8 | -457.3 | 1428.4 | * |
| INV_LOW | both | 33 | -130.7 | 0.89 | 85 | 247.4 | 1.10 | 0.49 | -130.7 | -466.5 | 713.9 |  |
| RAW_LOW | both | 33 | -41.2 | 0.96 | 85 | -709.2 | 0.77 | 0.49 | -41.2 | 239.4 | -948.6 |  |

selected on third 1: arm=INV_CONF52 modes=both
**Part A OOS (thirds 2+3): n= 114 net=   971.11 pf=1.32 wr=0.474 sh=  1.09 folds=[0.0, -457.3, 1428.4] bps=2.16**

### Part A sanity (selected variant, OOS period)
neighbours (no reselection):
- arm=RAW       : n= 199 net= -2329.05 pf=0.68 wr=0.487 sh= -1.92 folds=[0.0, 376.8, -2705.8]
- arm=INV       : n= 199 net=  1218.53 pf=1.22 wr=0.482 sh=  1.01 folds=[0.0, -923.8, 2142.4]
- arm=INV_LAYUP : n=  79 net=  1366.79 pf=1.74 wr=0.532 sh=  1.84 folds=[0.0, 35.4, 1331.4]
- arm=INV_CONF60: n=  79 net=  1366.79 pf=1.74 wr=0.532 sh=  1.84 folds=[0.0, 35.4, 1331.4]
- arm=INV_CONF52: n= 114 net=   971.11 pf=1.32 wr=0.474 sh=  1.09 folds=[0.0, -457.3, 1428.4]
- arm=INV_LOW   : n=  85 net=   247.42 pf=1.10 wr=0.494 sh=  0.30 folds=[0.0, -466.5, 713.9]
- arm=RAW_LOW   : n=  85 net=  -709.22 pf=0.77 wr=0.494 sh= -0.86 folds=[0.0, 239.4, -948.6]
- modes=lagged   : n=  87 net=   787.03 pf=1.35 wr=0.506 sh=  1.04 folds=[0.0, -178.5, 965.6]
- modes=lagged-bc: n=  27 net=   184.08 pf=1.23 wr=0.370 sh=  0.39 folds=[0.0, -278.8, 462.9]
- modes=both     : n= 114 net=   971.11 pf=1.32 wr=0.474 sh=  1.09 folds=[0.0, -457.3, 1428.4]
per-instrument OOS:
             n      net    wr
instrument                   
MBT          8   -38.14  0.38
MES         38   -77.52  0.45
MNQ         35  1367.58  0.63
MYM         33  -280.81  0.36
positive instruments: 1/4
neighbour INV_LAYUP OOS per-instrument: {'MBT': -38.1, 'MES': -108.8, 'MNQ': 1683.9, 'MYM': -170.1} (n {'MBT': 8, 'MES': 28, 'MNQ': 24, 'MYM': 19}) | by model exit reason: {'stop_loss': 2783.0, 'take_profit': -1730.7, 'timeout': 314.5}
neighbour INV OOS per-instrument: {'MBT': -155.2, 'MES': -96.3, 'MNQ': 1458.0, 'MYM': 12.0} (n {'MBT': 22, 'MES': 51, 'MNQ': 50, 'MYM': 76}) | by model exit reason: {'stop_loss': 4934.9, 'take_profit': -3330.3, 'timeout': -386.1}
per-tier OOS:
              n      net    wr
tier                          
layup        79  1366.79  0.53
short_range  35  -395.68  0.34
by model exit reason OOS:
             count      sum
reason                     
stop_loss       40  3434.94
take_profit     39 -2459.95
timeout         35    -3.88
top-3 removal: net 971.1 -> 1059.0 pf 1.37 folds [0.0, -407.4, 1466.5]
shuffle (model sides permuted within instrument x mode, 1000 reps): actual 971.1; shuffled mean -234.2 sd 812.8 p95 1156.9; P(shuffle >= actual) = 0.072
coin-flip sides on the same trades (OOS): mean -568.4 sd 1222.4; P(coinflip >= actual) = 0.111
order-sixths net (OOS covers sixths 3-6): {2: 500.3, 3: 288.6, 4: 89.2, 5: 93.0}
OOS decisions: 114 mirror trades (4 instruments); the same 60 days for every instrument -> effective independent periods are far fewer than trades.

Part A criteria: {"net_pos": true, "pf": true, "n": true, "folds": false}

## Part B - Hyperliquid 1h (tests/h_latpfn_reversal_fade_hl.py)
Forecasts: 11798  usable signals: 11798  coins (20): AAVE, BTC, DOGE, ENA, ETH, FARTCOIN, HYPE, LINK, LIT, NEAR, PUMP, SOL, SUI, TAO, TRUMP, UNI, WLD, XMR, XRP, ZEC
Period 2026-03-09 -> 2026-08-27; folds: [03-09,05-05), [05-05,07-01), [07-01,08-27)
## Walk-forward (taker) - select on fold 1, OOS = folds 2+3
selected on fold 1: {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12}
OOS (folds 2+3): n= 5184 net=-16708.03 pf=0.74 wr=0.483 sh= -6.81 bps=-32.23 folds=[0.0, -8406.7, -8301.3]
### Sanity (taker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
- H=4: n= 5207 net= -7869.22 pf=0.78 wr=0.471 sh= -5.43 bps=-15.11 folds=[0.0, -3591.5, -4277.8]
- H=8: n= 5190 net=-11811.33 pf=0.78 wr=0.488 sh= -5.94 bps=-22.76 folds=[0.0, -4891.5, -6919.8]
- H=12: n= 5184 net=-16708.03 pf=0.74 wr=0.483 sh= -6.81 bps=-32.23 folds=[0.0, -8406.7, -8301.3]
- arm=RAW: n= 7783 net=-19616.78 pf=0.79 wr=0.480 sh= -6.73 bps=-25.20 folds=[0.0, -10455.0, -9161.8]
- arm=FADE: n= 5184 net=  7275.48 pf=1.14 wr=0.475 sh=  2.97 bps= 14.03 folds=[0.0, 3647.6, 3627.9]
- arm=F_AGREE: n= 2589 net= -2870.08 pf=0.89 wr=0.475 sh= -1.83 bps=-11.09 folds=[0.0, -1982.1, -888.0]
- arm=F_DISAGR: n= 5184 net=-16708.03 pf=0.74 wr=0.483 sh= -6.81 bps=-32.23 folds=[0.0, -8406.7, -8301.3]
- arm=F_CONF: n= 5072 net=-14993.67 pf=0.76 wr=0.493 sh= -6.10 bps=-29.56 folds=[0.0, -8567.0, -6426.7]
- arm=INV: n= 7783 net=  5476.47 pf=1.07 wr=0.475 sh=  1.88 bps=  7.04 folds=[0.0, 3350.3, 2126.2]
- arm=INV_CONF: n= 5072 net=  5767.11 pf=1.11 wr=0.464 sh=  2.35 bps= 11.37 folds=[0.0, 3960.4, 1806.7]
- arm=INV_HI: n= 2595 net=  8595.06 pf=1.31 wr=0.469 sh=  4.31 bps= 33.12 folds=[0.0, 4594.8, 4000.2]
shuffle (model directions permuted within coin, 200 reps, OOS period): actual -16708.0; shuffled mean -10031.4 sd 1443.2 p5 -12428.4 p95 -7742.9; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -5374.5 sd 2388.2; P(random >= actual) = 1.000
top-3 removal (selected): net -16708.0 -> -17355.5 pf 0.73 folds [0.0, -8861.3, -8494.2]
top-3 removal (INV): net 5476.5 -> 4217.0 pf 1.05 folds [0.0, 3003.4, 1213.6]
positive coins: 2/20; illiquid names in universe: 0
secondary [INV_HI basis=wrap60 H=12]: fold1 (in-sample) net -1983.4 pf 0.84 n 1084 | OOS n= 2595 net=  8595.06 pf=1.31 wr=0.469 sh=  4.31 bps= 33.12 folds=[0.0, 4594.8, 4000.2]
  shuffle P(>=actual)=0.000 (mean -729.5 sd 1699.1) | random-bar same side-mix P(>=actual)=0.000 (mean -795.7 sd 1500.4) | positive coins 19/20 | top-3 removal net 7492.8 folds [0.0, 4247.9, 3244.9] | monthly {'05': 998.0, '06': 3504.0, '07': -797.0, '08': 4889.0}
  by side: n {-1.0: 998, 1.0: 1597} net {-1.0: 1499.8, 1.0: 7095.3}
secondary [INV_CONF basis=wrap60 H=12]: fold1 (in-sample) net -4868.0 pf 0.81 n 2297 | OOS n= 5072 net=  5767.11 pf=1.11 wr=0.464 sh=  2.35 bps= 11.37 folds=[0.0, 3960.4, 1806.7]
  shuffle P(>=actual)=0.000 (mean -2813.6 sd 2186.0) | random-bar same side-mix P(>=actual)=0.000 (mean -3051.4 sd 2133.3) | positive coins 15/20 | top-3 removal net 4979.4 folds [0.0, 3881.5, 1097.9] | monthly {'05': 2029.0, '06': 1779.0, '07': -3144.0, '08': 5103.0}
  by side: n {-1.0: 2398, 1.0: 2674} net {-1.0: -1299.8, 1.0: 7066.9}
secondary [INV basis=wrap60 H=12]: fold1 (in-sample) net -6216.2 pf 0.85 n 3908 | OOS n= 7783 net=  5476.47 pf=1.07 wr=0.475 sh=  1.88 bps=  7.04 folds=[0.0, 3350.3, 2126.2]
  shuffle P(>=actual)=0.000 (mean -5227.7 sd 3182.3) | random-bar same side-mix P(>=actual)=0.000 (mean -5678.7 sd 2800.2) | positive coins 15/20 | top-3 removal net 4217.0 folds [0.0, 3003.4, 1213.6] | monthly {'05': 807.0, '06': 2463.0, '07': -3508.0, '08': 5715.0}
  by side: n {-1.0: 3922, 1.0: 3861} net {-1.0: -2495.8, 1.0: 7972.3}
secondary [FADE basis=wrap60 H=12]: fold1 (in-sample) net -7086.4 pf 0.76 n 2572 | OOS n= 5184 net=  7275.48 pf=1.14 wr=0.475 sh=  2.97 bps= 14.03 folds=[0.0, 3647.6, 3627.9]
  shuffle P(>=actual)=0.005 (mean 3059.7 sd 1491.0) | random-bar same side-mix P(>=actual)=0.000 (mean -4024.0 sd 2440.6) | positive coins 17/20 | top-3 removal net 6219.8 folds [0.0, 3300.7, 2919.1] | monthly {'05': 334.0, '06': 3333.0, '07': -1316.0, '08': 4925.0}
  by side: n {-1.0: 2601, 1.0: 2583} net {-1.0: -814.4, 1.0: 8089.9}
## Walk-forward (maker) - select on fold 1, OOS = folds 2+3
selected on fold 1: {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12}
OOS (folds 2+3): n= 4608 net=-17129.52 pf=0.72 wr=0.477 sh= -7.43 bps=-37.17 folds=[0.0, -8992.0, -8137.5]
### Sanity (maker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
- H=4: n= 4631 net= -9085.17 pf=0.73 wr=0.463 sh= -6.50 bps=-19.62 folds=[0.0, -4114.8, -4970.3]
- H=8: n= 4614 net=-12591.01 pf=0.74 wr=0.480 sh= -6.57 bps=-27.29 folds=[0.0, -5435.4, -7155.6]
- H=12: n= 4608 net=-17129.52 pf=0.72 wr=0.477 sh= -7.43 bps=-37.17 folds=[0.0, -8992.0, -8137.5]
- arm=RAW: n= 6976 net=-20384.16 pf=0.76 wr=0.476 sh= -7.36 bps=-29.22 folds=[0.0, -11082.2, -9302.0]
- arm=FADE: n= 4726 net=  3685.44 pf=1.07 wr=0.466 sh=  1.57 bps=  7.80 folds=[0.0, 1846.4, 1839.1]
- arm=F_AGREE: n= 2359 net= -3220.38 pf=0.87 wr=0.476 sh= -2.10 bps=-13.65 folds=[0.0, -2025.6, -1194.8]
- arm=F_DISAGR: n= 4608 net=-17129.52 pf=0.72 wr=0.477 sh= -7.43 bps=-37.17 folds=[0.0, -8992.0, -8137.5]
- arm=F_CONF: n= 4531 net=-15427.05 pf=0.74 wr=0.491 sh= -6.67 bps=-34.05 folds=[0.0, -8942.8, -6484.3]
- arm=INV: n= 7044 net=  1139.00 pf=1.02 wr=0.466 sh=  0.41 bps=  1.62 folds=[0.0, 747.5, 391.5]
- arm=INV_CONF: n= 4637 net=  2400.67 pf=1.05 wr=0.458 sh=  1.02 bps=  5.18 folds=[0.0, 1806.0, 594.7]
- arm=INV_HI: n= 2413 net=  6302.61 pf=1.24 wr=0.467 sh=  3.32 bps= 26.12 folds=[0.0, 3303.6, 2999.0]
shuffle (model directions permuted within coin, 200 reps, OOS period): actual -17129.5; shuffled mean -10652.4 sd 1383.0 p5 -12858.8 p95 -8392.7; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -6793.7 sd 2181.0; P(random >= actual) = 1.000
top-3 removal (selected): net -17129.5 -> -17421.0 pf 0.71 folds [0.0, -9266.4, -8154.6]
top-3 removal (INV): net 1139.0 -> 962.1 pf 1.01 folds [0.0, 697.7, 264.4]
positive coins: 1/20; illiquid names in universe: 0
secondary [INV_HI basis=wrap60 H=12]: fold1 (in-sample) net -1939.4 pf 0.84 n 996 | OOS n= 2413 net=  6302.61 pf=1.24 wr=0.467 sh=  3.32 bps= 26.12 folds=[0.0, 3303.6, 2999.0]
  shuffle P(>=actual)=0.000 (mean -1798.4 sd 1541.4) | random-bar same side-mix P(>=actual)=0.000 (mean -1620.2 sd 1576.1) | positive coins 16/20 | top-3 removal net 5260.1 folds [0.0, 3037.1, 2223.0] | monthly {'05': 784.0, '06': 2423.0, '07': -1065.0, '08': 4161.0}
  by side: n {-1.0: 926, 1.0: 1487} net {-1.0: 554.8, 1.0: 5747.8}
secondary [INV_CONF basis=wrap60 H=12]: fold1 (in-sample) net -5066.4 pf 0.78 n 2063 | OOS n= 4637 net=  2400.67 pf=1.05 wr=0.458 sh=  1.02 bps=  5.18 folds=[0.0, 1806.0, 594.7]
  shuffle P(>=actual)=0.000 (mean -4799.6 sd 2299.6) | random-bar same side-mix P(>=actual)=0.000 (mean -4199.6 sd 2157.7) | positive coins 14/20 | top-3 removal net 1657.8 folds [0.0, 1772.5, -114.7] | monthly {'05': 1413.0, '06': 227.0, '07': -3487.0, '08': 4247.0}
  by side: n {-1.0: 2172, 1.0: 2465} net {-1.0: -2716.6, 1.0: 5117.3}
secondary [INV basis=wrap60 H=12]: fold1 (in-sample) net -6710.3 pf 0.82 n 3505 | OOS n= 7044 net=  1139.00 pf=1.02 wr=0.466 sh=  0.41 bps=  1.62 folds=[0.0, 747.5, 391.5]
  shuffle P(>=actual)=0.000 (mean -8262.6 sd 2477.8) | random-bar same side-mix P(>=actual)=0.000 (mean -6921.3 sd 2531.1) | positive coins 11/20 | top-3 removal net 962.1 folds [0.0, 697.7, 264.4] | monthly {'05': 129.0, '06': 517.0, '07': -4183.0, '08': 4676.0}
  by side: n {-1.0: 3515, 1.0: 3529} net {-1.0: -4807.2, 1.0: 5946.2}
secondary [FADE basis=wrap60 H=12]: fold1 (in-sample) net -6953.4 pf 0.74 n 2308 | OOS n= 4726 net=  3685.44 pf=1.07 wr=0.466 sh=  1.57 bps=  7.80 folds=[0.0, 1846.4, 1839.1]
  shuffle P(>=actual)=0.050 (mean 1121.7 sd 1445.7) | random-bar same side-mix P(>=actual)=0.000 (mean -5003.2 sd 2295.0) | positive coins 15/20 | top-3 removal net 3441.9 folds [0.0, 1796.6, 1645.3] | monthly {'05': -37.0, '06': 1885.0, '07': -2059.0, '08': 3897.0}
  by side: n {-1.0: 2367, 1.0: 2359} net {-1.0: -2661.3, 1.0: 6346.8}
full HL 1h report: tests/h_latpfn_reversal_fade_hl_1h.md

## Summary
```
{
 "partA_cme": {
  "best": {
   "arm": "INV_CONF52",
   "modes": "both"
  },
  "n": 114,
  "net": 971.1098722701045,
  "pf": 1.31771698728296,
  "wr": 0.47368421052631576,
  "sharpe": 1.0911560469860586,
  "folds": [
   0.0,
   -457.31205057646883,
   1428.4219228465734
  ],
  "criteria": {
   "net_pos": true,
   "pf": true,
   "n": true,
   "folds": false
  },
  "shuffle_p": 0.072,
  "top3_net": 1059.0462339579612,
  "top3_folds": [
   0.0,
   -407.4289265536037,
   1466.475160511565
  ]
 },
 "partB_hl": {
  "1h": {
   "taker": {
    "best": {
     "arm": "F_DISAGR",
     "basis": "wrap60",
     "H": 12
    },
    "n": 5184,
    "net": -16708.03008556828,
    "pf": 0.7411480212684787,
    "wr": 0.4826388888888889,
    "sharpe": -6.806235900229134,
    "folds": [
     0.0,
     -8406.705425373493,
     -8301.324660194787
    ],
    "net_bps": -32.229996307037574,
    "criteria": {
     "net_pos": false,
     "pf": false,
     "n": true,
     "folds": false
    }
   },
   "maker": {
    "best": {
     "arm": "F_DISAGR",
     "basis": "wrap60",
     "H": 12
    },
    "n": 4608,
    "net": -17129.524030827113,
    "pf": 0.715381881063735,
    "wr": 0.4765625,
    "sharpe": -7.429172919721031,
    "folds": [
     0.0,
     -8992.045079552703,
     -8137.47895127441
    ],
    "net_bps": -37.17344624745467,
    "criteria": {
     "net_pos": false,
     "pf": false,
     "n": true,
     "folds": false
    }
   }
  }
 }
}
```