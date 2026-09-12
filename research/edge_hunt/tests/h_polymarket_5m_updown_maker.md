# polymarket_5m_updown_maker — resting-limit (maker) bids on Polymarket BTC/ETH 5m and BTC 15m Up/Down

**Verdict: none.** A maker that rests bids at (anchor − X) and is filled only when a public print provably trades
through the bid loses in **192 of 192** grid cells in-sample (fold 1) and in **191 of 192** cells out-of-sample.
The fold-1 pick (the least-losing cell, −$172 in-sample) lands at OOS **+$62 on n=54 windows, PF 1.13, WR 37%**,
folds [+$30 (n=51), +$32 (n=3)] — below every threshold (n ≥ 60, PF ≥ 1.2), and it does not survive top-3-trade
removal (→ −$55), a 10-s settlement guard (→ −$33, n=61), or transfer to ETH-5m (−$15, n=20) and BTC-15m (−$21, n=17).
All neighbours are negative. Fees are not the constraint (maker fee is 0); adverse selection is: a resting bid on
these markets is hit almost exclusively when the outcome has just moved against it.

Script: `tests/h_polymarket_5m_updown_maker.py` · results: `tests/h_polymarket_5m_updown_maker_result.json` ·
log: `tests/h_polymarket_5m_updown_maker.log` · quant-lab: project `edge-hunt`, strategy `polymarket_5m_updown_maker`
(433 rows: 192 `is_f1_*`, 192 `oos_*`, `wf_oos`, `oos_selected_G{1,2,3,4,6,10}`, `shuffle_seed{1,2,3}`, `strat_feb_jul`,
`transfer` ×2; the first 36 rows are a quick-mode 1/4-subsample pass, marked `trust=suspect`/superseded).

## 1. Data (all public, cached under `data/`)

| set | source | coverage |
|---|---|---|
| BTC 5m windows | `polymarket/meta_*` + `trades_*` (Gamma events by slug `btc-updown-5m-<ts>`, data-api prints) | full span **2026-08-07 23:00 → 08-28 00:00 UTC, 5,749 resolved windows, 9.79M prints**; stratified Feb–Jul sample 3,435 windows |
| ETH 5m windows | `polymarket_eth_updown_5m/` (new, `fetch_polymarket_multi.py`) | 08-14 16:10 → 08-28, 3,838 windows, 1.39M prints |
| BTC 15m windows | `polymarket_btc_updown_15m/` (new) | 08-07 16:15 → 08-28, 1,951 windows, 1.92M prints |
| Binance spot 1s klines | `binance_1s/` (BTCUSDT, +Aug-27 added), `binance_1s_ETHUSDT/` (new, Aug 13–27) | |

Fee schedule verified live on Gamma for all three families: `{"rate":0.07,"exponent":1,"takerOnly":true,"rebateRate":0.2}`
→ **maker fee = 0** (makers receive a 20% rebate of taker fees; ignored here). Tick 0.001 (0.01 on 1,517 Feb–Mar windows), min size 5.
Print-side semantics confirmed: taker-BUY prints of a token sit +0.010 (median) above taker-SELL prints of the same token in
the same second, 82% of 606k same-second pairs.

## 2. Execution model (strict, pre-registered)

* Timestamp problem inherited from `h_poly_lastminute_1s`: data-api print stamps are Polygon settlement times, a few
  seconds (fat tail) after the match. Quote Q(s) posted at second s uses the Binance kline that closed at s and the
  taker-implied bid/ask from prints stamped < s. A print stamped t is tested against **Q(t − G)** — the stalest quote
  that could have been live — and only if **t < T1** (so the quote provably still existed even at zero delay).
  Honest G = 6 s (selection), G = 10 robustness, G = 1..4 contamination diagnostic only.
* **Fill = strictly traded through**: bid for token S at P is filled by a taker-SELL of S at price < P, or a taker-BUY
  of the complement at price > 1 − P (Polymarket's CLOB matches BUY Up vs BUY Down by minting). Filled at P for
  min(print size, remaining). 50 shares per side per window; bids capped at (last implied ask − tick) so no cell ever
  crosses the book as a taker. Payoff 1/0 at resolution; one decision = one window.
* Model: p = Φ(log(close/strike) / (σ√remaining)), strike = `priceToBeat` de-based by the trailing-12-window
  Chainlink/Binance basis (prior windows only), σ = trailing-2h std of 15-s returns scaled to 1 s (fold-1 Brier
  0.1415 vs 0.1417/0.1425 for 1 s/60 s; market mid Brier 0.1237 on the same seconds). `cal` anchor = fold-1 binned
  recalibration of p by (phase, p).
* Grid (192): anchor ∈ {model, cal, market(mid), blend} × mode ∈ {mm two-sided at anchor∓X, tilt one-sided only where
  model − mid ≥ X} × X ∈ {0.02, 0.04, 0.08, 0.15} × (T0,T1) ∈ {(0,60),(0,120),(60,120),(120,300),(200,300),(250,300)}.
  Walk-forward: select on fold 1 (08-07 23:00 → 08-14 15:40) by net; report folds 2+3.

## 3. Results

### Fold-1 in-sample: every cell negative

| mode | mean is_net | best is_net | mean OOS net | best OOS net |
|---|---|---|---|---|
| mm (two-sided) | −$4,641 | −$597 | −$8,010 | −$1,077 |
| tilt (one-sided) | −$2,846 | −$172 | −$4,912 | +$62 |

By X (OOS mean): 0.02 −$9,303 · 0.04 −$7,939 · 0.08 −$5,564 · 0.15 −$3,037 (loss shrinks only because fills vanish).
By phase (OOS mean): (0,60) −$5,146 · (0,120) −$6,861 · (60,120) −$5,481 · (120,300) −$9,111 · (200,300) −$7,275 · (250,300) −$4,890.
By anchor (OOS mean): market −$6,104 · blend −$6,342 · cal −$6,665 · model −$6,731.
Two-sided quoting at X=0.02 is filled in ~3,745 of 3,838 OOS windows and loses ≈ $3.5 per window on ≈ $50 cost (−7% of
notional): the bid is hit almost only after the Binance move has gone against it.

### HEADLINE — walk-forward OOS folds 2+3, fold-1 pick {anchor=market, mode=tilt, X=0.15, T0=0, T1=60, G=6}

| n | net | PF | WR | Sharpe | fold 2 | fold 3 | fill prob/window |
|---|---|---|---|---|---|---|---|
| 54 | **+$62** | 1.13 | 0.370 | 0.39 | +$30 (n=51) | +$32 (n=3) | 1.4% |

By ISO week: 08-10 −$64 (29) · 08-17 +$95 (24) · 08-24 +$32 (1). Top-3 removal → **−$55**. Top 10% of windows = 100%+ of net.

### Sanity checks (selected cell)

| check | result |
|---|---|
| settlement guard | G=10 → −$33 (n=61, PF 0.94); contaminated G=1/2/3/4 → +$119/+$88/+$74/−$32 (n=23–36) |
| shuffle (model permuted across windows, 3 seeds) | +$508 / −$453 / −$171 on n≈560 — the "signal" is indistinguishable from a random tilt |
| neighbours | the 5 nearest cells: −$28, −$48, −$144, −$388, −$510; 191/192 cells negative OOS |
| taker-fee stress (fee charged anyway) | +$46 |
| stratified Feb–Jul sample | +$114 on n=17 (5 months tiny positive, 2 negative) — not evidence |
| ETH-5m transfer (3,838 windows) | −$15, n=20, PF 0.90, folds [+9, −36, +12] |
| BTC-15m transfer (1,951 windows, T0/T1 scaled ×3) | −$21, n=17, PF 0.87, folds [−20, −66, +65] |
| concentration | single instrument; net comes from 3 windows; no hour-of-day structure (n too small) |

## 4. Calibration curves (OOS folds 2+3, market mid vs realised Up rate)

| rel (s into window) | bins 0.3–0.8: realised − price (weighted) | n |
|---|---|---|
| 120 | −0.009 | 1,853 |
| 200 | **−0.039** | 955 |
| 250 | −0.023 | 353 |

The market mid is well calibrated overall (Brier 0.124 vs model 0.142); the only systematic deviation is a ~4 pp
**over-pricing of Up in the 0.3–0.8 mid-range about 100 s before close** (each of the five bins at rel 200 is below
its price: 0.317/0.351, 0.379/0.451, 0.513/0.551, 0.624/0.648, 0.718/0.753). The Gaussian model is under-confident late
(rel 250, bins 0.6–0.9: realised 0.84–0.98 vs 0.65–0.85), which is why `cal` was included — it did not help the maker.
Full bin tables for all three markets are in the results JSON.

## 5. Interpretation

1. Maker fills on these markets are informed flow: a resting bid gets traded through when a taker bot reacts to a
   Binance move faster than the (G-seconds stale) quote. Widening X only removes fills; it never turns the sign.
2. The model/anchor choice is irrelevant (shuffle ≈ real), confirming the previous finding that the market already
   embeds everything Binance says; there is no mis-pricing for a passive quote to harvest at 5–10 s staleness.
3. The zero maker fee and 20% rebate are real but ~2 orders of magnitude smaller than the adverse-selection cost.
4. Together with `h_poly_lastminute_1s` (taker side), this closes the Polymarket 5m/15m Up/Down line on cached public
   data for both sides of the book.

## 6. Next test

The one residual, model-free anomaly is the −3.9 pp Up over-pricing at rel≈200 in the 0.3–0.8 range (n≈955 window-seconds
OOS). Test it as a **taker**: at rel 200 buy Down at the implied ask when the Up mid is in [0.35, 0.80], fee 0.07·p(1−p),
one decision per window, walk-forward over the full span, then ETH-5m/BTC-15m transfer. Expected gross ≈ 4 pp/share vs
spread ≈ 1 pp + fee ≈ 1.5–1.75 pp: marginal, but cheap to check and it uses only data already cached.
