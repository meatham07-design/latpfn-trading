# STATISTICS — hl_listing_drift (Binance UM), pick `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}`

events=820 listings 2020-02-03 -> 2026-07-29

baseline OOS: n=676 net=18004.7 pf=1.26 avg=26.63 (266.3 bps/trade)

## S1 — expanding-window walk-forward: re-pick the parameters every year

| test year | picked on all prior listings | train n | test n | test net | test pf | bps/trade |
|---|---|---|---|---|---|---|
| 2021 | `short_after N=24 H=14 hedge=True` | 70 | 58 | -835.8 | 0.90 | -144.1 |
| 2022 | `short_after N=24 H=7 hedge=True` | 128 | 26 | 610.3 | 1.25 | 234.7 |
| 2023 | `short_after N=24 H=7 hedge=True` | 154 | 99 | 4268.8 | 1.65 | 431.2 |
| 2024 | `short_after N=4 H=7 hedge=True` | 253 | 131 | 4157.1 | 1.26 | 317.3 |
| 2025 | `short_after N=4 H=14 hedge=True` | 384 | 242 | -5537.8 | 0.91 | -228.8 |
| 2026 | `short_after N=24 H=7 hedge=True` | 626 | 187 | 872.1 | 1.07 | 46.6 |

**Expanding-window OOS total 2021-2026: $3,535** across 743 trades (this is the number to believe: parameters are re-chosen only on the past, every year).

## S2 — equal-event-count folds (calendar thirds put 0 events in fold 1)

- fold sizes 273/273/274; boundaries 2024-03-01 | 2025-09-09
- fold-1 pick `{'rule': 'short_after', 'N': 4, 'H': 7, 'hedge': True}` (is net 13714) -> fold2 n=273 net=6028.2 pf=1.15; fold3 n=268 net=-625.5 pf=0.98

## S3/S4 — resampling and clustering

- bootstrap (iid trades, 676 units): mean 17867, P(net<=0) = 0.0342
- bootstrap (clustered by entry day, 414 units): mean 18049, P(net<=0) = 0.0344
- bootstrap (clustered by month, 50 units): mean 17848, P(net<=0) = 0.0626
- cluster-robust t (clusters = entry day, 414 clusters): t = 1.83
- cluster-robust t (clusters = month, 50 clusters): t = 1.49

## S5 — trimming

- remove top-3 winners: 18005 -> 16035
- remove top-5 winners: 18005 -> 14814
- remove top-10 winners: 18005 -> 11983
- remove top-25 winners: 18005 -> 4623
- remove the best year (2025, 7516): 10489
- remove the best month (2025-01, 6540): 11465
- positive months 37/50; median month 356
- winsorised at 1/99 pct: 21965 (raw 18005)

## S6 — breadth of the parameter grid (OOS folds 2+3)

- 24/40 grid variants with n>=30 are OOS-positive.
- short_after family: 14/16 positive; nets [-6678, -3345, 3916, 4739, 5010, 5960, 7543, 9029, 9152, 9722, 9752, 10957, 12960, 13474, 15326, 18005]

## S7 — matched-date control: same dates, SEASONED coins (spot daily panel)

- control book: 676 legs per draw, 300 draws. mean $5,455, sd $3,313, p95 $9,884, max $12,293
- actual listing book, price component only (alt + hedge - fees, funding excluded): $24,142
- **p(control >= actual) = 0.0000**
- actual including funding: $18,005 (funding costs $-6,137)

## S8 — decay

| year | n | mean bps/trade | t |
|---|---|---|---|
| 2022 | 17 | 1231.0 | 2.98 |
| 2023 | 99 | 431.2 | 1.68 |
| 2024 | 131 | 272.5 | 0.75 |
| 2025 | 240 | 313.2 | 1.07 |
| 2026 | 189 | 29.5 | 0.16 |

- 2026 mean 29.5 bps (n=189) vs 2022-2025 mean 358.3 bps (n=487); difference -328.7 bps, t = -1.27
- 2026 alone: t = 0.16, net $558
- OLS trend in per-trade bps: -204.4 bps per year

## S9 — underlying event study (no trading rule): excess return vs BTC, hour 24 -> hour 192

- n=813 listings; mean excess -3.94%, median -8.87%, share negative 0.67
- naive t = -3.26; day-clustered t = -4.57 (542 distinct days)
- by year: 2020: -9.4% (med -11.0%, n=70), 2021: -2.1% (med -9.9%, n=57), 2022: -3.5% (med -9.5%, n=27), 2023: -5.9% (med -11.1%, n=99), 2024: -3.0% (med -11.4%, n=131), 2025: -4.9% (med -14.4%, n=240), 2026: -0.9% (med -1.8%, n=189)
