# LEAKAGE — hl_listing_drift (Binance UM), pick `{'rule': 'short_after', 'N': 24, 'H': 7, 'hedge': True}`

events=820  dropped={'archive_start': 11, 'month_boundary': 0, 'no_data': 0, 'gap_first_48h': 1}  earliest archive month=2020-01

baseline OOS (folds 2+3, all events): n=676 net=18004.7 pf=1.26

## L1 — listing-timestamp integrity

- funding archive present for 817/820 symbols (3 without).
- hours between first 1h bar and first funding stamp: median 1.0h, p05 -33.4h, p95 4.0h, share in [-1, 9]h 0.718, share negative 0.353
  (a real listing funds within one 8h interval; a large positive gap means the kline archive starts before funding, a negative gap means funding predates the first kline -> t0 is NOT the listing.)
- symbols with ANY funding stamp before the first kline: 227 (mostly placeholder 0.0001/0.0 rows)
- symbols with a NON-placeholder funding rate before the first kline (real pre-t0 trading): 27 ['ALLOUSDT', 'APRUSDT', 'BARDUSDT', 'CLOUSDT', 'EDENUSDT', 'ERAUSDT', 'EULUSDT', 'HEMIUSDT', 'HOLOUSDT', 'JCTUSDT', 'KGENUSDT', 'LIGHTUSDT']
- OOS ex any-early-funding: n=494 net=10927.0 pf=1.19 avg=22.1
- OOS ex non-placeholder-early: n=649 net=16040.0 pf=1.24 avg=24.7
- OOS on the early-funding subset ALONE: n=182 net=7077.7 pf=1.73 avg=38.9
- S3 spot-check pool = the 227 symbols with an early funding stamp (the hardest cases for t0 integrity)
- S3 re-listing spot-check on 40 random symbols: first monthly file matches the cached first_month for 40, mismatch 0 [], network errors 0

## L2 — does t0 look like a real listing?

- entry-hour(UTC) concentration of t0: top hours 12h:112, 13h:103, 09h:99, 14h:89, 07h:86, 08h:55; distinct hours 19; share in the top-3 hours 0.38 (uniform would be 0.125)
- bar 0 is the highest-volume hour of the first 48h for 0.19 of events; day-1 volume is 0.26 of the first week's volume (a listing spike, not a mid-life month start)

## L3 — survivorship

- archive ends 2026-07; 31/832 symbols stop earlier (delisted since).
- delisted since : n=   9 net=   1262.7 pf=inf avg=140.3
- still listed   : n= 667 net=  16742.0 pf=1.25 avg=25.1
  (the sample INCLUDES delisted symbols, so it is point-in-time; if the edge lived only in the delisted half it would still be tradable but only ex-post identifiable.)

## L4 — duplicate base assets (re-listings under a new ticker)

- 2 base assets appear more than once: [('BOB', ['1000000BOBUSDT', 'BOBUSDT']), ('CAT', ['1000CATUSDT', 'CATUSDT'])]
- OOS keeping only the FIRST listing per base asset: n=674 net=17667.8 pf=1.26 (baseline n=676 net=18004.7)

## L5 — events silently dropped

- OOS-window events: {'traded': 676, 'too_short': 6}

## L6 — causality assertions on every OOS trade

- violations: NONE — every entry is the open 24h after the first traded bar, every exit the open 7d later

## L7 — archive-edge exclusions

- excluded as unverifiable (first archive month == 2020-01): ['ADAUSDT', 'BCHUSDT', 'BTCUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'LINKUSDT', 'LTCUSDT', 'TRXUSDT', 'XLMUSDT', 'XRPUSDT']
  these are the 11 original 2020-01 perps; they have no observable listing bar, so they cannot be tested either way.
