# CME weekend gap - BTC

Main data: Binance BTCUSDT 1h 2018-01-01 -> 2026-08-28 (spot proxy, HL taker fees 4.5 bps/side on $10k). Folds: [2018-01-01,2020-11-19), [2020-11-19,2023-10-09), [2023-10-09,2026-08-28)

Gap = close of the Sun 21:00 UTC bar / close of the Fri 20:00 UTC bar - 1 (price at 22:00 Sun vs 21:00 Fri = the CME Fri 16:00 CDT close -> Sun 17:00 CDT reopen window). Entry = OPEN of the Sun 22:00 UTC bar (taker). Fill arm: target = Friday-close level (taker), stop 1.5x|gap| (taker), time-stop 24h/48h. Cont arm: with the weekend move, same stop, time-stop.

Weekends: 451 (per fold [150, 151, 150]); weekday control windows (Tue/Wed/Thu, same 49h geometry): 1354.

|gap| distribution (weekend): median 1.17%, p75 2.84%, p90 5.39%; >0.5%: 320, >1%: 246, >2%: 148. Weekday control median 2.59%.

## (a) Does the gap fill? Fill = Friday-close level touched within N hours of the Sun 22:00 UTC open

**Weekend (Binance, 2018-2026)**

| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |
|---|---:|---:|---:|---:|---:|---:|
| >0% | 448 | 0.34 | 0.43 | 0.57 | 0.67 | 6.0 |
| >0.5% | 318 | 0.18 | 0.28 | 0.45 | 0.56 | 12.0 |
| >1% | 244 | 0.13 | 0.22 | 0.38 | 0.49 | 15.0 |
| >2% | 147 | 0.11 | 0.16 | 0.31 | 0.41 | 15.0 |

**Weekday control Tue/Wed/Thu**

| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |
|---|---:|---:|---:|---:|---:|---:|
| >0% | 1340 | 0.18 | 0.24 | 0.38 | 0.47 | 12.0 |
| >0.5% | 1188 | 0.11 | 0.16 | 0.31 | 0.41 | 16.0 |
| >1% | 1044 | 0.07 | 0.12 | 0.25 | 0.35 | 17.0 |
| >2% | 790 | 0.04 | 0.06 | 0.17 | 0.28 | 19.0 |

**Random windows (3000, any day/hour, same 49h geometry)**

| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |
|---|---:|---:|---:|---:|---:|---:|
| >0% | 2946 | 0.22 | 0.29 | 0.39 | 0.50 | 9.0 |
| >0.5% | 2512 | 0.13 | 0.20 | 0.30 | 0.43 | 14.0 |
| >1% | 2139 | 0.08 | 0.15 | 0.25 | 0.37 | 17.0 |
| >2% | 1552 | 0.04 | 0.08 | 0.17 | 0.27 | 20.0 |

**Real CME contract MBT=F** (111 weekends 2024-04-07 -> 2026-08-23; gap = Sun 17:00 CT open vs Fri 16:00 CT close; horizons count MBT trading bars)

| |gap| | n | fill 6h | fill 12h | fill 24h | fill 48h | median h-to-fill |
|---|---:|---:|---:|---:|---:|---:|
| >0% | 100 | 0.38 | 0.48 | 0.61 | 0.67 | 5.0 |
| >0.5% | 65 | 0.18 | 0.32 | 0.48 | 0.55 | 10.0 |
| >1% | 44 | 0.07 | 0.16 | 0.30 | 0.41 | 18.5 |
| >2% | 23 | 0.04 | 0.13 | 0.30 | 0.43 | 21.5 |

Reading: the base rate of 'price revisits a level from 49h ago within 24h' is the number to beat; the weekend rows must exceed the weekday/random rows for a gap-specific effect to exist.

## (b) Walk-forward, HL BTC perp (spot proxy, taker fees both sides)

Selected on fold 1 (by net, min 10 trades): `{'arm': 'cont', 'thr': 0.005, 'hold': 48, 'stop_mult': 0}`  
**OOS folds 2+3**: n= 202 net=  6233.94 pf= 1.18 wr=0.51 sharpe= 0.82 dd=5925 bps=30.9 folds=[0, 1226, 5008] fold_n=[0, 104, 98]

Full grid, full period (f1 = selection fold; OOS view = f2+f3):

| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fill_thr0_h24_s1.5 | 450 | -15539 | 0.67 | 0.43 | -2.75 | -34.5 | -4436 | -3978 | -7125 |  {'stop': 198, 'target': 171, 'time': 81} |
| fill_thr0_h24_s0 | 450 | -20627 | 0.63 | 0.58 | -3.03 | -45.8 | -5320 | -6872 | -8434 |  {'target': 257, 'time': 193} |
| fill_thr0_h48_s1.5 | 448 | -13747 | 0.72 | 0.46 | -2.31 | -30.7 | -4044 | -3839 | -5865 |  {'stop': 204, 'target': 189, 'time': 55} |
| fill_thr0_h48_s0 | 448 | -21095 | 0.66 | 0.66 | -2.59 | -47.1 | -6541 | -7754 | -6801 |  {'target': 300, 'time': 148} |
| fill_thr0.5_h24_s1.5 | 319 | -13243 | 0.70 | 0.47 | -2.35 | -41.5 | -4147 | -3187 | -5909 |  {'stop': 119, 'target': 119, 'time': 81} |
| fill_thr0.5_h24_s0 | 319 | -18830 | 0.64 | 0.55 | -2.81 | -59.0 | -5684 | -6009 | -7137 |  {'time': 177, 'target': 142} |
| fill_thr0.5_h48_s1.5 | 318 | -11469 | 0.75 | 0.50 | -1.93 | -36.1 | -3773 | -3047 | -4649 |  {'target': 137, 'stop': 126, 'time': 55} |
| fill_thr0.5_h48_s0 | 318 | -20336 | 0.65 | 0.63 | -2.53 | -63.9 | -7071 | -6956 | -6308 |  {'target': 177, 'time': 141} |
| fill_thr1_h24_s1.5 | 245 | -10479 | 0.73 | 0.47 | -1.88 | -42.8 | -2850 | -3202 | -4426 |  {'target': 85, 'stop': 81, 'time': 79} |
| fill_thr1_h24_s0 | 245 | -14053 | 0.68 | 0.51 | -2.19 | -57.4 | -1791 | -6889 | -5372 |  {'time': 152, 'target': 93} |
| fill_thr1_h48_s1.5 | 244 | -8826 | 0.78 | 0.51 | -1.50 | -36.2 | -2597 | -3063 | -3166 |  {'target': 102, 'stop': 87, 'time': 55} |
| fill_thr1_h48_s0 | 244 | -13458 | 0.72 | 0.58 | -1.82 | -55.2 | -1011 | -8186 | -4261 |  {'time': 125, 'target': 119} |
| fill_thr2_h24_s1.5 | 147 | -4851 | 0.83 | 0.49 | -0.91 | -33.0 | -1585 | -1373 | -1894 |  {'time': 70, 'target': 45, 'stop': 32} |
| fill_thr2_h24_s0 | 147 | -8378 | 0.74 | 0.50 | -1.39 | -57.0 | -797 | -5226 | -2355 |  {'time': 101, 'target': 46} |
| fill_thr2_h48_s1.5 | 147 | -3914 | 0.87 | 0.54 | -0.70 | -26.6 | -1443 | -1632 | -839 |  {'target': 57, 'time': 52, 'stop': 38} |
| fill_thr2_h48_s0 | 147 | -9638 | 0.74 | 0.56 | -1.38 | -65.6 | -109 | -8409 | -1120 |  {'time': 87, 'target': 60} |
| cont_thr0_h24_s1.5 | 450 | 10035 | 1.22 | 0.37 | 1.39 | 22.3 | -50 | 3737 | 6347 |  {'time': 238, 'stop': 212} |
| cont_thr0_h24_s0 | 450 | 13644 | 1.25 | 0.50 | 1.67 | 30.3 | 2561 | 2733 | 8350 |  {'time': 450} |
| cont_thr0_h48_s1.5 | 448 | 9720 | 1.18 | 0.31 | 1.13 | 21.7 | 346 | 4070 | 5304 |  {'stop': 255, 'time': 193} |
| cont_thr0_h48_s0 | 448 | 14630 | 1.19 | 0.48 | 1.32 | 32.7 | 6311 | 4795 | 3525 |  {'time': 448} |
| cont_thr0.5_h24_s1.5 | 319 | 10315 | 1.25 | 0.46 | 1.46 | 32.3 | 1293 | 3008 | 6014 |  {'time': 218, 'stop': 101} |
| cont_thr0.5_h24_s0 | 319 | 14157 | 1.35 | 0.51 | 1.92 | 44.4 | 4228 | 2275 | 7654 |  {'time': 319} |
| cont_thr0.5_h48_s1.5 | 318 | 11364 | 1.23 | 0.41 | 1.34 | 35.7 | 1841 | 3725 | 5798 |  {'time': 183, 'stop': 135} |
| cont_thr0.5_h48_s0 | 318 | 12762 | 1.23 | 0.50 | 1.29 | 40.1 | 6528 | 1226 | 5008 | SELECTED {'time': 318} |
| cont_thr1_h24_s1.5 | 245 | 7876 | 1.22 | 0.49 | 1.17 | 32.1 | -2365 | 4836 | 5405 |  {'time': 188, 'stop': 57} |
| cont_thr1_h24_s0 | 245 | 10849 | 1.32 | 0.52 | 1.56 | 44.3 | -260 | 5160 | 5949 |  {'time': 245} |
| cont_thr1_h48_s1.5 | 244 | 6903 | 1.17 | 0.45 | 0.88 | 28.3 | -3905 | 6066 | 4741 |  {'time': 162, 'stop': 82} |
| cont_thr1_h48_s0 | 244 | 8549 | 1.19 | 0.50 | 0.94 | 35.0 | -88 | 4141 | 4496 |  {'time': 244} |
| cont_thr2_h24_s1.5 | 147 | 2647 | 1.09 | 0.47 | 0.42 | 18.0 | -2191 | 3225 | 1613 |  {'time': 117, 'stop': 30} |
| cont_thr2_h24_s0 | 147 | 3473 | 1.13 | 0.48 | 0.54 | 23.6 | -1208 | 2901 | 1779 |  {'time': 147} |
| cont_thr2_h48_s1.5 | 147 | 3561 | 1.11 | 0.45 | 0.49 | 24.2 | -3659 | 6381 | 839 |  {'time': 105, 'stop': 42} |
| cont_thr2_h48_s0 | 147 | 3800 | 1.11 | 0.46 | 0.46 | 25.8 | -1562 | 4331 | 1032 |  {'time': 147} |

Other arm's fold-1 best (`{'arm': 'fill', 'thr': 0.02, 'hold': 48, 'stop_mult': 0}`) OOS folds 2+3: n=  81 net= -9529.40 pf= 0.59 wr=0.49 sharpe=-1.71 dd=13402 bps=-117.6 folds=[0, -8409, -1120] fold_n=[0, 54, 27]

OOS per year (sub-period signs):

| year | n | net |
|---|---:|---:|
| 2020 | 4 | 387 |
| 2021 | 43 | -2199 |
| 2022 | 36 | 1020 |
| 2023 | 30 | 5912 |
| 2024 | 32 | 2326 |
| 2025 | 36 | -805 |
| 2026 | 21 | -408 |

OOS by |gap| bucket:

| bucket | n | net | mean |
|---|---:|---:|---:|
| 0.5-1% | 52 | -2403 | -46 |
| 1-2% | 69 | 3275 | 47 |
| >2% | 81 | 5362 | 66 |

OOS exit reasons: {'time': 202}

- top-3 winner removal: OOS net 6234 -> 316 (pf 1.01, folds [0, -4691, 5008])

## Parameter neighbours (OOS folds 2+3 of every grid cell, no selection)

| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fill_thr0_h24_s1.5 | 300 | -11103 | 0.63 | 0.40 | -2.62 | -37.0 | 0 | -3978 | -7125 |  |
| fill_thr0_h24_s0 | 300 | -15306 | 0.58 | 0.56 | -2.85 | -51.0 | 0 | -6872 | -8434 |  |
| fill_thr0_h48_s1.5 | 300 | -9703 | 0.68 | 0.42 | -2.22 | -32.3 | 0 | -3839 | -5865 |  |
| fill_thr0_h48_s0 | 300 | -14554 | 0.62 | 0.65 | -2.27 | -48.5 | 0 | -7754 | -6801 |  |
| fill_thr0.5_h24_s1.5 | 202 | -9096 | 0.67 | 0.45 | -2.15 | -45.0 | 0 | -3187 | -5909 |  |
| fill_thr0.5_h24_s0 | 202 | -13146 | 0.60 | 0.54 | -2.50 | -65.1 | 0 | -6009 | -7137 |  |
| fill_thr0.5_h48_s1.5 | 202 | -7696 | 0.72 | 0.48 | -1.77 | -38.1 | 0 | -3047 | -4649 |  |
| fill_thr0.5_h48_s0 | 202 | -13264 | 0.63 | 0.63 | -2.10 | -65.7 | 0 | -6956 | -6308 |  |
| fill_thr1_h24_s1.5 | 150 | -7629 | 0.68 | 0.43 | -1.83 | -50.9 | 0 | -3202 | -4426 |  |
| fill_thr1_h24_s0 | 150 | -12262 | 0.58 | 0.47 | -2.41 | -81.7 | 0 | -6889 | -5372 |  |
| fill_thr1_h48_s1.5 | 150 | -6229 | 0.74 | 0.47 | -1.45 | -41.5 | 0 | -3063 | -3166 |  |
| fill_thr1_h48_s0 | 150 | -12447 | 0.61 | 0.55 | -2.08 | -83.0 | 0 | -8186 | -4261 |  |
| fill_thr2_h24_s1.5 | 81 | -3267 | 0.80 | 0.44 | -0.83 | -40.3 | 0 | -1373 | -1894 |  |
| fill_thr2_h24_s0 | 81 | -7581 | 0.63 | 0.44 | -1.61 | -93.6 | 0 | -5226 | -2355 |  |
| fill_thr2_h48_s1.5 | 81 | -2471 | 0.85 | 0.49 | -0.61 | -30.5 | 0 | -1632 | -839 |  |
| fill_thr2_h48_s0 | 81 | -9529 | 0.59 | 0.49 | -1.71 | -117.6 | 0 | -8409 | -1120 |  |
| cont_thr0_h24_s1.5 | 300 | 10085 | 1.37 | 0.38 | 1.81 | 33.6 | 0 | 3737 | 6347 | same arm |
| cont_thr0_h24_s0 | 300 | 11083 | 1.33 | 0.51 | 1.74 | 36.9 | 0 | 2733 | 8350 | same arm |
| cont_thr0_h48_s1.5 | 300 | 9374 | 1.30 | 0.31 | 1.41 | 31.2 | 0 | 4070 | 5304 | same arm |
| cont_thr0_h48_s0 | 300 | 8320 | 1.18 | 0.49 | 0.98 | 27.7 | 0 | 4795 | 3525 | same arm |
| cont_thr0.5_h24_s1.5 | 202 | 9022 | 1.38 | 0.47 | 1.67 | 44.7 | 0 | 3008 | 6014 | same arm |
| cont_thr0.5_h24_s0 | 202 | 9929 | 1.41 | 0.52 | 1.72 | 49.2 | 0 | 2275 | 7654 | same arm |
| cont_thr0.5_h48_s1.5 | 202 | 9523 | 1.35 | 0.41 | 1.46 | 47.1 | 0 | 3725 | 5798 | same arm |
| cont_thr0.5_h48_s0 | 202 | 6234 | 1.18 | 0.51 | 0.82 | 30.9 | 0 | 1226 | 5008 | same arm SELECTED |
| cont_thr1_h24_s1.5 | 150 | 10241 | 1.53 | 0.53 | 1.97 | 68.3 | 0 | 4836 | 5405 | same arm |
| cont_thr1_h24_s0 | 150 | 11109 | 1.59 | 0.56 | 2.04 | 74.1 | 0 | 5160 | 5949 | same arm |
| cont_thr1_h48_s1.5 | 150 | 10808 | 1.50 | 0.50 | 1.76 | 72.1 | 0 | 6066 | 4741 | same arm |
| cont_thr1_h48_s0 | 150 | 8637 | 1.33 | 0.55 | 1.23 | 57.6 | 0 | 4141 | 4496 | same arm |
| cont_thr2_h24_s1.5 | 81 | 4837 | 1.33 | 0.52 | 1.01 | 59.7 | 0 | 3225 | 1613 | same arm |
| cont_thr2_h24_s0 | 81 | 4680 | 1.31 | 0.53 | 0.92 | 57.8 | 0 | 2901 | 1779 | same arm |
| cont_thr2_h48_s1.5 | 81 | 7220 | 1.47 | 0.51 | 1.28 | 89.1 | 0 | 6381 | 839 | same arm |
| cont_thr2_h48_s0 | 81 | 5362 | 1.31 | 0.52 | 0.85 | 66.2 | 0 | 4331 | 1032 | same arm |

Same-arm cells OOS-positive: 16/16; all cells OOS-positive: 16/32

## Controls and shuffles (selected rule)

| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| weekday_control_full | 1188 | 23776 | 1.13 | 0.52 | 1.46 | 20.0 | 18822 | -806 | 5760 | Tue/Wed/Thu 22:00 UTC windows, same rule |
| weekday_control_OOS23 | 794 | 4953 | 1.04 | 0.51 | 0.41 | 6.2 | 0 | -806 | 5760 | folds 2+3 only |

- random-window shuffle (300 draws x 451 windows, any day/hour, same rule, OOS period): mean net=796 sd=7033 p5=-10983 p95=12282 mean n=254; actual OOS net=6234 -> P(shuffle >= actual)=0.210
- side shuffle (2000 draws, OOS trades, timing kept): mean=-1793 sd=7754; actual=6234 -> p=0.151

## Clock and data-source neighbours (selected rule, no re-selection)

| variant | n | net | pf | wr | sharpe | bps | f1 | f2 | f3 | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| clock_CT_full | 319 | 11389 | 1.20 | 0.50 | 1.13 | 35.7 | 5812 | 446 | 5131 | true CME wall-clock (Fri 16:00 CT -> Sun 17:00 CT), Binance |
| clock_CT_OOS23 | 202 | 5577 | 1.16 | 0.51 | 0.74 | 27.6 | 0 | 446 | 5131 |  |
| yf_BTC-USD_730d | 69 | 721 | 1.08 | 0.52 | 0.25 | 10.5 | 1625 | -505 | -399 | 104 weekends 2024-08-28 -> 2026-08-27 (inside fold 3) |
| binance_same_730d | 67 | 1450 | 1.19 | 0.52 | 0.53 | 21.6 | 1743 | 115 | -408 | same weekends on Binance |
| HL_BTC_1h_actual | 17 | -671 | 0.71 | 0.47 | -0.61 | -39.5 | -165 | -327 | -180 | 29 weekends 2026-01-31 -> 2026-08-27, real perp bars |
| binance_same_HLweekends | 18 | -674 | 0.71 | 0.50 | -0.61 | -37.4 | -139 | -322 | -212 |  |
| HL_BTC_15m_actual | 3 | 16 | 1.11 | 0.67 | 0.07 | 5.3 | 0 | -58 | 74 | 7 weekends, 15m stop/target resolution |
| MBT=F_1contract | 65 | -1143 | 0.85 | 0.49 | -0.49 | -21.5 | 848 | -944 | -1047 | gap on MBT itself (signal = reopen bar open = fill px, optimistic); hold counts trading bars; cme_fee |

Liquidity: BTC is the deepest perp on Hyperliquid (>$1B/day); single-instrument test, no concentration issue.

## Verdict

Criteria: `{'oos_net_pos': True, 'pf_ge_1_2': False, 'n_ge_60': True, 'folds_pos': True, 'shuffle_ok': False, 'neighbours_ok': True, 'top3_ok': True, 'subperiods_ok': False}` -> 3 failed  
**Verdict: none** (edge = all pass; weak = OOS net > 0 and exactly one failure; else none)

Reading: (a) the fill arm loses in every cell and every fold - weekend gaps DO get revisited more often than weekday windows of the same size (e.g. |gap|>1%: 38% vs 25% touched within 24h), but the unfilled ones run far enough that fading is a net loser even with the 1.5x stop. (b) the continuation arm is OOS-positive with all 16 neighbours positive, but it is thin: PF < 1.2, the random-window shuffle cannot reject it (p=0.21), removing the 3 best trades leaves ~0, the weekday control shows the same sign (generic 48h momentum after a >0.5% move), and 2025-2026 plus the real Hyperliquid bars (17 weekends) are negative. Not tradable as specified.
