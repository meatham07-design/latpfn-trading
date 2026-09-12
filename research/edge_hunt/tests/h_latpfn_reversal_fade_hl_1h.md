# latpfn_reversal_fade - Hyperliquid 1h (cached forecasts, exact timestamps)

Forecasts: 11798  usable signals: 11798  coins (20): AAVE, BTC, DOGE, ENA, ETH, FARTCOIN, HYPE, LINK, LIT, NEAR, PUMP, SOL, SUI, TAO, TRUMP, UNI, WLD, XMR, XRP, ZEC
Period 2026-03-09 -> 2026-08-27; folds: [03-09,05-05), [05-05,07-01), [07-01,08-27)

## Model direction distribution
- wrap60: long 0.50 neutral 0.01 short 0.50
- fc12: long 0.44 neutral 0.01 short 0.55
- wrap60_bc: long 0.55 neutral 0.02 short 0.43
- fc12_bc: long 0.40 neutral 0.03 short 0.57
- confidence: mean 0.683, >=0.6 share 0.63, ==1.0 share 0.31
- regime: {'volatile': 0.93, 'ranging': 0.06, 'trending': 0.0}
- model vs 24-bar trend (wrap60): agree 0.33, disagree 0.66
## Per-fold tilt: model long share vs realised market drift (mean 12-bar fwd return, gross)
- fold 1: n=3933 long share wrap60 0.50 fc12 0.42 | trend>0 share 0.51 | mean fwd 12-bar ret 17.1 bps
- fold 2: n=3932 long share wrap60 0.60 fc12 0.56 | trend>0 share 0.45 | mean fwd 12-bar ret -8.2 bps
- fold 3: n=3933 long share wrap60 0.40 fc12 0.34 | trend>0 share 0.55 | mean fwd 12-bar ret 36.9 bps

## Raw directional hit rate (sign of open[t+1+H]-open[t+1] vs model call; gross, no fees)
- wrap60 H=4: hit 0.499 (n=11714) folds ['0.503(n=3909)', '0.476(n=3912)', '0.517(n=3893)'] regime {'trending': 0.515, 'ranging': 0.496, 'volatile': 0.499} | counter-trend calls hit 0.514 (n=7779)
- wrap60 H=8: hit 0.507 (n=11697) folds ['0.518(n=3909)', '0.498(n=3912)', '0.505(n=3876)'] regime {'trending': 0.576, 'ranging': 0.501, 'volatile': 0.507} | counter-trend calls hit 0.518 (n=7762)
- wrap60 H=12: hit 0.509 (n=11691) folds ['0.522(n=3909)', '0.492(n=3912)', '0.515(n=3870)'] regime {'trending': 0.636, 'ranging': 0.492, 'volatile': 0.51} | counter-trend calls hit 0.518 (n=7756)
- fc12 H=4: hit 0.501 (n=11681) folds ['0.498(n=3892)', '0.484(n=3912)', '0.521(n=3877)'] regime {'ranging': 0.499, 'volatile': 0.502} | counter-trend calls hit 0.516 (n=7822)
- fc12 H=8: hit 0.511 (n=11664) folds ['0.520(n=3892)', '0.506(n=3912)', '0.507(n=3860)'] regime {'ranging': 0.505, 'volatile': 0.511} | counter-trend calls hit 0.520 (n=7805)
- fc12 H=12: hit 0.513 (n=11658) folds ['0.527(n=3892)', '0.502(n=3912)', '0.512(n=3854)'] regime {'ranging': 0.489, 'volatile': 0.515} | counter-trend calls hit 0.520 (n=7799)
- wrap60_bc H=4: hit 0.500 (n=11573) folds ['0.506(n=3848)', '0.473(n=3894)', '0.521(n=3831)'] regime {'trending': 0.576, 'ranging': 0.471, 'volatile': 0.502} | counter-trend calls hit 0.517 (n=7317)
- wrap60_bc H=8: hit 0.504 (n=11556) folds ['0.514(n=3848)', '0.492(n=3894)', '0.506(n=3814)'] regime {'trending': 0.636, 'ranging': 0.505, 'volatile': 0.504} | counter-trend calls hit 0.517 (n=7301)
- wrap60_bc H=12: hit 0.506 (n=11550) folds ['0.516(n=3848)', '0.485(n=3894)', '0.518(n=3808)'] regime {'trending': 0.576, 'ranging': 0.512, 'volatile': 0.505} | counter-trend calls hit 0.516 (n=7295)

## Walk-forward (taker) - select on fold 1, OOS = folds 2+3
selected on fold 1: {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12}
OOS (folds 2+3): n= 5184 net=-16708.03 pf=0.74 wr=0.483 sh= -6.81 bps=-32.23 folds=[0.0, -8406.7, -8301.3]

| arm | basis | H | f1 n | f1 net | f1 pf | full n | full net | full pf | f1 | f2 | f3 | sel |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RAW | wrap60 | 4 | 3908 | -3177.3 | 0.86 | 11714 | -14191.4 | 0.81 | -3177.3 | -5945.6 | -5068.5 |  |
| FADE | wrap60 | 4 | 2572 | -3758.2 | 0.77 | 7779 | -5270.8 | 0.89 | -3758.2 | -1121.7 | -390.8 |  |
| RAW | fc12 | 4 | 3891 | -3216.7 | 0.86 | 11681 | -13470.1 | 0.82 | -3216.7 | -5281.9 | -4971.5 |  |
| FADE | fc12 | 4 | 2576 | -3680.8 | 0.78 | 7822 | -5502.0 | 0.89 | -3680.8 | -1366.3 | -454.9 |  |
| F_AGREE | wrap60 | 4 | 1333 | -2280.1 | 0.72 | 3922 | -5476.6 | 0.77 | -2280.1 | -2382.2 | -814.3 |  |
| F_DISAGR | wrap60 | 4 | 2572 | -890.1 | 0.94 | 7779 | -8759.3 | 0.83 | -890.1 | -3591.5 | -4277.8 |  |
| F_CONF | wrap60 | 4 | 2297 | -1582.3 | 0.89 | 7386 | -8171.8 | 0.84 | -1582.3 | -3512.3 | -3077.1 |  |
| INV | wrap60 | 4 | 3908 | -3877.3 | 0.83 | 11714 | -6922.5 | 0.90 | -3877.3 | -1097.4 | -1947.9 |  |
| INV_CONF | wrap60 | 4 | 2297 | -2572.0 | 0.83 | 7386 | -5148.6 | 0.89 | -2572.0 | -1051.4 | -1525.2 |  |
| INV_HI | wrap60 | 4 | 1084 | -1247.2 | 0.84 | 3694 | -302.6 | 0.99 | -1247.2 | 816.6 | 128.1 |  |
| RAW | wrap60 | 8 | 3908 | -1452.0 | 0.95 | 11697 | -17349.3 | 0.84 | -1452.0 | -7390.1 | -8507.2 |  |
| FADE | wrap60 | 8 | 2572 | -5223.2 | 0.77 | 7762 | -2792.1 | 0.96 | -5223.2 | 165.5 | 2265.6 |  |
| RAW | fc12 | 8 | 3891 | -1533.7 | 0.95 | 11664 | -17018.2 | 0.84 | -1533.7 | -6894.6 | -8589.9 |  |
| FADE | fc12 | 8 | 2576 | -5054.9 | 0.78 | 7805 | -2723.7 | 0.96 | -5054.9 | 100.6 | 2230.6 |  |
| F_AGREE | wrap60 | 8 | 1333 | -1971.0 | 0.82 | 3922 | -6069.3 | 0.82 | -1971.0 | -2490.4 | -1608.0 |  |
| F_DISAGR | wrap60 | 8 | 2572 | 537.3 | 1.03 | 7762 | -11274.0 | 0.84 | 537.3 | -4891.5 | -6919.8 |  |
| F_CONF | wrap60 | 8 | 2297 | -292.5 | 0.98 | 7373 | -12575.6 | 0.82 | -292.5 | -6590.0 | -5693.0 |  |
| INV | wrap60 | 8 | 3908 | -5647.6 | 0.83 | 11697 | -3815.8 | 0.96 | -5647.6 | 331.3 | 1500.5 |  |
| INV_CONF | wrap60 | 8 | 2297 | -3898.3 | 0.81 | 7373 | -787.2 | 0.99 | -3898.3 | 2013.4 | 1097.7 |  |
| INV_HI | wrap60 | 8 | 1084 | -1517.0 | 0.85 | 3683 | 3804.2 | 1.11 | -1517.0 | 2618.4 | 2702.7 |  |
| RAW | wrap60 | 12 | 3908 | -960.0 | 0.97 | 11691 | -20576.7 | 0.84 | -960.0 | -10455.0 | -9161.8 |  |
| FADE | wrap60 | 12 | 2572 | -7086.4 | 0.76 | 7756 | 189.0 | 1.00 | -7086.4 | 3647.6 | 3627.9 |  |
| RAW | fc12 | 12 | 3891 | -1109.6 | 0.97 | 11658 | -21173.7 | 0.84 | -1109.6 | -9410.2 | -10653.9 |  |
| FADE | fc12 | 12 | 2576 | -6841.2 | 0.77 | 7799 | 733.3 | 1.01 | -6841.2 | 3269.5 | 4305.1 |  |
| F_AGREE | wrap60 | 12 | 1333 | -3274.5 | 0.76 | 3922 | -6144.6 | 0.85 | -3274.5 | -1982.1 | -888.0 |  |
| F_DISAGR | wrap60 | 12 | 2572 | 2344.3 | 1.10 | 7756 | -14363.7 | 0.84 | 2344.3 | -8406.7 | -8301.3 | * |
| F_CONF | wrap60 | 12 | 2297 | 621.4 | 1.03 | 7369 | -14372.3 | 0.83 | 621.4 | -8567.0 | -6426.7 |  |
| INV | wrap60 | 12 | 3908 | -6216.2 | 0.85 | 11691 | -739.7 | 0.99 | -6216.2 | 3350.3 | 2126.2 |  |
| INV_CONF | wrap60 | 12 | 2297 | -4868.0 | 0.81 | 7369 | 899.1 | 1.01 | -4868.0 | 3960.4 | 1806.7 |  |
| INV_HI | wrap60 | 12 | 1084 | -1983.4 | 0.84 | 3679 | 6611.7 | 1.16 | -1983.4 | 4594.8 | 4000.2 |  |

### Sanity (taker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
neighbours (OOS period, no reselection):
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
- basis=wrap60: n= 5184 net=-16708.03 pf=0.74 wr=0.483 sh= -6.81 bps=-32.23 folds=[0.0, -8406.7, -8301.3]
- basis=fc12: n= 5223 net=-17080.78 pf=0.74 wr=0.486 sh= -7.03 bps=-32.70 folds=[0.0, -8057.3, -9023.5]
model-free baselines (same bars, OOS period):
- TREND H=4: OOS n= 7850 net= -4606.09 pf=0.91 wr=0.447 sh= -2.72 bps= -5.87 folds=[0.0, -3413.2, -1192.9] | fold1 net -6022.3
- TREND H=8: OOS n= 7833 net= -1489.19 pf=0.98 wr=0.459 sh= -0.63 bps= -1.90 folds=[0.0, -2129.3, 640.1] | fold1 net -7167.0
- TREND H=12: OOS n= 7827 net=  4587.22 pf=1.06 wr=0.475 sh=  1.57 bps=  5.86 folds=[0.0, 1847.2, 2740.0] | fold1 net -10346.2
- TREND_AGREE H=4: OOS n= 2589 net= -3196.49 pf=0.80 wr=0.440 sh= -3.66 bps=-12.35 folds=[0.0, -2382.2, -814.3] | fold1 net -2280.1
- TREND_AGREE H=8: OOS n= 2589 net= -4098.33 pf=0.83 wr=0.452 sh= -3.22 bps=-15.83 folds=[0.0, -2490.4, -1608.0] | fold1 net -1971.0
- TREND_AGREE H=12: OOS n= 2589 net= -2870.08 pf=0.89 wr=0.475 sh= -1.83 bps=-11.09 folds=[0.0, -1982.1, -888.0] | fold1 net -3274.5
shuffle (model directions permuted within coin, 200 reps, OOS period): actual -16708.0; shuffled mean -10031.4 sd 1443.2 p5 -12428.4 p95 -7742.9; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -5374.5 sd 2388.2; P(random >= actual) = 1.000
BTC-hedged (equal-notional opposite BTC leg, taker fees on hedge): n= 5184 net=-17433.69 pf=0.67 wr=0.414 sh= -8.12 bps=-33.63 folds=[0.0, -9535.2, -7898.4]
top-3 removal (selected): net -16708.0 -> -17355.5 pf 0.73 folds [0.0, -8861.3, -8494.2]
top-3 removal (INV): net 5476.5 -> 4217.0 pf 1.05 folds [0.0, 3003.4, 1213.6]
per-coin OOS:
            count      sum  vol24_usd_M  illiquid(<5M)
instrument                                            
WLD           239   192.70          9.0          False
XMR           247    45.30         16.9          False
UNI           232  -223.99         14.3          False
NEAR          213  -493.49         25.9          False
DOGE          216  -498.22         16.9          False
LIT           217  -675.90         46.9          False
XRP           237  -715.75        117.8          False
PUMP          228  -720.83        174.8          False
ENA           219  -762.55        120.2          False
LINK          222  -790.96         20.8          False
TAO           228  -806.83         50.8          False
TRUMP         220  -844.23         41.4          False
SUI           222  -861.50         18.1          False
AAVE          218 -1060.24         14.7          False
FARTCOIN      227 -1132.84         37.1          False
SOL           235 -1148.07       1243.4          False
ZEC           205 -1260.21        289.2          False
BTC           469 -1416.33       3699.5          False
ETH           434 -1761.42       1679.4          False
HYPE          456 -1772.69        969.9          False
positive coins: 2/20; illiquid names in universe: 0
per-regime OOS: {'count': {'ranging': 451, 'trending': 24, 'volatile': 4709}, 'sum': {'ranging': -1345.1, 'trending': -27.8, 'volatile': -15335.2}}
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

| arm | basis | H | f1 n | f1 net | f1 pf | full n | full net | full pf | f1 | f2 | f3 | sel |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RAW | wrap60 | 4 | 3516 | -4822.8 | 0.78 | 10515 | -17684.1 | 0.75 | -4822.8 | -6554.1 | -6307.2 |  |
| FADE | wrap60 | 4 | 2308 | -4355.5 | 0.72 | 7056 | -7765.6 | 0.84 | -4355.5 | -1933.3 | -1476.8 |  |
| RAW | fc12 | 4 | 3499 | -4975.2 | 0.77 | 10464 | -17140.2 | 0.76 | -4975.2 | -6050.3 | -6114.7 |  |
| FADE | fc12 | 4 | 2311 | -4253.0 | 0.73 | 7108 | -7896.8 | 0.83 | -4253.0 | -2112.0 | -1531.8 |  |
| F_AGREE | wrap60 | 4 | 1190 | -2811.9 | 0.63 | 3549 | -6641.1 | 0.71 | -2811.9 | -2468.9 | -1360.2 |  |
| F_DISAGR | wrap60 | 4 | 2323 | -2004.5 | 0.86 | 6954 | -11089.7 | 0.77 | -2004.5 | -4114.8 | -4970.3 |  |
| F_CONF | wrap60 | 4 | 2082 | -2569.1 | 0.81 | 6630 | -10357.5 | 0.78 | -2569.1 | -3744.6 | -4043.8 |  |
| INV | wrap60 | 4 | 3505 | -5065.0 | 0.77 | 10571 | -10546.7 | 0.84 | -5065.0 | -2327.1 | -3154.5 |  |
| INV_CONF | wrap60 | 4 | 2063 | -3287.8 | 0.77 | 6717 | -7394.5 | 0.84 | -3287.8 | -1828.4 | -2278.3 |  |
| INV_HI | wrap60 | 4 | 996 | -1414.2 | 0.80 | 3424 | -1574.2 | 0.94 | -1414.2 | 272.8 | -432.8 |  |
| RAW | wrap60 | 8 | 3516 | -3541.4 | 0.88 | 10498 | -20463.7 | 0.80 | -3541.4 | -7930.1 | -8992.2 |  |
| FADE | wrap60 | 8 | 2308 | -5277.7 | 0.75 | 7040 | -5774.2 | 0.91 | -5277.7 | -1331.9 | 835.4 |  |
| RAW | fc12 | 8 | 3499 | -3734.0 | 0.87 | 10447 | -20321.5 | 0.80 | -3734.0 | -7615.3 | -8972.2 |  |
| FADE | fc12 | 8 | 2311 | -5177.5 | 0.76 | 7092 | -5738.9 | 0.91 | -5177.5 | -1327.0 | 765.6 |  |
| F_AGREE | wrap60 | 8 | 1190 | -2769.6 | 0.72 | 3549 | -7116.4 | 0.78 | -2769.6 | -2488.0 | -1858.8 |  |
| F_DISAGR | wrap60 | 8 | 2323 | -754.3 | 0.96 | 6937 | -13345.3 | 0.80 | -754.3 | -5435.4 | -7155.6 |  |
| F_CONF | wrap60 | 8 | 2082 | -1601.7 | 0.91 | 6617 | -14498.3 | 0.78 | -1601.7 | -6843.7 | -6052.9 |  |
| INV | wrap60 | 8 | 3505 | -6323.3 | 0.79 | 10555 | -8510.5 | 0.91 | -6323.3 | -2121.2 | -66.0 |  |
| INV_CONF | wrap60 | 8 | 2063 | -4135.4 | 0.78 | 6704 | -3998.1 | 0.93 | -4135.4 | 26.0 | 111.3 |  |
| INV_HI | wrap60 | 8 | 996 | -1511.8 | 0.84 | 3413 | 1756.5 | 1.06 | -1511.8 | 1308.4 | 1959.9 |  |
| RAW | wrap60 | 12 | 3516 | -3002.6 | 0.92 | 10492 | -23386.7 | 0.81 | -3002.6 | -11082.2 | -9302.0 |  |
| FADE | wrap60 | 12 | 2308 | -6953.4 | 0.74 | 7034 | -3267.9 | 0.96 | -6953.4 | 1846.4 | 1839.1 |  |
| RAW | fc12 | 12 | 3499 | -3239.5 | 0.91 | 10441 | -24138.4 | 0.80 | -3239.5 | -10383.4 | -10515.4 |  |
| FADE | fc12 | 12 | 2311 | -6751.2 | 0.75 | 7086 | -2734.1 | 0.96 | -6751.2 | 1657.7 | 2359.4 |  |
| F_AGREE | wrap60 | 12 | 1190 | -3905.1 | 0.69 | 3549 | -7125.5 | 0.81 | -3905.1 | -2025.6 | -1194.8 |  |
| F_DISAGR | wrap60 | 12 | 2323 | 931.6 | 1.04 | 6931 | -16197.9 | 0.81 | 931.6 | -8992.0 | -8137.5 | * |
| F_CONF | wrap60 | 12 | 2082 | -441.1 | 0.98 | 6613 | -15868.1 | 0.80 | -441.1 | -8942.8 | -6484.3 |  |
| INV | wrap60 | 12 | 3505 | -6710.3 | 0.82 | 10549 | -5571.3 | 0.95 | -6710.3 | 747.5 | 391.5 |  |
| INV_CONF | wrap60 | 12 | 2063 | -5066.4 | 0.78 | 6700 | -2665.7 | 0.96 | -5066.4 | 1806.0 | 594.7 |  |
| INV_HI | wrap60 | 12 | 996 | -1939.4 | 0.84 | 3409 | 4363.2 | 1.11 | -1939.4 | 3303.6 | 2999.0 |  |

### Sanity (maker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
neighbours (OOS period, no reselection):
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
- basis=wrap60: n= 4608 net=-17129.52 pf=0.72 wr=0.477 sh= -7.43 bps=-37.17 folds=[0.0, -8992.0, -8137.5]
- basis=fc12: n= 4634 net=-17568.32 pf=0.71 wr=0.479 sh= -7.71 bps=-37.91 folds=[0.0, -8821.9, -8746.4]
model-free baselines (same bars, OOS period):
- TREND H=4: OOS n= 7157 net= -7140.78 pf=0.85 wr=0.436 sh= -4.38 bps= -9.98 folds=[0.0, -4306.1, -2834.7] | fold1 net -7132.1
- TREND H=8: OOS n= 7141 net= -4659.84 pf=0.93 wr=0.454 sh= -2.06 bps= -6.53 folds=[0.0, -3623.2, -1036.6] | fold1 net -8016.9
- TREND H=12: OOS n= 7135 net=   630.72 pf=1.01 wr=0.470 sh=  0.22 bps=  0.88 folds=[0.0, 4.6, 626.1] | fold1 net -10835.4
- TREND_AGREE H=4: OOS n= 2359 net= -3829.11 pf=0.75 wr=0.428 sh= -4.54 bps=-16.23 folds=[0.0, -2468.9, -1360.2] | fold1 net -2811.9
- TREND_AGREE H=8: OOS n= 2359 net= -4346.83 pf=0.81 wr=0.449 sh= -3.52 bps=-18.43 folds=[0.0, -2488.0, -1858.8] | fold1 net -2769.6
- TREND_AGREE H=12: OOS n= 2359 net= -3220.38 pf=0.87 wr=0.476 sh= -2.10 bps=-13.65 folds=[0.0, -2025.6, -1194.8] | fold1 net -3905.1
shuffle (model directions permuted within coin, 200 reps, OOS period): actual -17129.5; shuffled mean -10652.4 sd 1383.0 p5 -12858.8 p95 -8392.7; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -6793.7 sd 2181.0; P(random >= actual) = 1.000
BTC-hedged (equal-notional opposite BTC leg, taker fees on hedge): n= 4608 net=-16457.81 pf=0.67 wr=0.416 sh= -8.22 bps=-35.72 folds=[0.0, -9414.0, -7043.9]
top-3 removal (selected): net -17129.5 -> -17421.0 pf 0.71 folds [0.0, -9266.4, -8154.6]
top-3 removal (INV): net 1139.0 -> 962.1 pf 1.01 folds [0.0, 697.7, 264.4]
per-coin OOS:
            count      sum  vol24_usd_M  illiquid(<5M)
instrument                                            
WLD           224   141.22          9.0          False
XMR           223   -44.76         16.9          False
TRUMP         185  -290.21         41.4          False
UNI           203  -353.40         14.3          False
DOGE          188  -576.24         16.9          False
NEAR          189  -588.19         25.9          False
LIT           203  -649.01         46.9          False
XRP           198  -749.28        117.8          False
LINK          201  -811.34         20.8          False
PUMP          217  -816.28        174.8          False
TAO           213  -836.31         50.8          False
SUI           201  -971.77         18.1          False
SOL           208 -1027.37       1243.4          False
ENA           194 -1057.32        120.2          False
AAVE          192 -1080.53         14.7          False
FARTCOIN      212 -1243.28         37.1          False
BTC           374 -1330.36       3699.5          False
ZEC           191 -1360.98        289.2          False
ETH           367 -1448.16       1679.4          False
HYPE          425 -2035.95        969.9          False
positive coins: 1/20; illiquid names in universe: 0
per-regime OOS: {'count': {'ranging': 364, 'trending': 22, 'volatile': 4222}, 'sum': {'ranging': -1114.0, 'trending': -11.7, 'volatile': -16003.9}}
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

## Summary
```
{
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
```