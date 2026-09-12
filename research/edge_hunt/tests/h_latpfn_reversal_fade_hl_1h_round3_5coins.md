# latpfn_reversal_fade - 1h

Forecasts: 3747  usable signals: 3747  coins (5): BTC, ETH, HYPE, LIT, PUMP
Period 2026-03-09 -> 2026-08-27; folds: [03-09,05-05), [05-05,07-01), [07-01,08-27)

## Model direction distribution
- wrap60: long 0.46 neutral 0.01 short 0.53
- fc12: long 0.40 neutral 0.01 short 0.59
- wrap60_bc: long 0.52 neutral 0.02 short 0.46
- fc12_bc: long 0.38 neutral 0.03 short 0.59
- confidence: mean 0.689, >=0.6 share 0.63, ==1.0 share 0.33
- regime: {'volatile': 0.9, 'ranging': 0.09, 'trending': 0.01}
- model vs 24-bar trend (wrap60): agree 0.33, disagree 0.66
## Per-fold tilt: model long share vs realised market drift (mean 12-bar fwd return, gross)
- fold 1: n=1368 long share wrap60 0.42 fc12 0.36 | trend>0 share 0.54 | mean fwd 12-bar ret 13.0 bps
- fold 2: n=1367 long share wrap60 0.58 fc12 0.52 | trend>0 share 0.47 | mean fwd 12-bar ret 5.3 bps
- fold 3: n=1012 long share wrap60 0.35 fc12 0.30 | trend>0 share 0.57 | mean fwd 12-bar ret 31.4 bps

## Raw directional hit rate (sign of open[t+1+H]-open[t+1] vs model call; gross, no fees)
- wrap60 H=4: hit 0.499 (n=3720) folds ['0.509(n=1357)', '0.489(n=1360)', '0.498(n=1003)'] regime {'ranging': 0.527, 'volatile': 0.496} | counter-trend calls hit 0.507 (n=2474)
- wrap60 H=8: hit 0.504 (n=3718) folds ['0.514(n=1357)', '0.503(n=1360)', '0.494(n=1001)'] regime {'ranging': 0.497, 'volatile': 0.505} | counter-trend calls hit 0.508 (n=2472)
- wrap60 H=12: hit 0.507 (n=3717) folds ['0.522(n=1357)', '0.497(n=1360)', '0.499(n=1000)'] regime {'ranging': 0.494, 'volatile': 0.508} | counter-trend calls hit 0.509 (n=2471)
- fc12 H=4: hit 0.497 (n=3712) folds ['0.497(n=1357)', '0.498(n=1358)', '0.495(n=997)'] regime {'ranging': 0.515, 'volatile': 0.496} | counter-trend calls hit 0.505 (n=2478)
- fc12 H=8: hit 0.504 (n=3710) folds ['0.511(n=1357)', '0.507(n=1358)', '0.489(n=995)'] regime {'ranging': 0.491, 'volatile': 0.506} | counter-trend calls hit 0.506 (n=2476)
- fc12 H=12: hit 0.504 (n=3709) folds ['0.519(n=1357)', '0.501(n=1358)', '0.488(n=994)'] regime {'ranging': 0.479, 'volatile': 0.507} | counter-trend calls hit 0.507 (n=2475)
- wrap60_bc H=4: hit 0.504 (n=3674) folds ['0.522(n=1336)', '0.489(n=1356)', '0.501(n=982)'] regime {'ranging': 0.492, 'volatile': 0.505} | counter-trend calls hit 0.512 (n=2309)
- wrap60_bc H=8: hit 0.507 (n=3672) folds ['0.520(n=1336)', '0.494(n=1356)', '0.505(n=980)'] regime {'ranging': 0.48, 'volatile': 0.508} | counter-trend calls hit 0.508 (n=2307)
- wrap60_bc H=12: hit 0.505 (n=3671) folds ['0.523(n=1336)', '0.489(n=1356)', '0.503(n=979)'] regime {'ranging': 0.495, 'volatile': 0.506} | counter-trend calls hit 0.507 (n=2306)

## Walk-forward (taker) - select on fold 1, OOS = folds 2+3
selected on fold 1: {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12}
OOS (folds 2+3): n= 1573 net= -4905.39 pf=0.73 wr=0.465 sh= -4.11 bps=-31.18 folds=[0.0, -3031.1, -1874.3]

| arm | basis | H | f1 n | f1 net | f1 pf | full n | full net | full pf | f1 | f2 | f3 | sel |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RAW | wrap60 | 4 | 1356 | -1250.8 | 0.83 | 3720 | -4998.6 | 0.78 | -1250.8 | -2202.7 | -1545.1 |  |
| FADE | wrap60 | 4 | 898 | -1272.2 | 0.75 | 2474 | -1460.5 | 0.90 | -1272.2 | -128.7 | -59.5 |  |
| RAW | fc12 | 4 | 1356 | -1153.1 | 0.84 | 3712 | -4964.3 | 0.78 | -1153.1 | -2216.4 | -1594.8 |  |
| FADE | fc12 | 4 | 887 | -1295.7 | 0.75 | 2478 | -1424.3 | 0.90 | -1295.7 | -114.0 | -14.7 |  |
| F_AGREE | wrap60 | 4 | 457 | -907.4 | 0.66 | 1241 | -2038.9 | 0.73 | -907.4 | -716.7 | -414.8 |  |
| F_DISAGR | wrap60 | 4 | 898 | -344.3 | 0.93 | 2474 | -2993.8 | 0.80 | -344.3 | -1509.4 | -1140.1 |  |
| F_CONF | wrap60 | 4 | 823 | -691.0 | 0.85 | 2372 | -2907.3 | 0.80 | -691.0 | -1337.5 | -878.8 |  |
| RAW | wrap60 | 8 | 1356 | -447.8 | 0.95 | 3718 | -4541.7 | 0.85 | -447.8 | -1896.6 | -2197.2 |  |
| FADE | wrap60 | 8 | 898 | -1965.5 | 0.74 | 2472 | -1488.8 | 0.93 | -1965.5 | 13.9 | 462.8 |  |
| RAW | fc12 | 8 | 1356 | -870.1 | 0.91 | 3710 | -5360.7 | 0.83 | -870.1 | -1984.5 | -2506.1 |  |
| FADE | fc12 | 8 | 887 | -1723.3 | 0.77 | 2476 | -1019.5 | 0.95 | -1723.3 | 108.9 | 595.0 |  |
| F_AGREE | wrap60 | 8 | 457 | -800.2 | 0.77 | 1241 | -1582.3 | 0.84 | -800.2 | -245.0 | -537.2 |  |
| F_DISAGR | wrap60 | 8 | 898 | 348.5 | 1.06 | 2472 | -2963.3 | 0.86 | 348.5 | -1651.8 | -1660.0 |  |
| F_CONF | wrap60 | 8 | 823 | -466.6 | 0.92 | 2370 | -3586.0 | 0.83 | -466.6 | -1751.6 | -1367.8 |  |
| RAW | wrap60 | 12 | 1356 | 37.6 | 1.00 | 3717 | -5249.8 | 0.86 | 37.6 | -3087.8 | -2199.7 |  |
| FADE | wrap60 | 12 | 898 | -2895.1 | 0.69 | 2471 | -824.5 | 0.97 | -2895.1 | 1392.9 | 677.7 |  |
| RAW | fc12 | 12 | 1356 | -741.6 | 0.94 | 3709 | -6905.0 | 0.82 | -741.6 | -3430.3 | -2733.1 |  |
| FADE | fc12 | 12 | 887 | -2452.3 | 0.73 | 2475 | 81.2 | 1.00 | -2452.3 | 1614.9 | 918.6 |  |
| F_AGREE | wrap60 | 12 | 457 | -1227.6 | 0.73 | 1241 | -1610.5 | 0.87 | -1227.6 | -40.5 | -342.4 |  |
| F_DISAGR | wrap60 | 12 | 898 | 1277.9 | 1.18 | 2471 | -3627.5 | 0.86 | 1277.9 | -3031.1 | -1874.3 | * |
| F_CONF | wrap60 | 12 | 823 | -298.0 | 0.96 | 2369 | -4329.4 | 0.83 | -298.0 | -2437.3 | -1594.2 |  |

### Sanity (taker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
neighbours (OOS period, no reselection):
- H=4: n= 1576 net= -2649.54 pf=0.74 wr=0.448 sh= -3.82 bps=-16.81 folds=[0.0, -1509.4, -1140.1]
- H=8: n= 1574 net= -3311.78 pf=0.77 wr=0.466 sh= -3.30 bps=-21.04 folds=[0.0, -1651.8, -1660.0]
- H=12: n= 1573 net= -4905.39 pf=0.73 wr=0.465 sh= -4.11 bps=-31.18 folds=[0.0, -3031.1, -1874.3]
- arm=RAW: n= 2361 net= -5287.42 pf=0.80 wr=0.471 sh= -3.66 bps=-22.39 folds=[0.0, -3087.8, -2199.7]
- arm=FADE: n= 1573 net=  2070.66 pf=1.14 wr=0.485 sh=  1.74 bps= 13.16 folds=[0.0, 1392.9, 677.7]
- arm=F_AGREE: n=  784 net=  -382.90 pf=0.95 wr=0.485 sh= -0.47 bps= -4.88 folds=[0.0, -40.5, -342.4]
- arm=F_DISAGR: n= 1573 net= -4905.39 pf=0.73 wr=0.465 sh= -4.11 bps=-31.18 folds=[0.0, -3031.1, -1874.3]
- arm=F_CONF: n= 1546 net= -4031.47 pf=0.77 wr=0.481 sh= -3.38 bps=-26.08 folds=[0.0, -2437.3, -1594.2]
- basis=wrap60: n= 1573 net= -4905.39 pf=0.73 wr=0.465 sh= -4.11 bps=-31.18 folds=[0.0, -3031.1, -1874.3]
- basis=fc12: n= 1588 net= -5395.44 pf=0.71 wr=0.462 sh= -4.47 bps=-33.98 folds=[0.0, -3276.7, -2118.7]
shuffle (model directions permuted within coin, 50 reps, OOS period): actual -4905.4; shuffled mean -3570.3 sd 658.0 p5 -4678.6 p95 -2670.1; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -1914.4 sd 1140.6; P(random >= actual) = 1.000
BTC-hedged (equal-notional opposite BTC leg, taker fees on hedge): n= 1573 net= -5669.39 pf=0.61 wr=0.302 sh= -5.58 bps=-36.04 folds=[0.0, -3581.8, -2087.6]
per-coin OOS:
            count      sum  vol24_usd_M  illiquid(<5M)
instrument                                            
LIT           139  -478.47         46.9          False
PUMP          228  -720.83        174.8          False
ETH           358 -1070.57       1679.4          False
HYPE          379 -1219.19        969.9          False
BTC           469 -1416.33       3699.5          False
positive coins: 0/5; illiquid names in universe: 0
per-regime OOS: {'count': {'ranging': 225, 'trending': 16, 'volatile': 1332}, 'sum': {'ranging': -392.8, 'trending': -53.3, 'volatile': -4459.3}}

## Walk-forward (maker) - select on fold 1, OOS = folds 2+3
selected on fold 1: {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12}
OOS (folds 2+3): n= 1376 net= -4749.62 pf=0.72 wr=0.457 sh= -4.08 bps=-34.52 folds=[0.0, -3088.4, -1661.2]

| arm | basis | H | f1 n | f1 net | f1 pf | full n | full net | full pf | f1 | f2 | f3 | sel |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RAW | wrap60 | 4 | 1216 | -1727.9 | 0.75 | 3299 | -5594.4 | 0.74 | -1727.9 | -2290.7 | -1575.8 |  |
| FADE | wrap60 | 4 | 803 | -1398.6 | 0.71 | 2228 | -1803.9 | 0.86 | -1398.6 | -252.8 | -152.5 |  |
| RAW | fc12 | 4 | 1210 | -1656.1 | 0.76 | 3283 | -5495.2 | 0.74 | -1656.1 | -2294.5 | -1544.5 |  |
| FADE | fc12 | 4 | 794 | -1429.3 | 0.70 | 2235 | -1752.0 | 0.87 | -1429.3 | -223.5 | -99.2 |  |
| F_AGREE | wrap60 | 4 | 402 | -1073.9 | 0.57 | 1102 | -2208.3 | 0.69 | -1073.9 | -645.8 | -488.6 |  |
| F_DISAGR | wrap60 | 4 | 813 | -655.1 | 0.85 | 2192 | -3420.0 | 0.75 | -655.1 | -1669.0 | -1095.9 |  |
| F_CONF | wrap60 | 4 | 747 | -909.5 | 0.78 | 2109 | -3080.5 | 0.77 | -909.5 | -1345.7 | -825.4 |  |
| RAW | wrap60 | 8 | 1216 | -1054.4 | 0.89 | 3297 | -5155.9 | 0.82 | -1054.4 | -1900.6 | -2200.9 |  |
| FADE | wrap60 | 8 | 803 | -1970.9 | 0.72 | 2226 | -1889.9 | 0.90 | -1970.9 | -174.6 | 255.6 |  |
| RAW | fc12 | 8 | 1210 | -1491.0 | 0.84 | 3281 | -5906.4 | 0.80 | -1491.0 | -1985.6 | -2429.9 |  |
| FADE | fc12 | 8 | 794 | -1799.5 | 0.74 | 2233 | -1493.4 | 0.92 | -1799.5 | -84.3 | 390.3 |  |
| F_AGREE | wrap60 | 8 | 402 | -961.5 | 0.71 | 1102 | -1723.2 | 0.82 | -961.5 | -191.7 | -570.0 |  |
| F_DISAGR | wrap60 | 8 | 813 | -97.0 | 0.98 | 2190 | -3436.4 | 0.83 | -97.0 | -1709.7 | -1629.7 |  |
| F_CONF | wrap60 | 8 | 747 | -774.3 | 0.87 | 2107 | -3750.0 | 0.81 | -774.3 | -1658.1 | -1317.6 |  |
| RAW | wrap60 | 12 | 1216 | -629.2 | 0.94 | 3296 | -5862.0 | 0.83 | -629.2 | -3142.1 | -2090.7 |  |
| FADE | wrap60 | 12 | 803 | -2714.7 | 0.68 | 2225 | -1053.5 | 0.95 | -2714.7 | 1316.7 | 344.4 |  |
| RAW | fc12 | 12 | 1210 | -1362.4 | 0.88 | 3280 | -7360.9 | 0.80 | -1362.4 | -3509.7 | -2488.8 |  |
| FADE | fc12 | 12 | 794 | -2349.5 | 0.72 | 2232 | -239.5 | 0.99 | -2349.5 | 1551.1 | 558.9 |  |
| F_AGREE | wrap60 | 12 | 402 | -1321.7 | 0.68 | 1102 | -1805.2 | 0.84 | -1321.7 | -38.0 | -445.5 |  |
| F_DISAGR | wrap60 | 12 | 813 | 704.8 | 1.10 | 2189 | -4044.8 | 0.83 | 704.8 | -3088.4 | -1661.2 | * |
| F_CONF | wrap60 | 12 | 747 | -590.0 | 0.91 | 2106 | -4338.9 | 0.81 | -590.0 | -2338.1 | -1410.9 |  |

### Sanity (maker, {'arm': 'F_DISAGR', 'basis': 'wrap60', 'H': 12})
neighbours (OOS period, no reselection):
- H=4: n= 1379 net= -2764.87 pf=0.71 wr=0.439 sh= -4.13 bps=-20.05 folds=[0.0, -1669.0, -1095.9]
- H=8: n= 1377 net= -3339.33 pf=0.76 wr=0.461 sh= -3.43 bps=-24.25 folds=[0.0, -1709.7, -1629.7]
- H=12: n= 1376 net= -4749.62 pf=0.72 wr=0.457 sh= -4.08 bps=-34.52 folds=[0.0, -3088.4, -1661.2]
- arm=RAW: n= 2080 net= -5232.83 pf=0.79 wr=0.467 sh= -3.71 bps=-25.16 folds=[0.0, -3142.1, -2090.7]
- arm=FADE: n= 1422 net=  1661.13 pf=1.12 wr=0.481 sh=  1.45 bps= 11.68 folds=[0.0, 1316.7, 344.4]
- arm=F_AGREE: n=  700 net=  -483.51 pf=0.93 wr=0.486 sh= -0.61 bps= -6.91 folds=[0.0, -38.0, -445.5]
- arm=F_DISAGR: n= 1376 net= -4749.62 pf=0.72 wr=0.457 sh= -4.08 bps=-34.52 folds=[0.0, -3088.4, -1661.2]
- arm=F_CONF: n= 1359 net= -3748.94 pf=0.77 wr=0.481 sh= -3.21 bps=-27.59 folds=[0.0, -2338.1, -1410.9]
- basis=wrap60: n= 1376 net= -4749.62 pf=0.72 wr=0.457 sh= -4.08 bps=-34.52 folds=[0.0, -3088.4, -1661.2]
- basis=fc12: n= 1388 net= -5170.68 pf=0.70 wr=0.455 sh= -4.39 bps=-37.25 folds=[0.0, -3347.0, -1823.7]
shuffle (model directions permuted within coin, 50 reps, OOS period): actual -4749.6; shuffled mean -3436.5 sd 635.8 p5 -4406.7 p95 -2527.0; P(shuffle >= actual) = 1.000
random-bar same-coin baseline (same n and side mix per coin): mean -1791.2 sd 940.4; P(random >= actual) = 1.000
BTC-hedged (equal-notional opposite BTC leg, taker fees on hedge): n= 1376 net= -5100.27 pf=0.62 wr=0.311 sh= -5.11 bps=-37.07 folds=[0.0, -3382.0, -1718.2]
per-coin OOS:
            count      sum  vol24_usd_M  illiquid(<5M)
instrument                                            
LIT           130  -331.65         46.9          False
ETH           302  -775.56       1679.4          False
PUMP          217  -816.28        174.8          False
BTC           374 -1330.36       3699.5          False
HYPE          353 -1495.77        969.9          False
positive coins: 0/5; illiquid names in universe: 0
per-regime OOS: {'count': {'ranging': 170, 'trending': 14, 'volatile': 1192}, 'sum': {'ranging': -261.2, 'trending': -39.0, 'volatile': -4449.5}}

## Summary
```
{
 "taker": {
  "best": {
   "arm": "F_DISAGR",
   "basis": "wrap60",
   "H": 12
  },
  "n": 1573,
  "net": -4905.391499492485,
  "pf": 0.7331979384710119,
  "wr": 0.46471710108073744,
  "sharpe": -4.109998469171411,
  "folds": [
   0.0,
   -3031.076052137987,
   -1874.3154473544992
  ],
  "net_bps": -31.184942781261825,
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
  "n": 1376,
  "net": -4749.62315054616,
  "pf": 0.722307443018326,
  "wr": 0.4571220930232558,
  "sharpe": -4.080859448590391,
  "folds": [
   0.0,
   -3088.418911175193,
   -1661.2042393709662
  ],
  "net_bps": -34.51761010571337,
  "criteria": {
   "net_pos": false,
   "pf": false,
   "n": true,
   "folds": false
  }
 }
}
```