# poly_lastminute_1s — Polymarket BTC 5m Up/Down, last-90-seconds staleness vs a Binance 1s model

**Verdict: none.** Walk-forward OOS net **-$2,255** on 2,657 windows (PF 0.97, WR 33%), OOS folds
[-$5,543, +$3,288]; stratified Feb–Aug sample -$8,103 (PF 0.87, all 3 folds negative, 6 of 7 months negative).
The apparent profit of the pre-registered design (model lag 1–2 s) is a **data artefact**: Polymarket
print timestamps are on-chain settlement times, several seconds after the match.

Script: `tests/h_poly_lastminute_1s.py` · results JSON: `tests/h_poly_lastminute_1s_result.json` ·
data: cached `data/polymarket/*` (9,199 windows / 20.6M prints) + Binance spot BTCUSDT **1s** klines
(`fetch_binance_1s.py` → `data/binance_1s/`, 196 daily files: Aug 7–26 full span + every stratified-sample day;
the Aug-27 file is not yet published so the full span is **2026-08-07 23:00 → 08-27 00:00 UTC, 5,368 windows**).
Quant-lab: project `edge-hunt`, strategy `poly_lastminute_1s` (18 in-sample cells, 18 OOS cells, 5 contaminated
cells marked `trust=suspect`, wf_oos, selected_fullspan, 3 shuffles, strat_feb_jul).

## 1. Data-integrity finding that changed the test

| check | result |
|---|---|
| gaps between distinct print timestamps | 48% = 1 s, 48% = 2 s, 3% = 3 s → prints sit on a ~1.5 s block lattice (Polygon), not on match times |
| market `closedTime − ts` | 318 / 355 / 387 s (p5/p50/p95): trading continues ~1 min after the window ends |
| prints stamped **after** `closedTime` | 4,116 prints (0.04%) in **2,503 of 5,421 windows**, lagging 3 / 6 / 12 / 24 / 48 s (p10/p25/p50/p75/p90) — impossible unless the stamp is settlement, not match |
| regression ΔUp-price(t) on Binance 1s returns lag 0..10 (rel 210–300, n=145k) | β: lag0 0.17, lag1 0.16, lag2 0.64, **lag3 2.58, lag4 2.45**, lag5 0.51, lag6.. ≤ 0 (pp per bp). Response concentrated 3–4 s "after" Binance and exhausted by 5 s. |

A print stamped at t was matched at t − D with D unknown (block inclusion + operator batching; median ≥ 3 s, fat
tail). Any model using Binance klines closer than ~5 s before the stamp is look-ahead relative to the real match, and
the ask it "fills" was already consumed. Therefore selection ran only over **L ≥ 6 s** (model kline closed ≥ 5 s before
the print stamp); L = 1..5 are shown only as a contamination diagnostic.

## 2. Model

* strike: `ptb_adj` = `price_to_beat` / exp(trailing 12-window mean Chainlink/Binance basis from prior windows), or
  plain Binance open at ts; sigma: trailing-2h std of {1,15,60}-s returns scaled to 1 s. Both chosen on **fold 1 only**
  by Brier (rel ≥ 210, L=6): ptb_adj/1s Brier 0.1198 vs binance/1s 0.1376. **Market price Brier on the same prints: 0.0781.**
* strike error is structural: Chainlink-vs-Binance basis changes by **3.74 bps (std) per window** (each Chainlink
  snapshot carries ~2.6 bps of independent noise); **46% of windows are close calls** (|Binance move at 210 s| < 3 bps)
  where the remaining 90-s vol (~3.5 bps) is comparable to that noise. The market resolves 100% consistently with
  Chainlink; a Binance-only model cannot see the quantity that resolves.
* calibration (full span, L=6, rel ≥ 210, second-level, n=221k): when model − market < −0.2 the market says 0.854, the
  model 0.476, realised **0.860**; when > 0.2 market 0.145, model 0.522, realised **0.153**. Logit(y) ~ 1.05·logit(mkt)
  (z=169) + 0.086·logit(model) (z=14): the model adds a sliver of information, the market holds essentially all of it.

## 3. Trade rule / execution

Taker, prints-only fills: buy the side whose token printed at least X below p_model, only on prints where an ask
provably existed (taker-BUY of that token or taker-SELL of the complement), first qualifying print fixes the side,
accumulate same-side qualifying prints (each capped at printed size) to $50 cost per window, payoff 1/0 at ts+300.
Fee = shares × rate × (p(1−p))^exp per the market's feeSchedule (all full-span windows are 0.07/exp 1; 0.25/exp 2 only
in Feb–Mar), taken in the outcome token, so its realised USD cost = fee tokens × payoff.

## 4. Walk-forward (folds: 08-07 23:00 → 08-14 07:20 → 08-20 15:40 → 08-27 00:00)

### In-sample grid (fold 1 only, honest L ≥ 6)

| L | T0 | X | n | net $ | PF | WR | sel |
|---|---|---|---|---|---|---|---|
| 6 | 210 | 0.03 | 1396 | +2906 | 1.09 | 0.47 | |
| 6 | 210 | 0.05 | 1288 | +88 | 1.00 | 0.44 | |
| 6 | 210 | 0.10 | 1114 | −2055 | 0.93 | 0.40 | |
| 6 | 240 | 0.03/0.05/0.10 | 1203/1101/954 | −3866/−4761/−3157 | 0.88/0.84/0.89 | | |
| 6 | 270 | 0.03/0.05/0.10 | 898/826/701 | −3693/−4516/−3774 | 0.85/0.81/0.82 | | |
| 8 | 210 | 0.03 | 1401 | **+3923** | 1.11 | 0.47 | ✔ |
| 8 | 210 | 0.05 | 1296 | +1279 | 1.04 | 0.44 | |
| 8 | 210 | 0.10 | 1122 | −2633 | 0.92 | 0.39 | |
| 8 | 240 | 0.03/0.05/0.10 | 1209/1108/963 | −4170/−4500/−3663 | 0.87/0.85/0.87 | | |
| 8 | 270 | 0.03/0.05/0.10 | 915/835/722 | −4198/−4943/−4086 | 0.83/0.80/0.82 | | |

### HEADLINE — OOS folds 2+3 with the fold-1 pick (X=0.03, T0=210, L=8, ptb_adj/1s)

| n | net | gross | fees | PF | WR | Sharpe | fold 2 | fold 3 |
|---|---|---|---|---|---|---|---|---|
| 2657 | **−$2,255** | −$1,111 | $1,144 | 0.97 | 0.330 | −0.32 | −$5,543 (n=1339) | +$3,288 (n=1318) |

Full span with the selected cell (fold 1 in-sample): n=4058, net +$1,667, PF 1.02; by day it swings −$1.9k…+$4.5k
(two days, Aug 10 and Aug 24, contribute +$8.7k of it). Entry price < 0.30 in 55% of windows (WR 12%, net −$1,023).

### Sensitivity — OOS of every honest cell (not the headline)

| T0 | X | L=6 net / PF / folds | L=8 net / PF / folds |
|---|---|---|---|
| 210 | 0.03 | −738 / 0.99 / [−5052, +4314] | −2255 / 0.97 / [−5543, +3288] |
| 210 | 0.05 | −3629 / 0.95 / [−3582, −47] | −3340 / 0.95 / [−3429, +90] |
| 210 | 0.10 | +6713 / 1.11 / [+575, +6138] | +2559 / 1.04 / [−659, +3218] |
| 240 | 0.03 | −12866 / 0.81 | −16206 / 0.76 |
| 240 | 0.05 | −11801 / 0.81 | −10484 / 0.84 |
| 240 | 0.10 | −5525 / 0.90 | −9965 / 0.82 |
| 270 | 0.03 | −1248 / 0.97 / [−6365, +5117] | −2487 / 0.94 |
| 270 | 0.05 | −1934 / 0.95 | −3305 / 0.91 |
| 270 | 0.10 | +1982 / 1.06 / [−5472, +7454] | +909 / 1.03 / [−5952, +6861] |

14 of 18 honest cells lose OOS. The only cell positive in both OOS folds (T0=210, X=0.10, L=6) lost −$2,055 in fold 1
(so no selection rule would have picked it), halves at L=8, and L=6 is still inside the settlement-delay tail
(post-close lags have median 12 s). Later T0 (240/270) is uniformly and heavily negative: the closer to resolution,
the more the market knows that the model does not.

## 5. Contamination diagnostic — same rule (X=0.10, T0=210), full span, model lag L

| L (s) | n | net $ | PF | Sharpe |
|---|---|---|---|---|
| 1 | 3074 | +43,625 | 1.51 | 4.73 |
| 2 | 3068 | +31,551 | 1.36 | 3.61 |
| 3 | 3066 | +22,175 | 1.25 | 2.55 |
| 4 | 3122 | +7,827 | 1.09 | 0.98 |
| 5 | 3180 | +5,671 | 1.06 | 0.73 |
| 6 | 3209 | +4,658 | 1.05 | 0.64 |
| 8 | 3265 | −74 | 1.00 | −0.01 |

Monotone decay of "profit" with the model lag, tracking the lag-3/4 peak of the print-response regression: this is the
signature of using Binance information from after the actual match, not of a stale market. The pre-registered L=1–2
design would have reported a spurious +$11.6k OOS (first pass of this script, recorded nowhere as a result).

## 6. Sanity checks

* **Shuffle** (model of a random other window at the same rel, selected params, 3 seeds): −$21.3k / −$25.5k / −$25.2k,
  PF 0.83–0.86 — a random signal is strongly adverse-selected; the honest signal is indistinguishable from zero.
* **Sub-period**: OOS fold 2 −$5,543, fold 3 +$3,288; stratified Feb–Aug −$8,103 with folds [−3525, −2801, −1777],
  months Feb −140, Mar −2417, Apr −2160, May −1136, Jun −629, Jul +138, Aug −1759.
* **Neighbours**: see §4 — no positive neighbourhood; the selected cell's neighbours are −$738 / −$3,340 / −$3,629.
* **Concentration**: single instrument; by fee schedule only 0.07/exp 1 in the full span; by side Up +$4.9k / Down
  −$3.3k full span (fold 1 included); P&L dominated by a few longshot wins at price < 0.3.

## 7. Interpretation

1. The sub-minute Polymarket "staleness" cannot be measured from the public prints feed: timestamps are settlement
   times with a multi-second fat-tailed delay, and the entire apparent edge lives inside that delay.
2. Even giving the model its best honest shot (basis-adjusted strike, fold-1-selected vol), the market's last-90-s
   price is far better calibrated (Brier 0.068 vs 0.108 at L=6) because resolution is Chainlink-vs-`price_to_beat`
   and the Chainlink/Binance basis moves ~3.7 bps per window — the same order as the remaining vol in the 46% of
   windows that are close calls. A Binance-only model is structurally blind to what decides those windows.
3. Fees are not the binding constraint (fees $1.1k on $130k notional OOS, ~0.9%); information is.
4. This closes the Polymarket-vs-Binance line for taker strategies on cached public data.

## 8. What a next test would need

* A **live recorder** (CLOB websocket book + Binance trade stream + Chainlink Data Streams BTC/USD), all stamped on
  receipt on one clock, running ≥ 1 week; only that can test a < 5 s staleness claim. Without it, no further
  Polymarket 5m hypothesis should be run on the data-api prints.
* The information that decides close-call windows is the **Chainlink stream vs `price_to_beat`**, not Binance; a model
  fed the Chainlink price (or the on-chain/Polymarket-displayed price) with sub-second receipt stamps is the only
  version of this hypothesis worth testing. Expect it to be crowded (the print response is complete within ~5 s
  including settlement).
* If the line is kept at all, switch to the **maker** side: post resting quotes at model ± spread in the 210–270 s
  phase and test adverse selection against the recorded book, instead of taking prints.
