# EXECUTION — hl_listing_drift (Binance UM), short at listing+24h, hold 7d, BTC-hedged

events=820; OOS = listings from 2022-04-02; $1000/event; taker 5.0 bps/side both legs.

baseline (0 bps slippage): n=676 net=18004.7 pf=1.26 bps=266.3 folds=[8100, 9905]

## E1 — slippage sweep (bps per side, applied to alt AND hedge legs)

| slip bps/side | n | net | pf | net bps/trade | fold2 | fold3 | 2026 net |
|---|---|---|---|---|---|---|---|
| 0 | 676 | 18004.7 | 1.26 | 266.3 | 8100 | 9905 | 557.9 |
| 2 | 676 | 17471.4 | 1.26 | 258.5 | 7981 | 9491 | 409.5 |
| 5 | 676 | 16671.5 | 1.24 | 246.6 | 7803 | 8869 | 186.9 |
| 10 | 676 | 15338.3 | 1.22 | 226.9 | 7505 | 7833 | -184.1 |
| 15 | 676 | 14005.1 | 1.20 | 207.2 | 7208 | 6797 | -555.1 |
| 20 | 676 | 12672.0 | 1.18 | 187.5 | 6911 | 5761 | -926.1 |
| 30 | 676 | 10005.7 | 1.14 | 148.0 | 6317 | 3688 | -1668.0 |
| 50 | 676 | 4673.4 | 1.06 | 69.1 | 5129 | -456 | -3152.0 |

- break-even slippage: >50 bps per side (4 legs per trade, so total round-trip friction = 4x this + 20 bps of fees).

## E2 — entry / exit timing perturbation (10 bps slippage throughout)

| variant | n | net | pf | bps |
|---|---|---|---|---|
| entry h-6 | 676 | 13073.8 | 1.18 | 193.4 |
| entry h-2 | 675 | 17279.1 | 1.25 | 256.0 |
| entry h24 (base) | 676 | 15338.3 | 1.22 | 226.9 |
| entry h+2 | 676 | 11272.8 | 1.16 | 166.8 |
| entry h+6 | 676 | 7163.2 | 1.10 | 106.0 |
| entry h+24 (day 2) | 675 | 2480.5 | 1.03 | 36.7 |
| entry at close of h24 | 676 | 13570.1 | 1.19 | 200.7 |
| exit at close | 676 | 14774.0 | 1.21 | 218.6 |
| hold 5d | 676 | 9239.1 | 1.15 | 136.7 |
| hold 10d | 668 | 13750.2 | 1.17 | 205.8 |
| hold 14d | 666 | -6012.7 | 0.95 | -90.3 |

## E3 — adverse-fill bounds (no extra slippage; fills taken from the bar's own range)

| fill quality | n | net | pf |
|---|---|---|---|
| open (base) | 676 | 18004.7 | 1.26 |
| 25% toward the adverse extreme | 676 | 10668.3 | 1.15 |
| 50% (mid of open->extreme) | 676 | 3167.2 | 1.04 |
| worst price of the bar | 676 | -12366.9 | 0.85 |

## E4 — funding realism (the short PAYS on net here)

- funding interval hours across the archive: {4: 122281, 8: 45902, 1: 12905, 2: 138}
- OOS components at 0 bps: alt 22128, funding -6137, hedge 3356, fees -1343
- per-trade funding: mean -9.08 USD on $1000 (-90.8 bps), p05 -75.3, p95 19.1, share negative 0.39
- funding x0 (ignored)     net=  21475.3 pf=1.32
- funding x1 (base)        net=  15338.3 pf=1.22
- funding x1.5 (worse)     net=  12269.8 pf=1.17
- funding x2               net=   9201.2 pf=1.13

## E5 — capacity per event

- entry-hour $ volume: median $4.2M, p25 $1.0M, p05 $0.02M
- at 1% of the thinner of the entry/exit hour: median size $15,341, p25 $3,935, p05 $107
- by year (median 1%-of-hour capacity): 2022: $9,493, 2023: $16,240, 2024: $34,905, 2025: $24,093, 2026: $2,419
- target $1,000/event -> realised avg size $910, OOS net $16,869 (321/month)
- target $5,000/event -> realised avg size $4,077, OOS net $88,549 (1,683/month)
- target $25,000/event -> realised avg size $14,400, OOS net $325,412 (6,187/month)
- target $100,000/event -> realised avg size $30,058, OOS net $750,930 (14,276/month)
- target $250,000/event -> realised avg size $39,540, OOS net $1,065,749 (20,261/month)

## E6 — concurrency, capital and margin

- concurrent open positions: median 2, p95 8, max 27
- since 2025-01: median 5, p95 12, max 27
- at $1,000/event: peak gross notional $54,000 -> initial margin $10,800 at 5x, $18,000 at 3x
- at $5,000/event: peak gross notional $270,000 -> initial margin $54,000 at 5x, $90,000 at 3x
- at $25,000/event: peak gross notional $1,350,000 -> initial margin $270,000 at 5x, $450,000 at 3x

## E7/E8 — realistic combined scenario

| year | n | net (10 bps slip) | avg/trade | bps/trade |
|---|---|---|---|---|
| 2022 | 17 | 2031.1 | 119.48 | 1194.8 |
| 2023 | 99 | 3874.9 | 39.14 | 391.4 |
| 2024 | 131 | 3037.5 | 23.19 | 231.9 |
| 2025 | 240 | 6578.8 | 27.41 | 274.1 |
| 2026 | 189 | -184.1 | -0.97 | -9.7 |

- at 20 bps/side: total net 12672 (pf 1.18); 2026 alone net -926 on n=189 (-49.0 bps/trade)
