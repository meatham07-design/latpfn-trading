# Overnight drift - CME micros (MNQ/MES/MYM/MGC)

Execution: 1 contract, market at bar open of the scheduled hour (yfinance 1h, ET), CME round-trip fee from common.FEES. Walk-forward: params picked on fold 1 (calendar third), OOS = folds 2+3.

Data span 2024-04-05 -> 2026-08-27; folds: [2024-04-05,2025-01-21), [2025-01-21,2025-11-09), [2025-11-09,2026-08-27)

## MNQ

Selected on fold 1: `{'session': 'on_16_9', 'side': 1, 'filt': 'all'}`  
**OOS folds 2+3**: n= 398 net= 13427.98 pf=1.24 wr=0.57 sharpe=1.51 dd=6248 folds=[0, 4452, 8976]

In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):

| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| on_16_9_L_all | 593 | 23707 | 1.33 | 0.59 | 2.42 | 10279 | 4452 | 8976 | 10279 | * |
| on_16_9_L_no_fri | 476 | 15141 | 1.27 | 0.58 | 1.85 | 9815 | 629 | 4698 | 9815 |  |
| on_16_9_L_vix_lt | 467 | 19594 | 1.38 | 0.60 | 2.40 | 8232 | 5853 | 5508 | 8232 |  |
| on_16_9_L_vix_ge | 126 | 4113 | 1.20 | 0.52 | 0.76 | 2046 | -1402 | 3468 | 2046 |  |
| on_16_9_S_all | 593 | -26363 | 0.73 | 0.40 | -2.69 | -11152 | -5356 | -9855 | -11152 |  |
| on_16_9_S_no_fri | 476 | -17274 | 0.76 | 0.42 | -2.11 | -10504 | -1354 | -5415 | -10504 |  |
| on_16_9_S_vix_lt | 467 | -21686 | 0.70 | 0.39 | -2.65 | -8994 | -6508 | -6185 | -8994 |  |
| on_16_9_S_vix_ge | 126 | -4677 | 0.81 | 0.47 | -0.86 | -2158 | 1151 | -3670 | -2158 |  |
| on_18_9_L_all | 593 | 21190 | 1.33 | 0.58 | 2.46 | 8022 | 4725 | 8443 | 8022 |  |
| on_18_9_L_no_fri | 593 | 21190 | 1.33 | 0.58 | 2.46 | 8022 | 4725 | 8443 | 8022 |  |
| on_18_9_L_vix_lt | 464 | 14149 | 1.33 | 0.59 | 2.16 | 7219 | 2374 | 4556 | 7219 |  |
| on_18_9_L_vix_ge | 129 | 7042 | 1.34 | 0.53 | 1.26 | 803 | 2351 | 3887 | 803 |  |
| on_18_9_S_all | 593 | -23847 | 0.72 | 0.42 | -2.77 | -8901 | -5621 | -9325 | -8901 |  |
| on_18_9_S_no_fri | 593 | -23847 | 0.72 | 0.42 | -2.77 | -8901 | -5621 | -9325 | -8901 |  |
| on_18_9_S_vix_lt | 464 | -16227 | 0.72 | 0.40 | -2.47 | -7985 | -3010 | -5232 | -7985 |  |
| on_18_9_S_vix_ge | 129 | -7619 | 0.73 | 0.47 | -1.36 | -916 | -2611 | -4093 | -916 |  |
| id_9_16_L_all | 593 | -4632 | 0.96 | 0.53 | -0.39 | -4701 | 1649 | -1581 | -4701 |  |
| id_9_16_L_no_fri | 476 | -2396 | 0.97 | 0.52 | -0.22 | -5036 | 4115 | -1475 | -5036 |  |
| id_9_16_L_vix_lt | 467 | -19969 | 0.76 | 0.50 | -2.16 | -8157 | -4092 | -7720 | -8157 |  |
| id_9_16_L_vix_ge | 126 | 15336 | 1.74 | 0.63 | 2.08 | 3456 | 5741 | 6139 | 3456 |  |
| id_9_16_S_all | 593 | 1976 | 1.02 | 0.47 | 0.17 | 3822 | -2550 | 703 | 3822 |  |
| id_9_16_S_no_fri | 476 | 263 | 1.00 | 0.48 | 0.02 | 4341 | -4836 | 758 | 4341 |  |
| id_9_16_S_vix_lt | 467 | 17876 | 1.27 | 0.49 | 1.93 | 7391 | 3442 | 7043 | 7391 |  |
| id_9_16_S_vix_ge | 126 | -15901 | 0.56 | 0.37 | -2.16 | -3568 | -5992 | -6340 | -3568 |  |

## MES

Selected on fold 1: `{'session': 'on_16_9', 'side': 1, 'filt': 'all'}`  
**OOS folds 2+3**: n= 398 net=  3318.98 pf=1.12 wr=0.57 sharpe=0.79 dd=4053 folds=[0, 698, 2621]

In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):

| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| on_16_9_L_all | 593 | 8467 | 1.24 | 0.58 | 1.77 | 5148 | 698 | 2621 | 5148 | * |
| on_16_9_L_no_fri | 476 | 3920 | 1.14 | 0.57 | 1.01 | 4288 | -1206 | 838 | 4288 |  |
| on_16_9_L_vix_lt | 467 | 6690 | 1.28 | 0.59 | 1.83 | 3810 | 1743 | 1137 | 3810 |  |
| on_16_9_L_vix_ge | 126 | 1778 | 1.16 | 0.54 | 0.57 | 1338 | -1044 | 1484 | 1338 |  |
| on_16_9_S_all | 593 | -12903 | 0.72 | 0.39 | -2.69 | -6607 | -2209 | -4087 | -6607 |  |
| on_16_9_S_no_fri | 476 | -7480 | 0.77 | 0.40 | -1.93 | -5440 | -6 | -2035 | -5440 |  |
| on_16_9_S_vix_lt | 467 | -10183 | 0.69 | 0.37 | -2.78 | -5082 | -2835 | -2266 | -5082 |  |
| on_16_9_S_vix_ge | 126 | -2720 | 0.80 | 0.45 | -0.87 | -1525 | 626 | -1821 | -1525 |  |
| on_18_9_L_all | 593 | 9141 | 1.30 | 0.58 | 2.18 | 4387 | 991 | 3763 | 4387 |  |
| on_18_9_L_no_fri | 593 | 9141 | 1.30 | 0.58 | 2.18 | 4387 | 991 | 3763 | 4387 |  |
| on_18_9_L_vix_lt | 464 | 5745 | 1.30 | 0.59 | 2.02 | 3412 | 98 | 2235 | 3412 |  |
| on_18_9_L_vix_ge | 129 | 3396 | 1.29 | 0.53 | 1.10 | 975 | 893 | 1528 | 975 |  |
| on_18_9_S_all | 593 | -13577 | 0.68 | 0.39 | -3.24 | -5853 | -2487 | -5237 | -5853 |  |
| on_18_9_S_no_fri | 593 | -13577 | 0.68 | 0.39 | -3.24 | -5853 | -2487 | -5237 | -5853 |  |
| on_18_9_S_vix_lt | 464 | -9215 | 0.66 | 0.37 | -3.24 | -4691 | -1160 | -3365 | -4691 |  |
| on_18_9_S_vix_ge | 129 | -4361 | 0.72 | 0.46 | -1.41 | -1162 | -1327 | -1872 | -1162 |  |
| id_9_16_L_all | 593 | -1145 | 0.98 | 0.52 | -0.19 | -2467 | 1036 | 286 | -2467 |  |
| id_9_16_L_no_fri | 476 | -325 | 0.99 | 0.52 | -0.06 | -2961 | 2034 | 602 | -2961 |  |
| id_9_16_L_vix_lt | 467 | -8044 | 0.79 | 0.51 | -1.92 | -4251 | -1652 | -2141 | -4251 |  |
| id_9_16_L_vix_ge | 126 | 6899 | 1.54 | 0.58 | 1.60 | 1784 | 2688 | 2427 | 1784 |  |
| id_9_16_S_all | 593 | -3290 | 0.94 | 0.47 | -0.54 | 1001 | -2539 | -1752 | 1001 |  |
| id_9_16_S_no_fri | 476 | -3235 | 0.92 | 0.47 | -0.60 | 1802 | -3238 | -1798 | 1802 |  |
| id_9_16_S_vix_lt | 467 | 4551 | 1.14 | 0.48 | 1.09 | 2972 | 568 | 1012 | 2972 |  |
| id_9_16_S_vix_ge | 126 | -7841 | 0.61 | 0.40 | -1.82 | -1971 | -3107 | -2763 | -1971 |  |

## MYM

Selected on fold 1: `{'session': 'on_16_9', 'side': 1, 'filt': 'all'}`  
**OOS folds 2+3**: n= 398 net=   594.48 pf=1.03 wr=0.51 sharpe=0.21 dd=3491 folds=[0, -942, 1536]

In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):

| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| on_16_9_L_all | 593 | 3083 | 1.13 | 0.52 | 0.97 | 2489 | -942 | 1536 | 2489 | * |
| on_16_9_L_no_fri | 476 | 317 | 1.02 | 0.51 | 0.12 | 1855 | -2144 | 607 | 1855 |  |
| on_16_9_L_vix_lt | 467 | 3030 | 1.19 | 0.54 | 1.28 | 1831 | 252 | 947 | 1831 |  |
| on_16_9_L_vix_ge | 126 | 53 | 1.01 | 0.48 | 0.03 | 658 | -1194 | 590 | 658 |  |
| on_16_9_S_all | 593 | -5740 | 0.80 | 0.45 | -1.81 | -3362 | 37 | -2415 | -3362 |  |
| on_16_9_S_no_fri | 476 | -2449 | 0.88 | 0.47 | -0.94 | -2544 | 1419 | -1323 | -2544 |  |
| on_16_9_S_vix_lt | 467 | -5122 | 0.75 | 0.44 | -2.17 | -2592 | -907 | -1623 | -2592 |  |
| on_16_9_S_vix_ge | 126 | -618 | 0.93 | 0.52 | -0.29 | -770 | 944 | -791 | -770 |  |
| on_18_9_L_all | 593 | 4313 | 1.20 | 0.54 | 1.52 | 1549 | -735 | 3498 | 1549 |  |
| on_18_9_L_no_fri | 593 | 4313 | 1.20 | 0.54 | 1.52 | 1549 | -735 | 3498 | 1549 |  |
| on_18_9_L_vix_lt | 464 | 2955 | 1.22 | 0.55 | 1.54 | 826 | -628 | 2756 | 826 |  |
| on_18_9_L_vix_ge | 129 | 1358 | 1.17 | 0.52 | 0.65 | 722 | -106 | 742 | 722 |  |
| on_18_9_S_all | 593 | -6969 | 0.74 | 0.44 | -2.45 | -2427 | -162 | -4381 | -2427 |  |
| on_18_9_S_no_fri | 593 | -6969 | 0.74 | 0.44 | -2.45 | -2427 | -162 | -4381 | -2427 |  |
| on_18_9_S_vix_lt | 464 | -5033 | 0.71 | 0.43 | -2.63 | -1593 | -8 | -3433 | -1593 |  |
| on_18_9_S_vix_ge | 129 | -1936 | 0.80 | 0.48 | -0.92 | -835 | -153 | -948 | -835 |  |
| id_9_16_L_all | 593 | 813 | 1.02 | 0.53 | 0.20 | -744 | 1220 | 336 | -744 |  |
| id_9_16_L_no_fri | 476 | 646 | 1.02 | 0.52 | 0.18 | -1836 | 1841 | 642 | -1836 |  |
| id_9_16_L_vix_lt | 467 | -3923 | 0.85 | 0.50 | -1.35 | -2208 | -315 | -1400 | -2208 |  |
| id_9_16_L_vix_ge | 126 | 4736 | 1.58 | 0.63 | 1.69 | 1464 | 1535 | 1737 | 1464 |  |
| id_9_16_S_all | 593 | -3469 | 0.90 | 0.46 | -0.86 | -134 | -2121 | -1215 | -134 |  |
| id_9_16_S_no_fri | 476 | -2779 | 0.90 | 0.47 | -0.75 | 1142 | -2562 | -1358 | 1142 |  |
| id_9_16_S_vix_lt | 467 | 1831 | 1.08 | 0.49 | 0.63 | 1442 | -335 | 724 | 1442 |  |
| id_9_16_S_vix_ge | 126 | -5300 | 0.60 | 0.37 | -1.90 | -1576 | -1786 | -1938 | -1576 |  |

## MGC

Selected on fold 1: `{'session': 'on_16_9', 'side': 1, 'filt': 'no_fri'}`  
**OOS folds 2+3**: n= 322 net= 11095.73 pf=1.22 wr=0.59 sharpe=1.11 dd=6571 folds=[0, 3701, 7395]

In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):

| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| on_16_9_L_all | 594 | 25199 | 1.34 | 0.59 | 2.22 | 4173 | 9457 | 11570 | 4173 |  |
| on_16_9_L_no_fri | 477 | 16243 | 1.27 | 0.60 | 1.59 | 5147 | 3701 | 7395 | 5147 | * |
| on_16_9_L_vix_lt | 468 | 24053 | 1.46 | 0.59 | 2.52 | 3624 | 8414 | 12015 | 3624 |  |
| on_16_9_L_vix_ge | 126 | 1147 | 1.05 | 0.60 | 0.18 | 549 | 1043 | -445 | 549 |  |
| on_16_9_S_all | 594 | -29049 | 0.71 | 0.41 | -2.55 | -5443 | -10765 | -12840 | -5443 |  |
| on_16_9_S_no_fri | 477 | -19333 | 0.75 | 0.40 | -1.90 | -6151 | -4751 | -8431 | -6151 |  |
| on_16_9_S_vix_lt | 468 | -27085 | 0.65 | 0.41 | -2.84 | -4732 | -9360 | -12993 | -4732 |  |
| on_16_9_S_vix_ge | 126 | -1963 | 0.92 | 0.40 | -0.32 | -711 | -1405 | 153 | -711 |  |
| on_18_9_L_all | 593 | 15068 | 1.20 | 0.58 | 1.39 | 972 | 4649 | 9447 | 972 |  |
| on_18_9_L_no_fri | 593 | 15068 | 1.20 | 0.58 | 1.39 | 972 | 4649 | 9447 | 972 |  |
| on_18_9_L_vix_lt | 465 | 14392 | 1.28 | 0.58 | 1.66 | 1562 | 2891 | 9940 | 1562 |  |
| on_18_9_L_vix_ge | 128 | 675 | 1.03 | 0.57 | 0.10 | -590 | 1758 | -493 | -590 |  |
| on_18_9_S_all | 593 | -18910 | 0.80 | 0.41 | -1.75 | -2242 | -5945 | -10723 | -2242 |  |
| on_18_9_S_no_fri | 593 | -18910 | 0.80 | 0.41 | -1.75 | -2242 | -5945 | -10723 | -2242 |  |
| on_18_9_S_vix_lt | 465 | -17406 | 0.74 | 0.41 | -2.01 | -2670 | -3811 | -10924 | -2670 |  |
| on_18_9_S_vix_ge | 128 | -1505 | 0.94 | 0.43 | -0.23 | 428 | -2134 | 201 | 428 |  |
| id_9_16_L_all | 594 | -2291 | 0.97 | 0.53 | -0.29 | -972 | 3255 | -4573 | -972 |  |
| id_9_16_L_no_fri | 477 | -1143 | 0.98 | 0.52 | -0.16 | 223 | 3755 | -5120 | 223 |  |
| id_9_16_L_vix_lt | 468 | -4698 | 0.90 | 0.52 | -0.74 | -1091 | 2053 | -5660 | -1091 |  |
| id_9_16_L_vix_ge | 126 | 2408 | 1.14 | 0.55 | 0.52 | 119 | 1202 | 1087 | 119 |  |
| id_9_16_S_all | 594 | -1559 | 0.98 | 0.46 | -0.20 | -304 | -4557 | 3303 | -304 |  |
| id_9_16_S_no_fri | 477 | -1948 | 0.96 | 0.46 | -0.28 | -1233 | -4799 | 4084 | -1233 |  |
| id_9_16_S_vix_lt | 468 | 1666 | 1.04 | 0.46 | 0.26 | -23 | -2993 | 4682 | -23 |  |
| id_9_16_S_vix_ge | 126 | -3224 | 0.84 | 0.44 | -0.69 | -281 | -1564 | -1379 | -281 |  |

## BASKET

Selected on fold 1: `{'session': 'on_16_9', 'side': 1, 'filt': 'all'}`  
**OOS folds 2+3**: n=1592 net= 38367.93 pf=1.23 wr=0.56 sharpe=2.55 dd=13003 folds=[0, 13664, 24704]

In-sample grid (fold1 = selection set; f1/f2/f3 = net per calendar third, full period):

| variant | n | net | pf | wr | sharpe | f1 | f2 | f3 | fold1_net | sel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| on_16_9_L_all | 2373 | 60456 | 1.29 | 0.57 | 3.76 | 22089 | 13664 | 24704 | 22089 | * |
| on_16_9_L_no_fri | 1905 | 35620 | 1.22 | 0.56 | 2.57 | 21104 | 979 | 13537 | 21104 |  |
| on_16_9_L_vix_lt | 1869 | 53366 | 1.37 | 0.58 | 4.01 | 17497 | 16263 | 19606 | 17497 |  |
| on_16_9_L_vix_ge | 504 | 7090 | 1.11 | 0.53 | 0.78 | 4591 | -2598 | 5097 | 4591 |  |
| on_16_9_S_all | 2373 | -74055 | 0.73 | 0.41 | -4.60 | -26564 | -18294 | -29196 | -26564 |  |
| on_16_9_S_no_fri | 1905 | -46537 | 0.77 | 0.42 | -3.35 | -24640 | -4693 | -17204 | -24640 |  |
| on_16_9_S_vix_lt | 1869 | -64076 | 0.69 | 0.40 | -4.82 | -21400 | -19609 | -23067 | -21400 |  |
| on_16_9_S_vix_ge | 504 | -9978 | 0.86 | 0.46 | -1.10 | -5164 | 1315 | -6129 | -5164 |  |
| on_18_9_L_all | 2372 | 49711 | 1.26 | 0.57 | 3.38 | 14930 | 9630 | 25151 | 14930 |  |
| on_18_9_L_no_fri | 2372 | 49711 | 1.26 | 0.57 | 3.38 | 14930 | 9630 | 25151 | 14930 |  |
| on_18_9_L_vix_lt | 1857 | 37240 | 1.30 | 0.58 | 3.27 | 13019 | 4734 | 19487 | 13019 |  |
| on_18_9_L_vix_ge | 515 | 12471 | 1.19 | 0.54 | 1.34 | 1911 | 4896 | 5664 | 1911 |  |
| on_18_9_S_all | 2372 | -63303 | 0.75 | 0.41 | -4.30 | -19423 | -14214 | -29666 | -19423 |  |
| on_18_9_S_no_fri | 2372 | -63303 | 0.75 | 0.41 | -4.30 | -19423 | -14214 | -29666 | -19423 |  |
| on_18_9_S_vix_lt | 1857 | -47882 | 0.72 | 0.40 | -4.20 | -16938 | -7989 | -22954 | -16938 |  |
| on_18_9_S_vix_ge | 515 | -15421 | 0.81 | 0.46 | -1.65 | -2484 | -6225 | -6712 | -2484 |  |
| id_9_16_L_all | 2373 | -7256 | 0.97 | 0.53 | -0.45 | -8884 | 7160 | -5532 | -8884 |  |
| id_9_16_L_no_fri | 1905 | -3217 | 0.98 | 0.52 | -0.22 | -9610 | 11745 | -5352 | -9610 |  |
| id_9_16_L_vix_lt | 1869 | -36634 | 0.81 | 0.51 | -2.97 | -15707 | -4006 | -16921 | -15707 |  |
| id_9_16_L_vix_ge | 504 | 29379 | 1.50 | 0.60 | 2.90 | 6823 | 11166 | 11389 | 6823 |  |
| id_9_16_S_all | 2373 | -6343 | 0.98 | 0.46 | -0.40 | 4385 | -11767 | 1040 | 4385 |  |
| id_9_16_S_no_fri | 1905 | -7699 | 0.96 | 0.47 | -0.53 | 6051 | -15435 | 1685 | 6051 |  |
| id_9_16_S_vix_lt | 1869 | 25924 | 1.16 | 0.48 | 2.10 | 11781 | 682 | 13460 | 11781 |  |
| id_9_16_S_vix_ge | 504 | -32266 | 0.64 | 0.40 | -3.19 | -7396 | -12449 | -12421 | -7396 |  |

## Sanity checks

### BASKET: `on_16_9_L_all`

- Shuffle (a): actual OOS net **38368** beats 67% of 21 random-hour windows (same hold length, same side/filter); random-hour mean 31596, best 46156 @ e_in=2. Sign-permutation p=0.002 (500 draws).
- Sub-period (b): OOS folds = [13664, 24704], n per fold [808, 784]
- Neighbours (c), OOS period only:

| variant | n | net | pf | folds2,3 |
|---|---:|---:|---:|---|
| e_in=15 e_out=9 | 1592 | 38310 | 1.22 | [14054, 24256] |
| e_in=16 e_out=8 | 1588 | 38731 | 1.26 | [13166, 25565] |
| e_in=16 e_out=10 | 1592 | 36378 | 1.19 | [11364, 25013] |
| filt=no_fri | 1288 | 14517 | 1.11 | [979, 13537] |
| filt=vix_lt | 1188 | 35869 | 1.33 | [16263, 19606] |
| filt=vix_ge | 404 | 2499 | 1.04 | [-2598, 5097] |

### MNQ: `on_16_9_L_all`

- Shuffle (a): actual OOS net **13428** beats 67% of 21 random-hour windows (same hold length, same side/filter); random-hour mean 11766, best 17652 @ e_in=2. Sign-permutation p=0.046 (500 draws).
- Sub-period (b): OOS folds = [4452, 8976], n per fold [202, 196]
- Neighbours (c), OOS period only:

| variant | n | net | pf | folds2,3 |
|---|---:|---:|---:|---|
| e_in=15 e_out=9 | 398 | 11694 | 1.20 | [3690, 8004] |
| e_in=16 e_out=8 | 397 | 13656 | 1.26 | [4692, 8964] |
| e_in=16 e_out=10 | 398 | 10907 | 1.16 | [3654, 7254] |
| filt=no_fri | 322 | 5327 | 1.12 | [629, 4698] |
| filt=vix_lt | 297 | 11362 | 1.30 | [5853, 5508] |
| filt=vix_ge | 101 | 2066 | 1.11 | [-1402, 3468] |

### MES: `on_16_9_L_all`

- Shuffle (a): actual OOS net **3319** beats 24% of 21 random-hour windows (same hold length, same side/filter); random-hour mean 5579, best 10737 @ e_in=2. Sign-permutation p=0.138 (500 draws).
- Sub-period (b): OOS folds = [698, 2621], n per fold [202, 196]
- Neighbours (c), OOS period only:

| variant | n | net | pf | folds2,3 |
|---|---:|---:|---:|---|
| e_in=15 e_out=9 | 398 | 2608 | 1.09 | [728, 1879] |
| e_in=16 e_out=8 | 397 | 3185 | 1.13 | [300, 2886] |
| e_in=16 e_out=10 | 398 | 4585 | 1.15 | [571, 4014] |
| filt=no_fri | 322 | -368 | 0.98 | [-1206, 838] |
| filt=vix_lt | 297 | 2879 | 1.17 | [1743, 1137] |
| filt=vix_ge | 101 | 440 | 1.04 | [-1044, 1484] |

### MYM: `on_16_9_L_all`

- Shuffle (a): actual OOS net **594** beats 24% of 21 random-hour windows (same hold length, same side/filter); random-hour mean 3557, best 8292 @ e_in=2. Sign-permutation p=0.298 (500 draws).
- Sub-period (b): OOS folds = [-942, 1536], n per fold [202, 196]
- Neighbours (c), OOS period only:

| variant | n | net | pf | folds2,3 |
|---|---:|---:|---:|---|
| e_in=15 e_out=9 | 398 | -159 | 0.99 | [-1366, 1208] |
| e_in=16 e_out=8 | 397 | 839 | 1.05 | [-824, 1663] |
| e_in=16 e_out=10 | 398 | 2111 | 1.10 | [-1160, 3272] |
| filt=no_fri | 322 | -1538 | 0.90 | [-2144, 607] |
| filt=vix_lt | 297 | 1199 | 1.11 | [252, 947] |
| filt=vix_ge | 101 | -605 | 0.92 | [-1194, 590] |

### MGC: `on_16_9_L_no_fri`

- Shuffle (a): actual OOS net **11096** beats 62% of 21 random-hour windows (same hold length, same side/filter); random-hour mean 8677, best 15579 @ e_in=18. Sign-permutation p=0.114 (500 draws).
- Sub-period (b): OOS folds = [3701, 7395], n per fold [162, 160]
- Neighbours (c), OOS period only:

| variant | n | net | pf | folds2,3 |
|---|---:|---:|---:|---|
| e_in=15 e_out=9 | 322 | 14434 | 1.28 | [4752, 9682] |
| e_in=16 e_out=8 | 321 | 11741 | 1.25 | [3334, 8407] |
| e_in=16 e_out=10 | 322 | 10742 | 1.19 | [2838, 7904] |
| filt=all | 398 | 21026 | 1.34 | [9457, 11570] |
| filt=vix_lt | 297 | 20429 | 1.49 | [8414, 12015] |
| filt=vix_ge | 101 | 598 | 1.03 | [1043, -445] |

## 5m exact 16:00->09:30 check (last ~70 days, descriptive, no folds)

| inst | n | on_16:00->09:30 net | pf | id_09:30->16:00 net | pf |
|---|---:|---:|---:|---:|---:|
| MNQ | 49 | 2295 | 1.21 | -4186 | 0.68 |
| MES | 49 | 1410 | 1.47 | -1053 | 0.75 |
| MYM | 49 | 1382 | 1.68 | -1012 | 0.62 |
| MGC | 49 | 1907 | 1.20 | 846 | 1.15 |

## Asymmetry test (OOS period): overnight minus intraday, paired by date

| inst | pairs | on_gross | id_gross | buy&hold gross | on/bh | on mean | id mean | t(on-id) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MNQ | 392 | 14320 | 958 | 15788 | 0.91 | 36.0 | 2.4 | 0.94 | 0.347 |
| MES | 392 | 4808 | 2806 | 8256 | 0.58 | 12.1 | 7.1 | 0.27 | 0.791 |
| MYM | 392 | 1486 | 2446 | 4724 | 0.31 | 3.7 | 6.2 | -0.24 | 0.811 |
| MGC | 392 | 22316 | -32 | 18732 | 1.19 | 56.1 | -0.1 | 2.15 | 0.032 |

- MNQ hour-of-day gross sum (ET bar-open hour, OOS): 0:-1181, 1:904, 2:2662, 3:3797, 4:1452, 5:664, 6:538, 7:-880, 8:1292, 9:-2172, 10:148, 11:1354, 12:822, 13:5881, 14:-1097, 15:-912, 16:2846, 18:3342, 19:2900, 20:2126, 21:-266, 22:-3474, 23:-623
- MES hour-of-day gross sum (ET bar-open hour, OOS): 0:-936, 1:559, 2:589, 3:1630, 4:431, 5:498, 6:671, 7:784, 8:259, 9:1249, 10:930, 11:-475, 12:875, 13:2556, 14:-480, 15:-388, 16:456, 18:1475, 19:954, 20:1164, 21:778, 22:-1298, 23:-335
- MYM hour-of-day gross sum (ET bar-open hour, OOS): 0:-702, 1:-147, 2:255, 3:944, 4:-25, 5:254, 6:646, 7:-82, 8:-179, 9:1844, 10:2163, 11:-988, 12:-214, 13:1549, 14:1111, 15:-697, 16:-60, 18:774, 19:74, 20:570, 21:259, 22:-614, 23:-462
- MGC hour-of-day gross sum (ET bar-open hour, OOS): 0:1436, 1:-3679, 2:4921, 3:-169, 4:-2660, 5:-2057, 6:-809, 7:5209, 8:-264, 9:-2700, 10:-16, 11:2118, 12:-2081, 13:-6, 14:-3656, 15:2651, 16:920, 18:4936, 19:950, 20:4180, 21:-1999, 22:-2215, 23:1013

## OOS summary

| universe | selected | OOS n | OOS net | pf | wr | sharpe | fold2 | fold3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| MNQ | on_16_9_L_all | 398 | 13428 | 1.24 | 0.57 | 1.51 | 4452 | 8976 |
| MES | on_16_9_L_all | 398 | 3319 | 1.12 | 0.57 | 0.79 | 698 | 2621 |
| MYM | on_16_9_L_all | 398 | 594 | 1.03 | 0.51 | 0.21 | -942 | 1536 |
| MGC | on_16_9_L_no_fri | 322 | 11096 | 1.22 | 0.59 | 1.11 | 3701 | 7395 |
| BASKET | on_16_9_L_all | 1592 | 38368 | 1.23 | 0.56 | 2.55 | 13664 | 24704 |

## Interpretation

- Walk-forward picks long overnight 16:00->09:00 ET on fold 1 for every universe. OOS (2025-01-21 -> 2026-08-27)
  basket net +38.4k USD on 1 contract each (PF 1.23, WR 0.56, both OOS folds positive); MNQ +13.4k, MGC +11.1k,
  MES +3.3k, MYM +0.6k (MYM fold 2 negative).
- **It does not survive the shuffle test.** Random 17-hour windows with the same hold length earn comparable or
  larger OOS net (basket: the overnight window beats only 67% of 21 random-hour windows; MES/MYM only 24%).
  The PnL is market beta from a strongly up-trending sample, not a time-of-day effect.
- The direct paired test of the hypothesis (overnight minus intraday gross, same date, OOS) is insignificant
  for the equity micros: MNQ t=0.94 p=0.35, MES t=0.27 p=0.79, MYM t=-0.24 p=0.81. Overnight captured 91% /
  58% / 31% of buy-and-hold for MNQ / MES / MYM, i.e. roughly pro-rata to time held. Only MGC shows a real
  asymmetry (t=2.15 p=0.03; overnight = 119% of buy-and-hold, intraday ~0) - one significant result out of four
  instruments, borderline after multiple comparisons, and MGC's gross is concentrated in Asia/London hours
  (02, 07, 18, 20 ET), not at the US cash-close/open transition.
- Short-intraday (the tradable "reverse") loses money OOS on the basket (id_9_16_S_all folds -11.8k / +1.0k).
  VIX>=20 intraday-long / VIX<20 intraday-short look good in-sample but are opposite-signed regime bets with
  n=100-500 and were not selected; treat as noise.
- Neighbours (+-1h entry/exit) are stable, as expected for a beta exposure; the no_fri filter (drop weekend
  holds) *hurts* on equities, meaning the weekend carry was a large part of the OOS PnL.
- The 5m exact 16:00->09:30 check on the last 70 days agrees in sign (overnight positive, intraday negative for
  the equity micros) but is 49 trades and descriptive only.

Verdict: weak (positive, fold-consistent OOS net but fails the shuffle check; the effect is beta, not timing).
Do not deploy as a standalone strategy.
