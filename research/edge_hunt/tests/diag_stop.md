# Does a stop rescue it?  (crypto listings only, 10 bps/side slippage)

| stop | n | stopped% | total net | bps/trade | 2023 | 2024 | 2025 | 2026 | worst trade bps |
|---|---|---|---|---|---|---|---|---|---|
| none | 787 | 0% | 21974 | 279 | 3875 | 3038 | 6579 | 358 | -28527 |
| +30% | 787 | 26% | 22558 | 287 | 2295 | 5326 | 5284 | 163 | -4880 |
| +50% | 787 | 15% | 20703 | 263 | 1042 | 7050 | 2299 | 1620 | -7351 |
| +75% | 787 | 8% | 21932 | 279 | 1153 | 6331 | 6296 | 673 | -9847 |
| +100% | 787 | 5% | 24547 | 312 | 4244 | 6071 | 5261 | 1132 | -14839 |
| +150% | 787 | 3% | 16282 | 207 | 3695 | 4560 | 1099 | -863 | -16703 |

## At realistic size (each event capped at 1% of the thinner of entry/exit hour volume)

| stop | target/event | 2025 net | 2026 net | 2026 avg size |
|---|---|---|---|---|
| none | $10,000 | 44,448 | -7,892 | $3,851 |
| none | $25,000 | -19,346 | -7,896 | $5,970 |
| +50% | $10,000 | -2,665 | 3,065 | $3,865 |
| +50% | $25,000 | -135,891 | -7,968 | $6,218 |
| +100% | $10,000 | 30,126 | -2,049 | $3,851 |
| +100% | $25,000 | -47,194 | -6,046 | $6,053 |

## Distribution with a +50% stop

- 2020: n= 70 win 0.76 median   1114 mean    889 p05   -4414 worst   -5105 stopped 7% median hold 168h
- 2021: n= 57 win 0.68 median    960 mean    216 p05   -4920 worst   -5741 stopped 16% median hold 168h
- 2022: n= 27 win 0.74 median    887 mean    459 p05   -4554 worst   -5929 stopped 7% median hold 168h
- 2023: n= 99 win 0.71 median    850 mean    105 p05   -5211 worst   -5695 stopped 15% median hold 168h
- 2024: n=131 win 0.69 median   1084 mean    538 p05   -5043 worst   -6226 stopped 12% median hold 168h
- 2025: n=240 win 0.60 median    841 mean     96 p05   -5358 worst   -7351 stopped 26% median hold 168h
- 2026: n=163 win 0.58 median    203 mean     99 p05   -4705 worst   -6020 stopped 6% median hold 168h
