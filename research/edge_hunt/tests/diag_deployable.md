# Deployable? — listing short at h24, 7d hold, BTC-hedged, 10 bps/side slippage

all events n=813 net=$21,432

## Filters chosen on 2020-2024 only

| filter | train n | train bps | 2025 n | 2025 bps | 2025 net | 2026 n | 2026 bps | 2026 net |
|---|---|---|---|---|---|---|---|---|
| no filter | 384 | 392 | 240 | 274 | 6579 | 189 | -10 | -184 |
| crypto only (no stock perps) | 384 | 392 | 240 | 274 | 6579 | 163 | 22 | 358 |
| crypto & day-1 vol > $96M (train median) | 192 | 334 | 197 | 260 | 5130 | 33 | 197 | 649 |
| crypto & day-1 vol > $357M (train p75) | 96 | 523 | 104 | 23 | 242 | 4 | 335 | 134 |
| crypto & 1%-hour capacity > $10k | 224 | 263 | 178 | 43 | 765 | 39 | -135 | -528 |

## Capacity and realistic $ P&L of the surviving filters (2026 only)

- crypto only, target $10,000/event: n=163, avg size $3,851, 2026 net $-7,892 ($-1,127/month over 7 months)
- crypto only, target $25,000/event: n=163, avg size $5,970, 2026 net $-7,896 ($-1,128/month over 7 months)
- crypto only, target $50,000/event: n=163, avg size $7,367, 2026 net $-35,263 ($-5,038/month over 7 months)
- crypto & day1>$357M, target $10,000/event: n=4, avg size $10,000, 2026 net $1,338 ($191/month over 7 months)
- crypto & day1>$357M, target $25,000/event: n=4, avg size $17,155, 2026 net $1,390 ($199/month over 7 months)
- crypto & day1>$357M, target $50,000/event: n=4, avg size $23,405, 2026 net $3,981 ($569/month over 7 months)

## Loss-tail shape (crypto, 2025 vs 2026)

- 2025: n=240 win rate 0.66, median 1251 bps, mean 274 bps, p05 -7776, p01 -16410, worst -28527 bps
- 2026: n=163 win rate 0.58, median 203 bps, mean 22 bps, p05 -2575, p01 -10496, worst -18246 bps

## Would a stop help? (cap each trade's loss at X bps, crypto only)

- 2025: raw 274 bps  stop@-500bps -> 1531  stop@-1000bps -> 1409  stop@-2000bps -> 1209   (a stop cannot be executed at exactly that level; upper bound only)
- 2026: raw 22 bps  stop@-500bps -> 611  stop@-1000bps -> 467  stop@-2000bps -> 319   (a stop cannot be executed at exactly that level; upper bound only)
