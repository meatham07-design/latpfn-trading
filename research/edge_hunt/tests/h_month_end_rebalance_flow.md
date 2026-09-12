# month_end_rebalance_flow — results

Round 3. Month-end rebalancing flow in CME index futures, daily settlement fills, 1 contract, cme_fee round trip.

## Data / roll verification

Session calendar = SPY sessions 2016-08-29 .. 2026-08-26 (2512 days). Roll days flagged by calendar (3rd Friday of Mar/Jun/Sep/Dec + next session): 82.

- ES: first 2016-08-29, ffilled 2 sessions; |ES-SPY| residual >50bps on 45/82 flagged roll days and 27 other days (17:00 vs 16:00 timing + real basis moves); roll adjustment changes 81 daily returns.
- NQ: first 2016-08-29, ffilled 2 sessions; |NQ-QQQ| residual >50bps on 49/82 flagged roll days and 59 other days (17:00 vs 16:00 timing + real basis moves); roll adjustment changes 81 daily returns.
- MES: first 2019-05-03, ffilled 0 sessions; |MES-SPY| residual >50bps on 37/58 flagged roll days and 15 other days (17:00 vs 16:00 timing + real basis moves); roll adjustment changes 58 daily returns.
- MNQ: first 2019-05-03, ffilled 0 sessions; |MNQ-QQQ| residual >50bps on 38/58 flagged roll days and 30 other days (17:00 vs 16:00 timing + real basis moves); roll adjustment changes 58 daily returns.
- GC: first 2016-08-29, ffilled 3 sessions; no roll adjustment applied.
- SPY: first 2016-08-29, ffilled 0 sessions; no roll adjustment applied.
- QQQ: first 2016-08-29, ffilled 0 sessions; no roll adjustment applied.
- GLD: first 2016-08-29, ffilled 0 sessions; no roll adjustment applied.
- Windows of arms A/B (T-3..T+4) touching a roll day on ES/NQ: **0** (expected 0: quarterly rolls are mid-month). Arm C (T-8..T-2) windows touching a roll day: {('ES', 'C_k2'): 37, ('ES', 'C_k3'): 37, ('ES', 'C_k4'): 37, ('NQ', 'C_k2'): 37, ('NQ', 'C_k3'): 37, ('NQ', 'C_k4'): 37}.

Folds (main): [('2016-08-29', '2019-12-28'), ('2019-12-28', '2023-04-27'), ('2023-04-27', '2026-08-26')]  
Folds (micros): [('2019-05-03', '2021-10-09'), ('2021-10-09', '2024-03-18'), ('2024-03-18', '2026-08-26')]


## Headline: pooled ES+NQ, 15-cell grid, select on fold 1


### headline_ESNQ_grid15 — ES+NQ

Selected on fold 1: **A_k4**  
OOS (folds 2+3): n=160 net=$96,684 pf=1.23 wr=0.61 sharpe=0.90 bps=21.1 folds=[0, 101101, -4416] fold_n=[0, 80, 80]

Gates: pro-rata drift baseline = $125,027 (excess = $-28,343); random same-length windows: mean $141,862, sd $106,492, z=-0.42, p=0.657; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 76 | -13,977 | 0.78 | -13.9 |  | 160 | 168,830 | 1.62 | [102266, 66564] |
| A_k3 | 76 | 4,093 | 1.05 | 4.1 |  | 160 | 149,374 | 1.45 | [63208, 86166] |
| A_k4 | 76 | 33,005 | 1.50 | 32.7 | * | 160 | 96,684 | 1.23 | [101101, -4416] |
| B_thr2_k2 | 84 | 4,336 | 1.07 | 3.8 |  | 204 | 185,497 | 1.55 | [84797, 100700] |
| B_thr2_k3 | 84 | 11,954 | 1.16 | 10.4 |  | 204 | 125,227 | 1.30 | [15579, 109648] |
| B_thr2_k4 | 84 | 31,169 | 1.52 | 27.2 |  | 204 | 73,187 | 1.15 | [35877, 37310] |
| B_thr3_k2 | 63 | 12,302 | 1.27 | 14.1 |  | 156 | 238,111 | 2.04 | [97194, 140917] |
| B_thr3_k3 | 63 | 21,352 | 1.37 | 24.4 |  | 156 | 179,981 | 1.59 | [41674, 138307] |
| B_thr3_k4 | 63 | 32,462 | 1.68 | 37.2 |  | 156 | 151,356 | 1.44 | [58341, 93014] |
| B_thr4_k2 | 41 | 7,111 | 1.22 | 12.5 |  | 130 | 255,556 | 2.62 | [99491, 156065] |
| B_thr4_k3 | 41 | 5,943 | 1.12 | 10.5 |  | 130 | 252,654 | 2.40 | [55939, 196715] |
| B_thr4_k4 | 41 | 23,021 | 1.65 | 40.6 |  | 130 | 259,599 | 2.41 | [66411, 193187] |
| C_k2 | 154 | -25,731 | 0.83 | -12.6 |  | 318 | 98,762 | 1.12 | [110266, -11505] |
| C_k3 | 154 | -7,661 | 0.95 | -3.7 |  | 318 | 79,307 | 1.09 | [71209, 8098] |
| C_k4 | 154 | 21,251 | 1.14 | 10.4 |  | 318 | 26,617 | 1.03 | [109101, -82485] |

## Per-arm walk-forward (ES+NQ pooled)


### armA_ESNQ — ES+NQ

Selected on fold 1: **A_k4**  
OOS (folds 2+3): n=160 net=$96,684 pf=1.23 wr=0.61 sharpe=0.90 bps=21.1 folds=[0, 101101, -4416] fold_n=[0, 80, 80]

Gates: pro-rata drift baseline = $125,027 (excess = $-28,343); random same-length windows: mean $142,551, sd $108,388, z=-0.42, p=0.674; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 76 | -13,977 | 0.78 | -13.9 |  | 160 | 168,830 | 1.62 | [102266, 66564] |
| A_k3 | 76 | 4,093 | 1.05 | 4.1 |  | 160 | 149,374 | 1.45 | [63208, 86166] |
| A_k4 | 76 | 33,005 | 1.50 | 32.7 | * | 160 | 96,684 | 1.23 | [101101, -4416] |

### armB_ESNQ — ES+NQ

Selected on fold 1: **B_thr3_k4**  
OOS (folds 2+3): n=156 net=$151,356 pf=1.44 wr=0.56 sharpe=1.43 bps=34.7 folds=[0, 58341, 93014] fold_n=[0, 87, 69]

Gates: pro-rata drift baseline = $61,958 (excess = $89,398); random same-length windows: mean $72,507, sd $95,514, z=0.83, p=0.209; MTD permutation: mean $39,528, z=1.69, p=0.042; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| B_thr2_k2 | 84 | 4,336 | 1.07 | 3.8 |  | 204 | 185,497 | 1.55 | [84797, 100700] |
| B_thr2_k3 | 84 | 11,954 | 1.16 | 10.4 |  | 204 | 125,227 | 1.30 | [15579, 109648] |
| B_thr2_k4 | 84 | 31,169 | 1.52 | 27.2 |  | 204 | 73,187 | 1.15 | [35877, 37310] |
| B_thr3_k2 | 63 | 12,302 | 1.27 | 14.1 |  | 156 | 238,111 | 2.04 | [97194, 140917] |
| B_thr3_k3 | 63 | 21,352 | 1.37 | 24.4 |  | 156 | 179,981 | 1.59 | [41674, 138307] |
| B_thr3_k4 | 63 | 32,462 | 1.68 | 37.2 | * | 156 | 151,356 | 1.44 | [58341, 93014] |
| B_thr4_k2 | 41 | 7,111 | 1.22 | 12.5 |  | 130 | 255,556 | 2.62 | [99491, 156065] |
| B_thr4_k3 | 41 | 5,943 | 1.12 | 10.5 |  | 130 | 252,654 | 2.40 | [55939, 196715] |
| B_thr4_k4 | 41 | 23,021 | 1.65 | 40.6 |  | 130 | 259,599 | 2.41 | [66411, 193187] |

### armC_ESNQ — ES+NQ

Selected on fold 1: **C_k4**  
OOS (folds 2+3): n=318 net=$26,617 pf=1.03 wr=0.51 sharpe=0.17 bps=2.9 folds=[0, 109101, -82485] fold_n=[0, 160, 158]

Gates: pro-rata drift baseline = $-25,122 (excess = $51,738); random same-length windows: mean $-31,020, sd $153,427, z=0.38, p=0.356; OOS windows touching a roll day: 54


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| C_k2 | 154 | -25,731 | 0.83 | -12.6 |  | 318 | 98,762 | 1.12 | [110266, -11505] |
| C_k3 | 154 | -7,661 | 0.95 | -3.7 |  | 318 | 79,307 | 1.09 | [71209, 8098] |
| C_k4 | 154 | 21,251 | 1.14 | 10.4 | * | 318 | 26,617 | 1.03 | [109101, -82485] |

## Per-instrument (15-cell grid each)


### inst_ES — ES

Selected on fold 1: **B_thr3_k4**  
OOS (folds 2+3): n=70 net=$24,086 pf=1.22 wr=0.53 sharpe=0.52 bps=15.1 folds=[0, 16928, 7158] fold_n=[0, 40, 30]

Gates: pro-rata drift baseline = $16,020 (excess = $8,067); random same-length windows: mean $19,901, sd $43,849, z=0.10, p=0.467; MTD permutation: mean $12,730, z=0.36, p=0.375; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | -7,371 | 0.75 | -14.6 |  | 80 | 56,593 | 1.61 | [33528, 23065] |
| A_k3 | 38 | -1,621 | 0.95 | -3.2 |  | 80 | 51,643 | 1.45 | [29140, 22503] |
| A_k4 | 38 | 12,792 | 1.44 | 25.3 |  | 80 | 34,618 | 1.24 | [41603, -6985] |
| B_thr2_k2 | 39 | -4,728 | 0.84 | -8.9 |  | 93 | 61,043 | 1.63 | [32992, 28051] |
| B_thr2_k3 | 39 | 785 | 1.02 | 1.5 |  | 93 | 46,068 | 1.39 | [18129, 27938] |
| B_thr2_k4 | 39 | 13,185 | 1.52 | 24.8 |  | 93 | 35,193 | 1.26 | [21142, 14051] |
| B_thr3_k2 | 23 | 4,169 | 1.29 | 13.1 |  | 70 | 61,862 | 1.89 | [36916, 24946] |
| B_thr3_k3 | 23 | 9,619 | 1.54 | 30.3 |  | 70 | 38,937 | 1.41 | [17716, 21221] |
| B_thr3_k4 | 23 | 15,769 | 2.07 | 49.7 | * | 70 | 24,086 | 1.22 | [16928, 7158] |
| B_thr4_k2 | 13 | 5,499 | 1.72 | 31.5 |  | 53 | 43,752 | 1.92 | [23209, 20544] |
| B_thr4_k3 | 13 | 6,812 | 1.51 | 39.1 |  | 53 | 32,240 | 1.54 | [4671, 27569] |
| B_thr4_k4 | 13 | 14,224 | 2.58 | 81.6 |  | 53 | 41,540 | 1.76 | [5684, 35856] |
| C_k2 | 77 | -8,478 | 0.86 | -8.3 |  | 159 | 22,791 | 1.08 | [32805, -10014] |
| C_k3 | 77 | -2,728 | 0.96 | -2.7 |  | 159 | 17,841 | 1.06 | [28417, -10577] |
| C_k4 | 77 | 11,685 | 1.19 | 11.4 |  | 159 | 816 | 1.00 | [40880, -40064] |

### inst_NQ — NQ

Selected on fold 1: **A_k4**  
OOS (folds 2+3): n=80 net=$62,066 pf=1.22 wr=0.62 sharpe=0.65 bps=23.3 folds=[0, 59498, 2568] fold_n=[0, 40, 40]

Gates: pro-rata drift baseline = $84,380 (excess = $-22,314); random same-length windows: mean $100,402, sd $94,018, z=-0.41, p=0.662; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | -6,606 | 0.82 | -13.1 |  | 80 | 112,236 | 1.63 | [68738, 43498] |
| A_k3 | 38 | 5,714 | 1.14 | 11.3 |  | 80 | 97,731 | 1.45 | [34068, 63663] |
| A_k4 | 38 | 20,214 | 1.55 | 40.1 | * | 80 | 62,066 | 1.22 | [59498, 2568] |
| B_thr2_k2 | 45 | 9,064 | 1.28 | 14.7 |  | 111 | 124,454 | 1.51 | [51805, 72649] |
| B_thr2_k3 | 45 | 11,169 | 1.26 | 18.2 |  | 111 | 79,159 | 1.26 | [-2550, 81709] |
| B_thr2_k4 | 45 | 17,984 | 1.52 | 29.2 |  | 111 | 37,994 | 1.11 | [14735, 23259] |
| B_thr3_k2 | 40 | 8,133 | 1.27 | 14.6 |  | 86 | 176,249 | 2.11 | [60278, 115971] |
| B_thr3_k3 | 40 | 11,733 | 1.30 | 21.1 |  | 86 | 141,044 | 1.67 | [23958, 117086] |
| B_thr3_k4 | 40 | 16,693 | 1.50 | 30.0 |  | 86 | 127,269 | 1.54 | [41413, 85856] |
| B_thr4_k2 | 28 | 1,612 | 1.07 | 4.1 |  | 77 | 211,804 | 2.93 | [76283, 135521] |
| B_thr4_k3 | 28 | -868 | 0.97 | -2.2 |  | 77 | 220,414 | 2.83 | [51268, 169146] |
| B_thr4_k4 | 28 | 8,797 | 1.33 | 22.4 |  | 77 | 218,059 | 2.69 | [60728, 157331] |
| C_k2 | 77 | -17,254 | 0.80 | -16.9 |  | 159 | 75,971 | 1.14 | [77462, -1491] |
| C_k3 | 77 | -4,934 | 0.95 | -4.8 |  | 159 | 61,466 | 1.11 | [42792, 18674] |
| C_k4 | 77 | 9,566 | 1.11 | 9.3 |  | 159 | 25,801 | 1.04 | [68222, -42421] |

### inst_GC — GC

Selected on fold 1: **A_k2**  
OOS (folds 2+3): n=80 net=$50,570 pf=1.41 wr=0.60 sharpe=0.89 bps=26.3 folds=[0, 43970, 6600] fold_n=[0, 40, 40]

Gates: pro-rata drift baseline = $42,727 (excess = $7,843); random same-length windows: mean $45,261, sd $50,850, z=0.10, p=0.470; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | 15,698 | 1.87 | 31.9 | * | 80 | 50,570 | 1.41 | [43970, 6600] |
| A_k3 | 38 | 11,358 | 1.54 | 23.1 |  | 80 | 81,940 | 1.65 | [25020, 56920] |
| A_k4 | 38 | 10,008 | 1.36 | 20.3 |  | 80 | 120,080 | 1.79 | [50680, 69400] |
| B_thr2_k2 | 27 | 12,772 | 2.10 | 36.1 |  | 92 | -1,038 | 0.99 | [47054, -48092] |
| B_thr2_k3 | 27 | 9,712 | 1.73 | 27.5 |  | 92 | 9,162 | 1.05 | [32714, -23552] |
| B_thr2_k4 | 27 | 3,602 | 1.19 | 10.2 |  | 92 | 17,722 | 1.08 | [47954, -30232] |
| B_thr3_k2 | 19 | 10,554 | 2.71 | 42.2 |  | 67 | 3,012 | 1.02 | [58254, -55242] |
| B_thr3_k3 | 19 | 6,334 | 1.88 | 25.4 |  | 67 | 24,552 | 1.18 | [46084, -21532] |
| B_thr3_k4 | 19 | 3,954 | 1.36 | 15.8 |  | 67 | 24,452 | 1.15 | [67004, -42552] |
| B_thr4_k2 | 7 | 3,812 | 3.12 | 39.6 |  | 52 | 5,902 | 1.05 | [52760, -46858] |
| B_thr4_k3 | 7 | 612 | 1.23 | 6.4 |  | 52 | 23,702 | 1.19 | [42480, -18778] |
| B_thr4_k4 | 7 | -2,638 | 0.51 | -27.4 |  | 52 | 19,112 | 1.13 | [57210, -38098] |
| C_k2 | 77 | -4,958 | 0.92 | -5.0 |  | 159 | 13,494 | 1.04 | [38750, -25256] |
| C_k3 | 77 | -9,298 | 0.85 | -9.3 |  | 159 | 44,864 | 1.12 | [19800, 25064] |
| C_k4 | 77 | -10,648 | 0.85 | -10.7 |  | 159 | 83,004 | 1.21 | [45460, 37544] |

### inst_SPY — SPY

Selected on fold 1: **B_thr2_k4**  
OOS (folds 2+3): n=94 net=$15,768 pf=1.27 wr=0.53 sharpe=0.79 bps=16.8 folds=[0, 12775, 2993] fold_n=[0, 49, 45]

Gates: pro-rata drift baseline = $10,713 (excess = $5,055); random same-length windows: mean $12,693, sd $23,063, z=0.13, p=0.456; MTD permutation: mean $13,873, z=0.14, p=0.447; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | -1,536 | 0.92 | -4.0 |  | 80 | 28,889 | 1.76 | [18855, 10034] |
| A_k3 | 38 | 3,989 | 1.18 | 10.5 |  | 80 | 29,174 | 1.61 | [19994, 9180] |
| A_k4 | 38 | 13,438 | 1.69 | 35.4 |  | 80 | 27,494 | 1.49 | [27634, -140] |
| B_thr2_k2 | 39 | 1,723 | 1.10 | 4.4 |  | 94 | 23,586 | 1.50 | [15501, 8085] |
| B_thr2_k3 | 39 | 6,814 | 1.35 | 17.5 |  | 94 | 18,280 | 1.34 | [9949, 8331] |
| B_thr2_k4 | 39 | 13,551 | 1.82 | 34.7 | * | 94 | 15,768 | 1.27 | [12775, 2993] |
| B_thr3_k2 | 26 | 367 | 1.03 | 1.4 |  | 71 | 28,511 | 1.85 | [17055, 11456] |
| B_thr3_k3 | 26 | 2,897 | 1.17 | 11.1 |  | 71 | 16,932 | 1.38 | [6403, 10529] |
| B_thr3_k4 | 26 | 7,369 | 1.48 | 28.3 |  | 71 | 15,652 | 1.34 | [8682, 6970] |
| B_thr4_k2 | 13 | 4,532 | 1.85 | 34.9 |  | 55 | 21,401 | 1.81 | [15440, 5961] |
| B_thr4_k3 | 13 | 7,468 | 1.93 | 57.4 |  | 55 | 6,972 | 1.19 | [4939, 2034] |
| B_thr4_k4 | 13 | 11,868 | 2.91 | 91.3 |  | 55 | 4,605 | 1.12 | [6971, -2367] |
| C_k2 | 77 | -3,523 | 0.92 | -4.6 |  | 159 | 10,295 | 1.08 | [14815, -4521] |
| C_k3 | 77 | 2,002 | 1.04 | 2.6 |  | 159 | 10,579 | 1.08 | [15954, -5375] |
| C_k4 | 77 | 11,451 | 1.25 | 14.9 |  | 159 | 8,899 | 1.06 | [23594, -14695] |

### inst_QQQ — QQQ

Selected on fold 1: **B_thr2_k4**  
OOS (folds 2+3): n=110 net=$33,114 pf=1.35 wr=0.55 sharpe=1.14 bps=30.1 folds=[0, 21783, 11331] fold_n=[0, 57, 53]

Gates: pro-rata drift baseline = $19,689 (excess = $13,425); random same-length windows: mean $20,936, sd $31,035, z=0.39, p=0.377; MTD permutation: mean $23,703, z=0.53, p=0.301; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | -1,362 | 0.94 | -3.6 |  | 80 | 43,851 | 1.85 | [32446, 11405] |
| A_k3 | 38 | 8,269 | 1.31 | 21.8 |  | 80 | 39,568 | 1.60 | [23894, 15674] |
| A_k4 | 38 | 19,182 | 1.75 | 50.5 |  | 80 | 37,840 | 1.49 | [35923, 1917] |
| B_thr2_k2 | 46 | 12,820 | 1.60 | 27.9 |  | 110 | 46,451 | 1.62 | [27948, 18503] |
| B_thr2_k3 | 46 | 16,607 | 1.63 | 36.1 |  | 110 | 31,552 | 1.34 | [11892, 19660] |
| B_thr2_k4 | 46 | 21,864 | 1.99 | 47.5 | * | 110 | 33,114 | 1.35 | [21783, 11331] |
| B_thr3_k2 | 38 | 8,519 | 1.43 | 22.4 |  | 90 | 62,605 | 2.15 | [34876, 27729] |
| B_thr3_k3 | 38 | 12,798 | 1.54 | 33.7 |  | 90 | 48,837 | 1.69 | [20726, 28111] |
| B_thr3_k4 | 38 | 14,621 | 1.69 | 38.5 |  | 90 | 49,764 | 1.70 | [28913, 20852] |
| B_thr4_k2 | 28 | 3,681 | 1.22 | 13.1 |  | 75 | 57,323 | 2.44 | [32984, 24339] |
| B_thr4_k3 | 28 | 4,235 | 1.20 | 15.1 |  | 75 | 50,879 | 2.02 | [24543, 26336] |
| B_thr4_k4 | 28 | 10,351 | 1.60 | 37.0 |  | 75 | 51,874 | 1.97 | [31582, 20292] |
| C_k2 | 77 | -10,464 | 0.84 | -13.6 |  | 159 | 27,803 | 1.17 | [33218, -5415] |
| C_k3 | 77 | -833 | 0.99 | -1.1 |  | 159 | 23,520 | 1.13 | [24666, -1146] |
| C_k4 | 77 | 10,080 | 1.15 | 13.1 |  | 159 | 21,792 | 1.11 | [36695, -14903] |

### inst_GLD — GLD

Selected on fold 1: **B_thr2_k2**  
OOS (folds 2+3): n=88 net=$15,480 pf=1.27 wr=0.52 sharpe=0.78 bps=17.6 folds=[0, 22540, -7060] fold_n=[0, 39, 49]

Gates: pro-rata drift baseline = $7,750 (excess = $7,730); random same-length windows: mean $8,523, sd $17,841, z=0.39, p=0.348; MTD permutation: mean $16,396, z=-0.07, p=0.528; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 38 | 9,570 | 1.67 | 25.2 |  | 80 | 31,036 | 1.69 | [21463, 9573] |
| A_k3 | 38 | 8,699 | 1.54 | 22.9 |  | 80 | 37,914 | 1.80 | [13504, 24410] |
| A_k4 | 38 | 6,780 | 1.30 | 17.8 |  | 80 | 53,470 | 1.94 | [27321, 26149] |
| B_thr2_k2 | 25 | 10,454 | 2.35 | 41.8 | * | 88 | 15,480 | 1.27 | [22540, -7060] |
| B_thr2_k3 | 25 | 9,032 | 2.16 | 36.1 |  | 88 | 17,113 | 1.30 | [16561, 552] |
| B_thr2_k4 | 25 | 5,335 | 1.44 | 21.3 |  | 88 | 22,190 | 1.33 | [26147, -3957] |
| B_thr3_k2 | 18 | 10,363 | 4.16 | 57.6 |  | 65 | 25,400 | 1.64 | [25892, -491] |
| B_thr3_k3 | 18 | 6,675 | 2.70 | 37.1 |  | 65 | 31,899 | 1.85 | [24068, 7830] |
| B_thr3_k4 | 18 | 5,961 | 1.90 | 33.1 |  | 65 | 32,993 | 1.72 | [31989, 1004] |
| B_thr4_k2 | 5 | 3,734 | 9.74 | 74.7 |  | 50 | 17,950 | 1.53 | [23924, -5974] |
| B_thr4_k3 | 5 | 924 | 1.56 | 18.5 |  | 50 | 21,957 | 1.65 | [20091, 1866] |
| B_thr4_k4 | 5 | -1,142 | 0.64 | -22.8 |  | 50 | 19,172 | 1.46 | [24326, -5154] |
| C_k2 | 77 | -6,979 | 0.85 | -9.1 |  | 159 | 6,060 | 1.04 | [10605, -4545] |
| C_k3 | 77 | -7,850 | 0.83 | -10.2 |  | 159 | 12,938 | 1.09 | [2647, 10291] |
| C_k4 | 77 | -9,769 | 0.82 | -12.7 |  | 159 | 28,493 | 1.19 | [16463, 12031] |

### inst_MES — MES

Selected on fold 1: **A_k4**  
OOS (folds 2+3): n=58 net=$-784 pf=0.94 wr=0.53 sharpe=-0.17 bps=-5.1 folds=[0, -385, -400] fold_n=[0, 29, 29]

Gates: pro-rata drift baseline = $2,288 (excess = $-3,072); random same-length windows: mean $2,901, sd $4,451, z=-0.83, p=0.801; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 28 | 1,023 | 1.37 | 21.0 |  | 58 | 3,682 | 1.48 | [1998, 1684] |
| A_k3 | 28 | 2,218 | 1.70 | 45.5 |  | 58 | 1,988 | 1.20 | [-317, 2305] |
| A_k4 | 28 | 3,760 | 2.62 | 77.2 | * | 58 | -784 | 0.94 | [-385, -400] |
| B_thr2_k2 | 34 | -817 | 0.81 | -14.0 |  | 67 | 6,017 | 1.90 | [3910, 2107] |
| B_thr2_k3 | 34 | -558 | 0.87 | -9.5 |  | 67 | 4,172 | 1.45 | [1672, 2500] |
| B_thr2_k4 | 34 | 505 | 1.12 | 8.6 |  | 67 | 2,524 | 1.24 | [1220, 1304] |
| B_thr3_k2 | 23 | 115 | 1.04 | 3.0 |  | 51 | 5,893 | 2.25 | [4464, 1429] |
| B_thr3_k3 | 23 | 105 | 1.04 | 2.7 |  | 51 | 3,878 | 1.55 | [2494, 1384] |
| B_thr3_k4 | 23 | 625 | 1.23 | 16.0 |  | 51 | 1,951 | 1.22 | [1899, 51] |
| B_thr4_k2 | 14 | -17 | 0.99 | -0.7 |  | 39 | 4,230 | 2.44 | [2030, 2200] |
| B_thr4_k3 | 14 | -619 | 0.72 | -24.8 |  | 39 | 3,680 | 1.96 | [404, 3276] |
| B_thr4_k4 | 14 | -240 | 0.88 | -9.6 |  | 39 | 4,232 | 2.19 | [88, 4144] |
| C_k2 | 56 | -499 | 0.94 | -5.1 |  | 116 | 1,693 | 1.07 | [3724, -2031] |
| C_k3 | 56 | 696 | 1.08 | 7.2 |  | 116 | -1 | 1.00 | [1409, -1410] |
| C_k4 | 56 | 2,239 | 1.29 | 23.0 |  | 116 | -2,773 | 0.90 | [1342, -4115] |

### inst_MNQ — MNQ

Selected on fold 1: **A_k4**  
OOS (folds 2+3): n=58 net=$-683 pf=0.97 wr=0.57 sharpe=-0.08 bps=-3.2 folds=[0, -1804, 1121] fold_n=[0, 29, 29]

Gates: pro-rata drift baseline = $4,532 (excess = $-5,215); random same-length windows: mean $5,416, sd $8,787, z=-0.69, p=0.776; OOS windows touching a roll day: 0


| cell | IS n | IS net | IS pf | IS bps | sel | OOS n | OOS net | OOS pf | OOS folds |
|---|---:|---:|---:|---:|:-:|---:|---:|---:|---|
| A_k2 | 28 | 2,953 | 1.73 | 48.1 |  | 58 | 7,427 | 1.49 | [3653, 3774] |
| A_k3 | 28 | 3,667 | 1.74 | 59.7 |  | 58 | 5,296 | 1.29 | [-1275, 6571] |
| A_k4 | 28 | 6,510 | 2.69 | 105.9 | * | 58 | -683 | 0.97 | [-1804, 1121] |
| B_thr2_k2 | 40 | -228 | 0.97 | -2.5 |  | 79 | 12,158 | 1.67 | [7010, 5148] |
| B_thr2_k3 | 40 | -1,140 | 0.87 | -12.7 |  | 79 | 8,250 | 1.35 | [1652, 6598] |
| B_thr2_k4 | 40 | 882 | 1.11 | 9.8 |  | 79 | 2,398 | 1.08 | [1268, 1129] |
| B_thr3_k2 | 33 | 887 | 1.17 | 12.8 |  | 61 | 16,259 | 2.36 | [6600, 9660] |
| B_thr3_k3 | 33 | 180 | 1.03 | 2.6 |  | 61 | 13,155 | 1.80 | [2905, 10250] |
| B_thr3_k4 | 33 | 2,213 | 1.42 | 31.9 |  | 61 | 10,030 | 1.51 | [2607, 7423] |
| B_thr4_k2 | 28 | 1,065 | 1.27 | 17.7 |  | 54 | 19,900 | 3.63 | [8282, 11618] |
| B_thr4_k3 | 28 | -6 | 1.00 | -0.1 |  | 54 | 21,188 | 3.69 | [5729, 15459] |
| B_thr4_k4 | 28 | 1,655 | 1.38 | 27.5 |  | 54 | 19,545 | 3.04 | [4971, 14574] |
| C_k2 | 56 | -323 | 0.97 | -2.6 |  | 116 | 6,920 | 1.16 | [7342, -421] |
| C_k3 | 56 | 391 | 1.03 | 3.2 |  | 116 | 4,789 | 1.10 | [2414, 2375] |
| C_k4 | 56 | 3,234 | 1.26 | 26.4 |  | 116 | -1,190 | 0.98 | [1885, -3074] |

## Fixed-rule cross-section (no selection; full period; arm B thr=3% k=3 and arm A k=3)

| inst | rule | n | net | pf | wr | bps | folds | random-window z | p |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| ES | B_thr3_k3 | 93 | 48,555 | 1.43 | 0.56 | 25.4 | [9619, 17716, 21221] | 0.80 | 0.207 |
| ES | A_k3 | 118 | 50,023 | 1.33 | 0.59 | 20.5 | [-1621, 29140, 22503] | 0.12 | 0.450 |
| ES | C_k3 | 236 | 15,113 | 1.04 | 0.51 | 3.1 | [-2728, 28417, -10577] | 0.61 | 0.267 |
| NQ | B_thr3_k3 | 126 | 152,777 | 1.61 | 0.58 | 46.1 | [11733, 23958, 117086] | 1.36 | 0.090 |
| NQ | A_k3 | 118 | 103,445 | 1.40 | 0.59 | 32.7 | [5714, 34068, 63663] | 0.11 | 0.447 |
| NQ | C_k3 | 236 | 56,532 | 1.08 | 0.50 | 9.0 | [-4934, 42792, 18674] | 0.83 | 0.187 |
| MES | B_thr3_k3 | 74 | 3,983 | 1.40 | 0.53 | 24.0 | [105, 2494, 1384] | 0.75 | 0.227 |
| MES | A_k3 | 86 | 4,206 | 1.33 | 0.56 | 20.8 | [2218, -317, 2305] | 0.23 | 0.430 |
| MES | C_k3 | 172 | 696 | 1.02 | 0.49 | 1.7 | [696, 1409, -1410] | 0.44 | 0.327 |
| MNQ | B_thr3_k3 | 94 | 13,335 | 1.58 | 0.55 | 46.2 | [180, 2905, 10250] | 1.27 | 0.110 |
| MNQ | A_k3 | 86 | 8,962 | 1.39 | 0.58 | 32.5 | [3667, -1275, 6571] | 0.24 | 0.400 |
| MNQ | C_k3 | 172 | 5,180 | 1.09 | 0.48 | 9.4 | [391, 2414, 2375] | 0.80 | 0.207 |
| GC | B_thr3_k3 | 86 | 30,886 | 1.21 | 0.59 | 15.8 | [6334, 46084, -21532] | 0.21 | 0.407 |
| GC | A_k3 | 118 | 93,298 | 1.63 | 0.58 | 38.6 | [11358, 25020, 56920] | 0.54 | 0.263 |
| GC | C_k3 | 236 | 35,566 | 1.08 | 0.53 | 7.4 | [-9298, 19800, 25064] | 0.86 | 0.193 |
| SPY | B_thr3_k3 | 97 | 19,829 | 1.32 | 0.53 | 20.4 | [2897, 6403, 10529] | 0.56 | 0.273 |
| SPY | A_k3 | 118 | 33,163 | 1.47 | 0.60 | 28.1 | [3989, 19994, 9180] | 0.34 | 0.367 |
| SPY | C_k3 | 236 | 12,581 | 1.07 | 0.50 | 5.3 | [2002, 15954, -5375] | 0.74 | 0.230 |
| QQQ | B_thr3_k3 | 128 | 61,635 | 1.65 | 0.58 | 48.2 | [12798, 20726, 28111] | 1.47 | 0.087 |
| QQQ | A_k3 | 118 | 47,837 | 1.52 | 0.60 | 40.5 | [8269, 23894, 15674] | 0.36 | 0.363 |
| QQQ | C_k3 | 236 | 22,687 | 1.09 | 0.50 | 9.6 | [-833, 24666, -1146] | 0.98 | 0.147 |
| GLD | B_thr3_k3 | 83 | 38,574 | 1.93 | 0.58 | 46.5 | [6675, 24068, 7830] | 1.72 | 0.027 |
| GLD | A_k3 | 118 | 46,613 | 1.73 | 0.55 | 39.5 | [8699, 13504, 24410] | 1.08 | 0.123 |
| GLD | C_k3 | 236 | 5,088 | 1.03 | 0.50 | 2.2 | [-7850, 2647, 10291] | 0.44 | 0.313 |

## Arm B leg decomposition (ES+NQ, thr=3%, k=3, full period, in-sample)

| leg | n | net | avg bps | wr |
|---|---:|---:|---:|---:|
| long_T-1_T+k after up-month | 88 | 100,373 | 35.0 | 0.67 |
| long_T-3_T+k (MTD<=-thr) | 43 | 148,596 | 140.9 | 0.74 |
| short_T-3_T-1 (MTD>=+thr) | 88 | -47,637 | -26.0 | 0.39 |

## Diagnostic: ES return of T-3..T-1 and T-1..T+3 by MTD bucket (full period, in-sample, bps)

| MTD bucket | months | mean T-3..T-1 | mean T-1..T+3 | t(post) |
|---|---:|---:|---:|---:|
| <-4% | 14 | 58.6 | 66.3 | 1.10 |
| -4..-2% | 10 | 14.7 | 75.3 | 0.90 |
| -2..0% | 13 | 3.8 | -25.4 | -0.44 |
| 0..2% | 26 | 3.6 | 59.9 | 2.26 |
| 2..4% | 28 | 7.6 | -9.9 | -0.30 |
| >4% | 26 | 5.9 | -11.1 | -0.23 |

Spearman corr(MTD, pre) = -0.094; corr(MTD, post) = -0.061


## Diagnostic: is the post-down-month rebound month-end specific? (7-session fwd return after trailing-15-session return <= -3%, bps)

| inst | at T-3: n | mean | t | any day: n | mean | t | diff t |
|---|---:|---:|---:|---:|---:|---:|---:|
| ES | 16 | 174 | 3.20 | 314 | 74 | 3.03 | 1.66 |
| NQ | 23 | 151 | 2.63 | 400 | 83 | 3.61 | 1.10 |
| SPY | 15 | 161 | 3.24 | 316 | 70 | 2.75 | 1.63 |
| GLD | 19 | 81 | 1.38 | 322 | 58 | 3.65 | 0.38 |

## 1h tradability check (2024-05 .. 2026-08, fills at the 16:00 ET hourly-bar open vs daily settlement)

- ES A_k4: |16:00ET − daily close| median 1.5 bps, p90 4.4 bps over 593 days; daily-close fills: n=27 net=$-521 pf=0.99 wr=0.63 sharpe=-0.01 bps=-0.6 folds=[-1024, -30611, 31114] fold_n=[9, 9, 9]; 16:00 fills: n=27 net=$-446 pf=0.99 wr=0.63 sharpe=-0.01 bps=-0.5 folds=[-999, -30449, 31001] fold_n=[9, 9, 9]
- ES A_k3: |16:00ET − daily close| median 1.5 bps, p90 4.4 bps over 593 days; daily-close fills: n=27 net=$25,654 pf=1.56 wr=0.52 sharpe=0.86 bps=30.0 folds=[-7286, -1361, 34301] fold_n=[9, 9, 9]; 16:00 fills: n=25 net=$18,955 pf=1.42 wr=0.48 sharpe=0.64 bps=23.8 folds=[-9167, -6342, 34464] fold_n=[8, 8, 9]
- NQ A_k4: |16:00ET − daily close| median 1.6 bps, p90 4.8 bps over 590 days; daily-close fills: n=27 net=$14,364 pf=1.10 wr=0.59 sharpe=0.18 bps=11.5 folds=[11100, -46615, 49880] fold_n=[9, 9, 9]; 16:00 fills: n=27 net=$14,729 pf=1.11 wr=0.59 sharpe=0.19 bps=11.8 folds=[10975, -46200, 49955] fold_n=[9, 9, 9]
- NQ A_k3: |16:00ET − daily close| median 1.6 bps, p90 4.8 bps over 590 days; daily-close fills: n=27 net=$66,824 pf=1.78 wr=0.63 sharpe=1.14 bps=53.5 folds=[4985, -1500, 63340] fold_n=[9, 9, 9]; 16:00 fills: n=25 net=$53,890 pf=1.64 wr=0.60 sharpe=0.93 bps=46.3 folds=[-1912, -7702, 63505] fold_n=[8, 8, 9]

## Verdict

Criteria: {"oos_net_pos": true, "pf_ge_1_2": true, "n_ge_60": true, "folds_pos": false, "random_p_lt_05": false, "beats_drift": false, "neighbours_pos": true}; neighbours (OOS net): [('A_k3', 149374.49999999843)]  
**Verdict: none**

## Interpretation

1. **Headline = none.** Walk-forward on the pooled ES+NQ 15-cell grid selected the unconditional turn-of-month long `A_k4` on fold 1 (IS $33k, pf 1.50). OOS (2019-12 .. 2026-08): n=160, net $96.7k, pf 1.23, folds +$101k / -$4.4k. It is *below* both gates: the pro-rata buy-and-hold drift over the same sessions is $125k and 1,000 random same-side same-length windows average $142k (p=0.66, z=-0.42). The unconditional arm is index beta held over 5 sessions, exactly the overnight_drift mistake the gates were built to catch.
2. **The rebalancing mechanism is not in the prices.** Pre-window (T-3..T-1) returns after months with MTD >= +2% are +6 to +8 bps, not negative; the arm-B short leg loses money in-sample (-$47.6k over 88 legs). Spearman corr(MTD, pre-window) = -0.09. If pensions are selling into month-end after up-months, the market absorbs it without a price footprint at daily resolution.
3. **What arm B actually captures is a post-drawdown rebound.** Arm B walk-forward (grid restricted to arm B, `B_thr3_k4`) is the best-looking sub-result: OOS $151k, pf 1.44, both OOS folds positive, beats drift ($62k), MTD-permutation p=0.04 — but random-window p=0.21 and every dollar comes from the 43 "long after MTD <= -3%" legs ($148.6k). The 7-session return after a >=3% 15-session drawdown is +174 bps when it starts at T-3 vs +74 bps on any other day (ES, n=16 vs 314, diff t=1.66); suggestive of a month-end-specific rebound, nowhere near established. Choosing arm B after seeing its OOS would be post-hoc selection; it is reported, not headlined.
4. **The non-equity control shows the same thing.** GC `A_k3` full-period: 38.6 bps/trade, pf 1.63; GLD `B_thr3_k3`: 46.5 bps, pf 1.93, random-window p=0.027. Whatever turn-of-month pattern exists here is not specific to equity-index rebalancing.
5. **Roll check passed for A/B, failed for C.** Zero A/B windows touch a Yahoo splice day (quarterly rolls are mid-month); arm C's T-8 window touches a roll in 37 of 118 months per instrument, and C is flat anyway (OOS pf 1.03, fold 3 -$82k) even on the roll-adjusted series.
6. **Tradability.** The 16:00 ET hourly-bar price differs from the Yahoo daily settlement by a median 1.5 bps (p90 4.5 bps). Re-running with 16:00 fills on 2024-05..2026-08 gives 0-25% lower net than daily-close fills (ES A_k3 $25.7k -> $19.0k, NQ A_k3 $66.8k -> $53.9k) — executable, but the daily-close numbers slightly overstate.
7. **Micros.** MES/MNQ (2019-05 .. 2026-08, own folds) select `A_k4` on fold 1 and lose OOS (-$784 / -$683, pf 0.94 / 0.97) — small sample, but no support.

Fees are irrelevant here (0.2-0.5 bps per round trip vs 20-40 bps per trade gross); the failure is statistical, not cost-driven.
