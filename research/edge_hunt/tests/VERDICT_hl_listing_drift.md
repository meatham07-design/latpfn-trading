# hl_listing_drift — final verdict after the three adversarial lenses

**Date:** 2026-08-29. **Rule tested:** short a newly listed Binance USDT-M perp at
the open 24 h after its first traded hour, hold 7 days, equal-notional BTC hedge,
taker fees both legs, funding included. **Verdict: the phenomenon is REAL; the
trade is NOT DEPLOYABLE.** Grade: **weak — do not fund.**

## 0. The original result was computed on a partial dataset

The round-5 run (2026-08-28 12:41) read the listing index while the archive
fetcher was still writing it: it saw **139 of 832 symbols**. Its headline
(+$7,219, PF 1.61, `short_after N=24 H=14 hedged`) is void. Backed up in
`tests/_round5_partial139/`. The script also had an `UnboundLocalError` (fixed)
introduced after that run.

**Re-run on the complete archive (820 usable listings, 2020-02 → 2026-07):**
pick becomes `short_after N=24 **H=7** hedged`; OOS (calendar folds 2+3) n=676,
net **+$18,005**, PF 1.26, WR 0.66, Sharpe 1.89, 266 bps/trade; both OOS folds
positive; every calendar year positive; top-3 removal 18,005 → 16,035; largest
single coin 2% of |net|. `H=14` — the old pick — is **negative** (−$3,345).

## 1. LEAKAGE — PASS

- Every OOS trade asserted: entry is the open exactly 24 h after the first traded
  bar, exit the open exactly 7 d later, side short, no gaps. **Zero violations.**
- t0 integrity: 40/40 of the hardest symbols (those with a funding stamp before
  their first kline) confirmed against the live S3 archive — no earlier monthly
  file exists. The early stamps are Binance's placeholder 0.0001/0.0 rows written
  at contract creation. Only 27 symbols have a real pre-t0 funding rate; dropping
  them leaves **+$16,040 (n=649)**.
- Survivorship: the sample includes delisted perps. Still-listed names alone are
  **+$16,742 (n=667)**; delisted names are 9 trades. Not a survivorship artefact.
- Duplicate base assets (BOB, CAT): dedup → +$17,668. No hedge-lookup drops.

## 2. STATISTICS — the effect is real, the *rule* is not selectable

**What passes.**
- Event study, no trading rule: 813 listings, excess return vs BTC from hour 24 to
  hour 192 has median **−8.9%**, mean −3.9%, negative in 67% of listings,
  **day-clustered t = −4.57** (542 distinct days), and is negative in **every
  year 2020–2026**. This is a genuine, strongly significant phenomenon.
- **Matched-date control (the test that killed most of the campaign):** short a
  random *seasoned* coin instead, same dates, same count, same BTC hedge, 300
  draws → mean +$5,455, max +$12,293, versus the listing book's price component
  **+$24,142**. **p(control ≥ actual) = 0.0000.** It is not generic short-alt beta.
- Breadth: 14/16 `short_after` grid variants are OOS-positive (the two losers are
  both H=14). 24/40 of the whole grid.

**What fails.**
- **Expanding-window walk-forward** (re-pick parameters each year on all prior
  listings only, which is what a live desk would do): 2021 −836, 2022 +610,
  2023 +4,269, 2024 +4,157, **2025 −5,538**, 2026 +872 → **total +$3,535 over 743
  trades = 47 bps/trade.** The −5,538 and −836 years are both years the optimiser
  picked H=14. The +$18k headline requires knowing H=7 in advance.
- Equal-event-count folds: fold-1 pick → fold 2 +6,028, **fold 3 −626.**
- Cluster-robust t = **1.83** (entry day) / **1.49** (month). Bootstrap
  P(net ≤ 0) = 0.034 iid, **0.063** by month.
- Concentration: removing the top 25 of 676 trades takes +18,005 → **+4,623**.

## 3. EXECUTION — survives friction, dies at size

- **Slippage: robust.** Break-even is **> 50 bps per side** on all four legs.
  At 10 bps/side the book is still +$15,338.
- **Timing: fragile.** Entry +2 h → 167 bps/trade, +6 h → 106, +24 h → 37 (from
  227 at h24). The alpha lives in a narrow window, which is authentic for an event
  effect but demands punctual execution.
- **Fill quality matters:** filling 25% of the way toward the bar's adverse
  extreme cuts +18,005 → +10,668; 50% → +3,167.
- **Funding is the market charging for the crowd:** the short pays **−91
  bps/trade** on average (−$6,137 of a $22,128 gross alt leg). Everyone is already
  short new listings.
- **Capacity is small and shrinking.** 1% of the thinner of the entry/exit hour:
  median $15.3k per event overall, but by year 2024 $34.9k → 2025 $24.1k →
  **2026 $2.4k**.
- **At size it inverts.** Sizing each event at min(target, 1%-of-hour):

  | target/event | 2024 | 2025 | 2026 |
  |---|---|---|---|
  | $10,000 | +17,285 | +44,448 | −7,892 |
  | $25,000 | **−5,856** | **−19,346** | −7,896 |
  | $50,000 | **−75,665** | **−239,024** | −35,263 |

  The sign flip is one short squeeze per year taking the full cap: PNUT −270% of
  notional (2024), STBL −285%, AVNT −194%, H −174% (2025), BILL −182% (2026).
  The $1k-per-event backtest only looked good because the position was too small
  to matter. **Hard stops do not fix it** — at $25k/event a +50% stop made 2025
  *worse* (−$135,891): it converts pump-then-collapse winners into realised losses.

## 4. DECAY — 2026 is gone

Per-trade bps, crypto listings only, 10 bps/side slippage:
2020 **917** · 2021 289 · 2022 246 · 2023 421 · 2024 273 · 2025 313 · **2026 22**.
Underlying median excess return vs BTC: −11% to −14% every year through 2025,
**−1.8% in 2026**. 26 of the 189 2026 listings are equity-linked perps
(AAPL/AMZN/…) which lose −169 bps; excluding them, 2026 crypto is +22 bps/trade —
inside the noise (t = 0.16) and below realistic friction.

## 5. Bottom line

The post-listing decay is the **only statistically real, non-beta, non-tail-driven
effect the entire 23-hypothesis edge hunt has produced**. It is also not a
business: it pays ~$25 per $1,000 event in a good year, has room for roughly
$2–15k per event, is concentrated in ~5 listings a week, carries −100% to −285%
single-trade squeeze risk, and its 2026 expectancy is statistically zero.

Do not allocate. Track it forward instead: log every new Binance/HL listing and
its day-1→day-8 excess return vs BTC for a quarter, and revisit only if the
median excess returns to ≤ −8% *and* per-event capacity recovers above $25k.

Files: `h_hl_listing_drift.{py,md,json}` (full-sample rerun),
`verify_hl_listing_drift_{leakage,execution,statistics}.{py,md,json}`,
`diag_2026.py`, `diag_deployable.{py,md,json}`, `diag_stop.{py,md,json}`,
`_round5_partial139/` (the void run). Lab rows: project `edge-hunt`,
strategy `hl_listing_drift`, variants `verify_*`.
