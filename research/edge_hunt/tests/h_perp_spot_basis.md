# perp_spot_basis results
Period 2026-01-31 -> 2026-08-27, 50 coins, notional $1000/trade, lookback 168h, funding included in PnL, fold edges = calendar thirds.
Folds: F1 2026-01-31->2026-04-10, F2 2026-04-10->2026-06-19, F3 2026-06-19->2026-08-27

## premium_taker

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 4098 | -3499.2 | 0.88 | 0.48 | 9383 | -12720.4 | 0.83 | -5654.7 | -7065.8 |  |
| z1.5_h8 | 2965 | -394.6 | 0.99 | 0.50 | 6659 | -9305.6 | 0.87 | -3426.5 | -5879.1 |  |
| z1.5_h12 | 2430 | 773.4 | 1.03 | 0.50 | 5388 | -8228.0 | 0.88 | -1629.9 | -6598.2 |  |
| z1.5_h24 | 1622 | 3637.6 | 1.13 | 0.52 | 3619 | -3915.0 | 0.94 | 1518.2 | -5433.1 | * |
| z2.0_h4 | 2056 | -951.6 | 0.94 | 0.49 | 5062 | -7100.4 | 0.84 | -3182.3 | -3918.2 |  |
| z2.0_h8 | 1605 | 52.3 | 1.00 | 0.51 | 3810 | -7704.5 | 0.83 | -2299.1 | -5405.3 |  |
| z2.0_h12 | 1394 | 566.1 | 1.03 | 0.49 | 3189 | -5312.1 | 0.88 | -1363.3 | -3948.8 |  |
| z2.0_h24 | 1039 | 2143.2 | 1.11 | 0.51 | 2342 | -6544.4 | 0.86 | 42.5 | -6586.8 |  |
| z2.5_h4 | 994 | -665.9 | 0.92 | 0.48 | 2810 | -3407.8 | 0.87 | -1344.6 | -2063.2 |  |
| z2.5_h8 | 820 | 370.3 | 1.04 | 0.49 | 2213 | -3630.4 | 0.87 | -1632.9 | -1997.6 |  |
| z2.5_h12 | 735 | 67.8 | 1.01 | 0.48 | 1913 | -3127.0 | 0.89 | -782.6 | -2344.4 |  |
| z2.5_h24 | 596 | 50.8 | 1.00 | 0.48 | 1517 | -6326.4 | 0.81 | -527.9 | -5798.5 |  |
| z3.0_h4 | 488 | -227.4 | 0.95 | 0.49 | 1566 | -1512.3 | 0.90 | -986.8 | -525.4 |  |
| z3.0_h8 | 420 | 881.9 | 1.20 | 0.51 | 1302 | -2324.4 | 0.87 | -1664.3 | -660.1 |  |
| z3.0_h12 | 389 | 799.3 | 1.17 | 0.51 | 1151 | -1506.1 | 0.92 | -1001.2 | -504.8 |  |
| z3.0_h24 | 333 | 641.8 | 1.10 | 0.48 | 946 | -3436.7 | 0.84 | -213.2 | -3223.4 |  |

**Walk-forward pick z1.5_h24 -> OOS** n=3619 net=-3914.96 pf=0.94 wr=0.50 sh=-1.18 bps=-10.8 folds=[0.0, 1518.2, -5433.1]  gross=-653.3 fees=3261.6 maxdd=7891.1 hold=24h

Neighbors OOS net: z1.5_h12=-8228.0, z2.0_h12=-5312.1, z2.0_h24=-6544.4 -> 0/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=-3915.0, null mean=-3601.3 sd=3067.7, p(null>=real)=0.560

OOS by side: side -1: n=1838 net=-6630.9; side 1: n=1781 net=2716.0

OOS funding component: 966.4 USD of net -3915.0

OOS liquid (>= $5M/24h, 34 coins): n=2531 net=-4566.09 pf=0.90 wr=0.50 sh=-1.66 bps=-18.0 folds=[0.0, -1737.2, -2828.9]

OOS illiquid (< $5M/24h, 16 coins): n=1088 net=  651.13 pf=1.04 wr=0.49 sh=0.35 bps=6.0 folds=[0.0, 3255.3, -2604.2]

OOS per coin (net USD): NEAR=-1252(78), TRUMP=-845(75), VVV=-774(70), ZEC=-683(81), ADA*=-677(93), PENGU=-606(89), WLD=-602(75), CHIP=-578(49), FET*=-569(59), XRP=-537(78), PUMP=-522(70), CRV=-511(66), kPEPE=-370(79), SUI=-346(75), DOGE=-303(68), ENA=-273(83), JUP=-260(88), GRASS*=-247(70), FARTCOIN=-240(75), INJ*=-210(73), BTC=-207(77), LTC*=-182(71), XMR=-168(75), TRX*=-127(76), PAXG*=-125(72), SOL=-123(73), BNB=-106(81), GRAM*=-98(25), ETH=-75(83), AERO*=-70(81), AAVE=-31(85), TAO=78(78), MON=111(75), CC*=202(81), WIF*=211(68), PURR*=232(63), ONDO=250(80), XPL=277(79), ASTER*=299(70), SPX=320(65), UNI=322(72), ETHFI*=332(68), CASHCAT=368(22), AVAX=373(76), HEMI*=426(56), HYPE=450(79), ZRO=459(78), LINK=630(78), LIT=1208(76), JTO*=1256(62)  (* = illiquid)

## premium_maker_entry

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 3991 | -4394.8 | 0.85 | 0.47 | 9156 | -13843.2 | 0.81 | -6599.1 | -7244.1 |  |
| z1.5_h8 | 2903 | -844.2 | 0.97 | 0.50 | 6521 | -9949.7 | 0.86 | -3903.7 | -6046.1 |  |
| z1.5_h12 | 2380 | 284.7 | 1.01 | 0.50 | 5268 | -9030.6 | 0.87 | -2156.7 | -6873.9 |  |
| z1.5_h24 | 1599 | 3307.9 | 1.12 | 0.51 | 3562 | -3919.1 | 0.94 | 1201.0 | -5120.1 | * |
| z2.0_h4 | 1989 | -2130.2 | 0.86 | 0.48 | 4912 | -7664.6 | 0.82 | -3615.7 | -4048.9 |  |
| z2.0_h8 | 1556 | -699.2 | 0.96 | 0.50 | 3715 | -8551.6 | 0.81 | -3250.7 | -5300.9 |  |
| z2.0_h12 | 1352 | 121.9 | 1.01 | 0.49 | 3112 | -5430.9 | 0.88 | -1819.2 | -3611.8 |  |
| z2.0_h24 | 1014 | 1659.3 | 1.09 | 0.50 | 2299 | -7004.5 | 0.85 | -154.1 | -6850.4 |  |
| z2.5_h4 | 962 | -999.9 | 0.87 | 0.48 | 2720 | -3865.9 | 0.85 | -1859.3 | -2006.6 |  |
| z2.5_h8 | 797 | 291.2 | 1.03 | 0.49 | 2155 | -4218.0 | 0.85 | -2320.6 | -1897.3 |  |
| z2.5_h12 | 715 | -110.3 | 0.99 | 0.47 | 1865 | -3465.1 | 0.88 | -1298.1 | -2167.0 |  |
| z2.5_h24 | 583 | 173.1 | 1.02 | 0.48 | 1482 | -6507.9 | 0.80 | -728.9 | -5779.0 |  |
| z3.0_h4 | 474 | -322.3 | 0.92 | 0.48 | 1516 | -1634.8 | 0.89 | -1219.6 | -415.1 |  |
| z3.0_h8 | 410 | 932.9 | 1.22 | 0.51 | 1260 | -2261.3 | 0.87 | -1936.2 | -325.1 |  |
| z3.0_h12 | 380 | 833.4 | 1.18 | 0.50 | 1114 | -1753.3 | 0.90 | -1415.6 | -337.7 |  |
| z3.0_h24 | 325 | 386.5 | 1.06 | 0.47 | 921 | -3550.3 | 0.83 | -539.9 | -3010.3 |  |

**Walk-forward pick z1.5_h24 -> OOS** n=3562 net=-3919.11 pf=0.94 wr=0.50 sh=-1.18 bps=-11.0 folds=[0.0, 1201.0, -5120.1]  gross=-1777.4 fees=2141.7 maxdd=7605.5 hold=24h

Neighbors OOS net: z1.5_h12=-9030.6, z2.0_h12=-5430.9, z2.0_h24=-7004.5 -> 0/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=-3919.1, null mean=-2915.5 sd=3036.7, p(null>=real)=0.620

OOS by side: side -1: n=1809 net=-6631.6; side 1: n=1753 net=2712.5

OOS funding component: 958.9 USD of net -3919.1

OOS liquid (>= $5M/24h, 34 coins): n=2499 net=-4568.61 pf=0.90 wr=0.50 sh=-1.66 bps=-18.3 folds=[0.0, -1943.1, -2625.5]

OOS illiquid (< $5M/24h, 16 coins): n=1063 net=  649.50 pf=1.04 wr=0.49 sh=0.35 bps=6.1 folds=[0.0, 3144.1, -2494.6]

OOS per coin (net USD): NEAR=-1255(78), TRUMP=-859(75), VVV=-798(70), ZEC=-699(79), ADA*=-656(93), CHIP=-616(48), PENGU=-603(87), WLD=-572(75), PUMP=-562(68), XRP=-523(77), FET*=-502(59), CRV=-483(66), kPEPE=-354(78), FARTCOIN=-354(74), SUI=-317(75), DOGE=-263(68), ENA=-258(79), BTC=-223(76), LTC*=-222(70), XMR=-203(74), INJ*=-186(73), GRASS*=-160(70), TRX*=-124(74), BNB=-112(79), JUP=-106(87), GRAM*=-91(24), SOL=-80(71), PAXG*=-72(67), AERO*=-71(77), ETH=-55(82), AAVE=52(84), TAO=111(78), MON=155(75), HEMI*=219(55), CC*=233(80), AVAX=235(74), ONDO=235(79), WIF*=259(68), PURR*=275(56), ETHFI*=279(67), ASTER*=288(68), XPL=293(78), UNI=310(70), CASHCAT=377(22), SPX=382(65), HYPE=431(78), ZRO=518(77), LINK=572(77), LIT=1056(76), JTO*=1180(62)  (* = illiquid)

## premium_maker_both

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 3973 | -4242.4 | 0.86 | 0.47 | 9111 | -15132.3 | 0.79 | -7327.6 | -7804.7 |  |
| z1.5_h8 | 2897 | -1312.9 | 0.96 | 0.49 | 6508 | -11359.5 | 0.84 | -4311.7 | -7047.8 |  |
| z1.5_h12 | 2375 | 256.7 | 1.01 | 0.50 | 5252 | -10248.1 | 0.85 | -2988.2 | -7259.9 |  |
| z1.5_h24 | 1598 | 3367.3 | 1.12 | 0.51 | 3555 | -4114.5 | 0.94 | 989.8 | -5104.3 | * |
| z2.0_h4 | 1978 | -2430.5 | 0.85 | 0.47 | 4897 | -8372.1 | 0.81 | -3815.7 | -4556.4 |  |
| z2.0_h8 | 1553 | -804.5 | 0.95 | 0.49 | 3702 | -9425.9 | 0.79 | -3786.3 | -5639.6 |  |
| z2.0_h12 | 1349 | 48.3 | 1.00 | 0.49 | 3107 | -6172.5 | 0.86 | -2405.6 | -3766.9 |  |
| z2.0_h24 | 1014 | 1489.9 | 1.08 | 0.50 | 2299 | -7114.7 | 0.85 | -251.7 | -6863.0 |  |
| z2.5_h4 | 959 | -1276.2 | 0.84 | 0.47 | 2706 | -4651.1 | 0.82 | -2246.4 | -2404.7 |  |
| z2.5_h8 | 795 | 157.0 | 1.02 | 0.48 | 2146 | -4878.9 | 0.83 | -2695.8 | -2183.1 |  |
| z2.5_h12 | 715 | -284.7 | 0.97 | 0.47 | 1863 | -3980.0 | 0.86 | -1415.8 | -2564.1 |  |
| z2.5_h24 | 583 | 97.6 | 1.01 | 0.48 | 1480 | -6618.7 | 0.80 | -676.7 | -5942.0 |  |
| z3.0_h4 | 473 | -481.5 | 0.89 | 0.48 | 1511 | -2083.6 | 0.86 | -1393.1 | -690.4 |  |
| z3.0_h8 | 408 | 802.2 | 1.18 | 0.50 | 1258 | -2413.4 | 0.86 | -2032.0 | -381.4 |  |
| z3.0_h12 | 380 | 711.3 | 1.15 | 0.49 | 1113 | -2024.3 | 0.88 | -1430.6 | -593.7 |  |
| z3.0_h24 | 325 | 302.5 | 1.05 | 0.47 | 920 | -3617.6 | 0.83 | -584.5 | -3033.1 |  |

**Walk-forward pick z1.5_h24 -> OOS** n=3555 net=-4114.53 pf=0.94 wr=0.50 sh=-1.24 bps=-11.6 folds=[0.0, 989.8, -5104.3]  gross=-2987.5 fees=1127.0 maxdd=7746.7 hold=24h

Neighbors OOS net: z1.5_h12=-10248.1, z2.0_h12=-6172.5, z2.0_h24=-7114.7 -> 0/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=-4114.5, null mean=-1458.4 sd=2834.0, p(null>=real)=0.835

OOS by side: side -1: n=1806 net=-6781.2; side 1: n=1749 net=2666.7

OOS funding component: 959.8 USD of net -4114.5

OOS liquid (>= $5M/24h, 34 coins): n=2492 net=-4626.23 pf=0.90 wr=0.50 sh=-1.68 bps=-18.6 folds=[0.0, -2041.2, -2585.1]

OOS illiquid (< $5M/24h, 16 coins): n=1063 net=  511.70 pf=1.03 wr=0.49 sh=0.28 bps=4.8 folds=[0.0, 3031.0, -2519.3]

OOS per coin (net USD): NEAR=-1214(78), TRUMP=-872(74), VVV=-783(70), CHIP=-733(48), ZEC=-690(77), ADA*=-681(93), PENGU=-657(86), WLD=-575(74), PUMP=-558(68), FET*=-548(59), XRP=-542(77), CRV=-484(66), FARTCOIN=-353(74), kPEPE=-350(77), SUI=-305(75), XMR=-250(74), DOGE=-246(68), ENA=-246(79), LTC*=-229(70), BTC=-208(76), GRASS*=-198(70), INJ*=-152(73), TRX*=-111(74), BNB=-93(79), GRAM*=-93(24), SOL=-75(71), ETH=-64(82), AERO*=-60(77), PAXG*=-52(67), JUP=-34(86), AAVE=69(84), TAO=103(78), MON=124(75), HEMI*=166(55), ONDO=225(79), AVAX=243(74), PURR*=251(56), CC*=252(80), ETHFI*=256(67), XPL=269(78), WIF*=281(68), ASTER*=287(68), UNI=306(70), SPX=372(65), CASHCAT=386(22), HYPE=443(78), ZRO=510(77), LINK=583(77), LIT=1071(76), JTO*=1142(62)  (* = illiquid)

## basis_taker

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 210 | -439.6 | 0.65 | 0.42 | 481 | -352.4 | 0.81 | -310.6 | -41.8 |  |
| z1.5_h8 | 162 | -515.6 | 0.61 | 0.41 | 333 | -69.7 | 0.96 | -169.8 | 100.1 |  |
| z1.5_h12 | 127 | -238.8 | 0.80 | 0.50 | 256 | 141.2 | 1.09 | -192.0 | 333.2 |  |
| z1.5_h24 | 87 | -209.6 | 0.82 | 0.46 | 169 | 201.7 | 1.15 | -72.2 | 273.9 |  |
| z2.0_h4 | 110 | -458.1 | 0.42 | 0.35 | 260 | 9.3 | 1.01 | -80.6 | 89.9 |  |
| z2.0_h8 | 88 | -696.1 | 0.27 | 0.32 | 203 | 38.8 | 1.04 | -147.9 | 186.7 |  |
| z2.0_h12 | 78 | -683.6 | 0.33 | 0.33 | 166 | 382.3 | 1.40 | 109.9 | 272.3 |  |
| z2.0_h24 | 62 | -767.2 | 0.37 | 0.37 | 128 | 237.9 | 1.25 | 34.1 | 203.8 |  |
| z2.5_h4 | 71 | -292.7 | 0.38 | 0.38 | 124 | -267.4 | 0.59 | -106.2 | -161.2 |  |
| z2.5_h8 | 64 | -421.5 | 0.33 | 0.33 | 108 | -132.1 | 0.79 | -105.7 | -26.4 |  |
| z2.5_h12 | 59 | -481.3 | 0.34 | 0.36 | 99 | 133.3 | 1.21 | 46.3 | 87.0 |  |
| z2.5_h24 | 47 | -241.5 | 0.64 | 0.40 | 79 | 146.8 | 1.21 | -54.9 | 201.7 |  |
| z3.0_h4 | 36 | -75.9 | 0.54 | 0.42 | 51 | 40.5 | 1.19 | -26.7 | 67.3 |  |
| z3.0_h8 | 36 | -148.5 | 0.51 | 0.42 | 46 | 47.3 | 1.18 | -19.2 | 66.5 |  |
| z3.0_h12 | 36 | -218.7 | 0.41 | 0.39 | 42 | 58.4 | 1.19 | -33.5 | 92.0 |  |
| z3.0_h24 | 29 | 104.4 | 1.37 | 0.48 | 36 | 94.7 | 1.25 | -49.6 | 144.4 | * |

**Walk-forward pick z3.0_h24 -> OOS** n=  36 net=   94.74 pf=1.25 wr=0.44 sh=0.46 bps=26.3 folds=[0.0, -49.6, 144.4]  gross=127.3 fees=32.5 maxdd=195.3 hold=24h

Neighbors OOS net: z2.5_h12=133.3, z2.5_h24=146.8, z3.0_h12=58.4 -> 3/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=94.7, null mean=-61.3 sd=144.4, p(null>=real)=0.160

OOS by side: side -1: n=23 net=-85.5; side 1: n=13 net=180.2

OOS funding component: 2.5 USD of net 94.7

OOS per coin (net USD): BTC=-12(17), ETH=107(19)  (* = illiquid)

## basis_maker_entry

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 206 | -401.6 | 0.67 | 0.42 | 471 | -224.4 | 0.87 | -228.8 | 4.4 |  |
| z1.5_h8 | 157 | -442.3 | 0.65 | 0.41 | 327 | -49.3 | 0.97 | -221.5 | 172.3 |  |
| z1.5_h12 | 125 | -313.0 | 0.74 | 0.49 | 250 | 133.6 | 1.08 | -225.2 | 358.7 |  |
| z1.5_h24 | 86 | -351.0 | 0.70 | 0.45 | 167 | 104.2 | 1.07 | -183.4 | 287.6 |  |
| z2.0_h4 | 109 | -415.4 | 0.45 | 0.36 | 256 | 59.0 | 1.06 | -62.2 | 121.3 |  |
| z2.0_h8 | 87 | -669.5 | 0.28 | 0.32 | 198 | 56.8 | 1.06 | -166.2 | 223.1 |  |
| z2.0_h12 | 77 | -674.7 | 0.32 | 0.34 | 164 | 398.1 | 1.43 | 94.7 | 303.4 |  |
| z2.0_h24 | 62 | -750.1 | 0.38 | 0.37 | 127 | 249.2 | 1.26 | 23.5 | 225.7 |  |
| z2.5_h4 | 69 | -248.4 | 0.44 | 0.41 | 118 | -263.0 | 0.58 | -113.8 | -149.2 |  |
| z2.5_h8 | 62 | -405.4 | 0.34 | 0.31 | 103 | -95.9 | 0.84 | -91.2 | -4.7 |  |
| z2.5_h12 | 57 | -484.6 | 0.32 | 0.37 | 96 | 128.3 | 1.21 | 21.5 | 106.8 |  |
| z2.5_h24 | 45 | -319.0 | 0.52 | 0.38 | 78 | 167.6 | 1.25 | -48.7 | 216.2 |  |
| z3.0_h4 | 34 | -45.6 | 0.68 | 0.47 | 48 | 56.4 | 1.28 | -20.3 | 76.7 |  |
| z3.0_h8 | 34 | -143.6 | 0.51 | 0.38 | 43 | 72.9 | 1.31 | -3.5 | 76.4 |  |
| z3.0_h12 | 34 | -231.1 | 0.37 | 0.38 | 40 | 76.8 | 1.26 | -26.2 | 103.1 |  |
| z3.0_h24 | 27 | 19.6 | 1.07 | 0.44 | 35 | 117.0 | 1.33 | -35.0 | 152.0 | * |

**Walk-forward pick z3.0_h24 -> OOS** n=  35 net=  116.97 pf=1.33 wr=0.49 sh=0.57 bps=33.4 folds=[0.0, -35.0, 152.0]  gross=138.1 fees=21.1 maxdd=189.7 hold=24h

Neighbors OOS net: z2.5_h12=128.3, z2.5_h24=167.6, z3.0_h12=76.8 -> 3/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=117.0, null mean=-31.1 sd=144.8, p(null>=real)=0.150

OOS by side: side -1: n=22 net=-68.4; side 1: n=13 net=185.4

OOS funding component: 2.2 USD of net 117.0

OOS per coin (net USD): BTC=3(16), ETH=114(19)  (* = illiquid)

## premium_btceth_taker

In-sample grid (fold 1) + OOS (folds 2+3) net for every cell:

| params | IS n | IS net | IS pf | IS wr | OOS n | OOS net | OOS pf | OOS f2 | OOS f3 | sel |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|
| z1.5_h4 | 162 | -186.6 | 0.75 | 0.44 | 450 | -306.7 | 0.82 | -65.3 | -241.5 |  |
| z1.5_h8 | 114 | 104.8 | 1.17 | 0.50 | 317 | -27.4 | 0.98 | -12.2 | -15.2 |  |
| z1.5_h12 | 98 | 71.1 | 1.11 | 0.54 | 256 | -159.6 | 0.91 | 49.9 | -209.5 |  |
| z1.5_h24 | 65 | 351.9 | 1.53 | 0.65 | 160 | -282.6 | 0.82 | -158.9 | -123.7 | * |
| z2.0_h4 | 85 | -57.8 | 0.86 | 0.45 | 227 | -128.8 | 0.85 | -98.7 | -30.1 |  |
| z2.0_h8 | 66 | 38.9 | 1.10 | 0.55 | 174 | -96.8 | 0.90 | -115.8 | 18.9 |  |
| z2.0_h12 | 59 | -3.1 | 0.99 | 0.54 | 147 | -3.6 | 1.00 | -72.9 | 69.2 |  |
| z2.0_h24 | 46 | 97.8 | 1.16 | 0.59 | 105 | 38.4 | 1.04 | -56.6 | 95.0 |  |
| z2.5_h4 | 38 | -73.8 | 0.59 | 0.34 | 120 | -14.5 | 0.97 | -22.3 | 7.8 |  |
| z2.5_h8 | 30 | -39.5 | 0.83 | 0.43 | 91 | 191.5 | 1.53 | 45.3 | 146.2 |  |
| z2.5_h12 | 29 | -13.7 | 0.94 | 0.52 | 77 | 38.7 | 1.07 | -69.2 | 108.0 |  |
| z2.5_h24 | 25 | 31.0 | 1.10 | 0.52 | 61 | 251.7 | 1.50 | 98.5 | 153.2 |  |
| z3.0_h4 | 18 | -3.5 | 0.95 | 0.44 | 55 | -18.6 | 0.91 | -22.4 | 3.7 |  |
| z3.0_h8 | 12 | -39.7 | 0.66 | 0.42 | 46 | 31.4 | 1.12 | -26.4 | 57.8 |  |
| z3.0_h12 | 11 | -46.7 | 0.60 | 0.36 | 38 | 0.4 | 1.00 | -42.5 | 42.9 |  |
| z3.0_h24 | 10 | -81.0 | 0.49 | 0.40 | 34 | 122.9 | 1.35 | 132.6 | -9.7 |  |

**Walk-forward pick z1.5_h24 -> OOS** n= 160 net= -282.58 pf=0.82 wr=0.39 sh=-0.82 bps=-17.7 folds=[0.0, -158.9, -123.7]  gross=-138.5 fees=144.1 maxdd=435.9 hold=24h

Neighbors OOS net: z1.5_h12=-159.6, z2.0_h12=-3.6, z2.0_h24=38.4 -> 1/3 positive

Shuffle test (200 random-timing nulls, same coins/sides/holds/count, funding incl.): real=-282.6, null mean=-125.6 sd=286.3, p(null>=real)=0.700

OOS by side: side -1: n=87 net=-226.2; side 1: n=73 net=-56.4

OOS funding component: 16.3 USD of net -282.6

OOS per coin (net USD): BTC=-207(77), ETH=-75(83)  (* = illiquid)

## Interpretation

### Diagnostic: long-only (fade negative premium), premium/taker

WF pick z1.5_h24 -> OOS n=1781 net= 2715.99 pf=1.10 wr=0.48 sh=1.31 bps=15.2 folds=[0.0, 502.9, 2213.1]; shuffle (random long timing, same coins/count/hold): real=2716.0 null=2288.4+-2091.5 p=0.415

## Interpretation

**Verdict: none.** Fading an extreme trailing-7d z-score of the Hyperliquid perp premium (or the
HL-vs-yfinance spot basis) has no fee-adjusted out-of-sample edge on any execution mode.

Headline (premium source, 50-coin basket, taker, walk-forward pick z1.5/h24 on fold 1):
OOS n=3619, net **-3915 USD** (-10.8 bps/trade), PF 0.94, folds F2 +1518 / F3 -5433, Sharpe -1.2.
Maker entry (-3919) and maker both sides (-4115) are no better: the fee saving (~6 bps) is smaller
than the signal's negative gross. Every one of the 16 grid cells is negative OOS in all three
premium/basket modes; 0/3 neighbors of the selected cell are positive.

Why it fails:
1. Funding does not pay for it. Over a 24h hold the collected funding is ~2.7 bps of notional
   (+966 USD on 3.6M traded) vs ~9 bps taker / 3 bps maker round-trip fees.
2. The short side (fade *high* premium) is the loser: OOS shorts -6631 USD vs longs +2716. High
   premium clusters in up-trending tapes (fold 3), where shorts get run over. A short-only version
   is worse, and the sign flip (premium momentum) is also negative net of fees (-6563/-4763/+2155
   per fold for z1.5/h24), i.e. the extreme carries no directional information either way.
3. The long side's profit is beta, not signal: a long-only walk-forward gives OOS +2716 but the
   random-timing null (same coins, counts and holds) averages +2288 +- 2092, p=0.415.
4. Shuffle tests for the full strategy are all null (p=0.56 / 0.62 / 0.84 / 0.70).
5. The illiquid subset (<$5M/24h, 16 coins) is the only positive slice (+651) and it is entirely
   fold 2 (+3255, then -2604 in fold 3): unstable and un-tradeable at size anyway.
6. yfinance basis on BTC/ETH: the WF pick (z3/h24) is +95 USD taker / +117 maker on 36 trades,
   fold 2 negative (-50/-35), shuffle p=0.16, ETH carries all of it. Far below the n>=60 /
   all-folds-positive bar; the basis series from Yahoo's aggregated hourly closes is noisy (corr
   0.29 with HL's own premium) and the "signal" is mostly quote-timing noise.

Next test suggestions (concrete):
- Drop directional perp-only fading. The premium mean-reverts (autocorr 0.96 -> 0.66 at 24h) but
  the tradeable expression is the *basis*, not the perp direction: test a hedged perp-short /
  HL-spot-long carry (HYPE, PURR, BTC, ETH, SOL have HL spot) entered only when the annualised
  funding exceeds round-trip fees on both legs by >2x, held until funding normalises.
- Condition on funding rate *level* instead of premium z-score: enter short only when hourly
  funding > 0.0005 (0.05%/h) so the carry alone covers fees within ~4h; that is a different
  hypothesis (funding harvesting) with a much sparser, higher-quality signal set.
- If keeping an outright fade, require a cross-sectional condition (coin premium z-score high
  while BTC premium is flat) and exit on premium normalisation (z crossing 0) rather than a time
  stop; the time-stop exits here land in trending tapes and dominate the loss.
