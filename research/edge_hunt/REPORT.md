# Edge hunt — final report (rounds 1–4)

Written 2026-08-28. Scope: `research/edge_hunt/` only. Every number below is **net of fees** from the fee model in `common.py` (`FEES`: Hyperliquid taker 4.5 bps/side, maker 1.5 bps/side; CME micros $2.24–3.74 round trip incl. 1 tick/side; ES $6.80, NQ $7.80), from **walk-forward out-of-sample** runs (parameters chosen on the earliest fold only), with signal at bar *t* and fill at *t+1* open or a limit verifiably traded through. Every variant is in quant-lab (`/Users/molt_bot/quant-lab/lab.db`, project `edge-hunt`, 2,604 rows across 22 strategies, plus one smoke_test row).

Verdict rule used by every test: **edge** = OOS net > 0 AND OOS PF >= 1.2 AND OOS n >= 60 independent decisions AND every OOS fold > 0 AND survives shuffle + parameter neighbours + top-3-trade removal. **weak** = positive but fails exactly one. Otherwise **none**.

## 1. Bottom line

**No hypothesis reached "edge". Zero of 22.** Three were graded "weak" by their own reports; the adversarial verify scripts (`tests/verify_*.py`) reduced two of them to zero or to market beta, and round 4 refuted the third on eight years of survivorship-aware data:

| weak candidate | author OOS | after skeptics | what it really is |
|---|---|---|---|
| `overnight_drift` (long CME micros 16:00->09:00 ET) | +$38,368 / 1,592 nights / PF 1.23 | **+$24,703, PF 1.15** after removing Yahoo roll jumps and adding 1 tick/side (`verify_exec_D_roll_adj_plus1tick`); +$15,404, PF 1.10 if every roll-week leg is dropped | Long index/gold beta in an up-trending sample. Random 17-hour windows earn the same; overnight-minus-intraday is insignificant on MNQ/MES/MYM (p 0.35–0.81) and MGC's p goes 0.032 -> 0.145 once roll legs are dropped. |
| `mean_reversion_zscore` (1h, HL 50 perps, maker fade of \|z\|>3) | +$1,214 / 1,754 / PF 1.08 | **+$140, PF 1.01** with realistic fills, slippage and funding (`1h_exec_realistic_combined`); -$154 at a 5 bps fill margin; bootstrap P(net<=0) = 0.16–0.31 | Recovers most of the adverse selection of a resting limit; nothing left after costs. |
| `xsec_mom30_rev1_hedged` (long z(30d)-z(1d) alt book, BTC-hedged) | +$3,738 / 73 / PF 1.74 | ex-top-3 trades **+$294** (p 0.43); signal composed from the two best round-1 OOS cells (hidden search); round 4 on 2019–2026 Binance panel: **-$89,156 OOS, negative every year 2022–2026** | Three lottery tickets (PUMP, CASHCAT, ACE) on a 4-name book. Dead. |

The best *corrected* positive number in the whole campaign is therefore the overnight micro-futures basket, and it is not an alpha: the same nights bought as plain 16:00->16:00 buy-and-hold made **more** (+$42,476 vs +$38,368 raw, `verify_stats_bh_16_16_L_all`). Everything else is zero or negative once fees, fills, roll splices, timestamp artefacts, survivorship and post-hoc selection are removed.

## 2. Ranking of every hypothesis tested

Ranked by skeptic-corrected OOS net, then fold consistency and robustness. "OOS" = walk-forward folds 2+3 (or later calendar years) with fold-1-selected parameters. n = OOS decisions.

| # | key (round) | market / rule (one line) | OOS n | OOS net (USD) | PF | OOS folds | corrected / skeptic number | verdict | report |
|---|---|---|---|---|---|---|---|---|---|
| 1 | overnight_drift (1) | long MNQ+MES+MYM+MGC 16:00->09:00 ET, 1 ct each, market at bar open | 1,592 | +38,368 | 1.23 | +13,664 / +24,704 | +24,703 PF 1.15 (roll-adj +1 tick); shuffle vs random 17h windows: 67th pct only; B&H 16->16 = +42,476 | weak (beta) | `tests/h_overnight_drift.md` |
| 2 | mean_reversion_zscore (1) | HL 1h, 50 perps: \|z(2-bar ret)\|>3 -> maker limit at close, exit taker at 0.5 retrace or 4 bars; $1k/trade | 1,754 | +1,214 | 1.08 | +1,526 / -311 | +140 PF 1.01 realistic; rolling WF (pick on f2 -> f3) -1,026; rank-51–100 universe -467 | weak -> ~0 | `tests/h_mean_reversion_zscore.md`, `verify_mean_reversion_zscore_*.json` |
| 3 | xsec_mom30_rev1_hedged (2) | HL PIT top-50: long top-20% of z(30d)-z(1d), weekly, $1k/name, BTC short hedge | 73 (53 long) | +3,738 | 1.74 | +603 / +3,135 | ex-top-3 +294; realized-only +725; 1-day signal lag +1,548; **round 4 long-history -89,156 (PF 0.58)** | weak -> none | `tests/h_xsec_mom30_rev1_hedged.md`, `tests/h_xsec_mom_longhist.md` |
| 4 | latpfn_reversal_fade, Part A (3–4) | CME mirror of saved LaT-PFN lagged-mode trades: **invert** conf>=0.52 calls, 1 ct | 114 | +971 | 1.32 | -457 / +1,428 | MNQ +1,368 carries it (MBT -38, MES -78, MYM -281); shuffle p 0.072; 60 days only | none | `tests/h_latpfn_reversal_fade.md` |
| 5 | cme_weekend_gap_btc (4) | BTC: after \|Fri 21:00->Sun 22:00 UTC gap\|>0.5%, go **with** the gap 48h, $10k, HL taker | 202 | +6,234 | 1.18 | +1,226 / +5,008 | top-3 removal -> +316 (PF 1.01, fold 2 -4,691); random-window p 0.21; weekday control same sign; real HL bars (17 weekends) -671; 2025–26 negative | none | `tests/h_cme_weekend_gap_btc.md` |
| 6 | month_end_rebalance_flow (3) | ES+NQ long T-1 -> T+4 around month end, 1 ct, daily settlement fills | 160 | +96,684 | 1.23 | +101,101 / -4,416 | below pro-rata drift baseline (+125,027) and random same-length windows (p 0.66); post-hoc arm B +151k has random-window p 0.21 | none | `tests/h_month_end_rebalance_flow.md` |
| 7 | premium_dislocation_revert (3) | HL: long a -2.5 ATR flush bar whose premium <= -30 bps, maker, exit on normalisation | 7 | -210 | 0.19 | -97 / -112 | comparison cells (not the hypothesis): flush with *quiet* premium +397 PF 1.29 (fold 3 -39); market-wide flush +540 PF 2.53 on **12 signal hours** (t 1.73) | none | `tests/h_premium_dislocation_revert.md` |
| 8 | btc_alt_leadlag (1) | HL 15m: after \|BTC 6-bar ret\|>=1%, long/short 5 laggard alts 6 bars, taker | 217 | +225 | 1.10 | -449 / +674 | shuffle p 0.17 / 0.31; leaders beat laggards; 5m arm -966 | none | `tests/h_btc_alt_leadlag.md` |
| 9 | polymarket_5m_updown_maker (4) | rest bids at market mid -0.15 in first 60 s of BTC 5m Up/Down, fill only on trade-through | 54 | +62 | 1.13 | +30 / +32 (n=3) | top-3 removal -55; 10-s settlement guard -33; 191/192 grid cells negative OOS; ETH-5m -15, BTC-15m -21 | none | `tests/h_polymarket_5m_updown_maker.md` |
| 10 | perp_spot_basis (1) | HL 50 perps: fade 7d z-score of premium, 24h hold (basis BTC/ETH sub-arm: +95 taker / +117 maker on 36 trades) | 3,619 | -3,915 | 0.94 | +1,518 / -5,433 | maker -3,919; long-only +2,716 but random-timing null +2,288 (p 0.42); basis arm fold 2 negative, ETH carries all | none | `tests/h_perp_spot_basis.md` |
| 11 | flush_reversal_long (2) | HL 1h PIT top-50: long after -2% high-vol bar, bid 0.25 x range below close, 12-bar hold | 26 | -142 | 0.72 | +137 / -278 | shuffle pct 0.03 (worse than random); arm B -593; BTC-hedged -180; fold-1 signal was market-wide beta | none | `tests/h_flush_reversal_long.md` |
| 12 | xsec_momentum (1) | HL snapshot-50: long top / short bottom 10% by 30d return, daily | 231 | -178 | 0.98 | -49 / -129 | universe survivorship-biased; illiquid names -3,331 | none | `tests/h_xsec_momentum.md` |
| 13 | orb_crypto (1) | HL 15m BTC/ETH/SOL: fade 60-min opening range, 1.5x target, taker | 191 | -570 | 0.91 | -543 / -27 | stops -5,191; fee = 10% of 1R | none | `tests/h_orb_crypto.md` |
| 14 | volume_shock_reversal (1) | HL 15m: fade 8x volume / 2xATR wick bar, stop at wick, taker | 704 | -695 | 0.82 | -246 / -448 | OOS gross ~ 0; shuffle pct 0.80; 0/10 neighbours positive | none | `tests/h_volume_shock_reversal.md` |
| 15 | range_edge_maker_fade (2) | HL 15m/1h 10 coins: rest limits at opening-range edge +0.25w, maker | 392 / 1,039 | -558 / -697 | 0.66 / 0.84 | -190/-368 ; -801/+104 | level-shuffle pct 0.45; stops dominate | none | `tests/h_range_edge_maker_fade.md` |
| 16 | funding_xsec_carry (2) | HL PIT: long bottom / short top decile by 72h funding, 3-day max hold, maker | 348 | -1,866 | 0.83 | -470 / -1,396 | carry +728 vs price -2,487: funding is fair compensation for drift; shuffle p 0.90; all 24 cells negative | none | `tests/h_funding_xsec_carry.md` |
| 17 | funding_extreme (1) | HL 1h: contrarian on top/bottom-10% 1h funding, 24h hold | 1,911 | -2,254 | 0.94 | +823 / -3,077 | funding $0.49/trade vs fees $0.90; shuffle p 0.63; 1/7 neighbours | none | `tests/h_funding_extreme.md` |
| 18 | poly_lastminute_1s (3) | Polymarket BTC 5m: take stale asks in last 90 s vs Binance 1s model (L>=6 s) | 2,657 | -2,255 | 0.97 | -5,543 / +3,288 | L=1–2 "profit" (+$11.6k) was look-ahead: print stamps are settlement times; 14/18 honest cells lose | none | `tests/h_poly_lastminute_1s.md` |
| 19 | crypto_seasonality (1) | BTC/ETH 1h: hour-of-day / weekend / session rules, taker | 138 | -2,980 | 0.77 | -4,671 / +1,692 | zero-fee OOS also negative; clock-shift shuffle pct 0.54 | none | `tests/h_crypto_seasonality.md` |
| 20 | gold_session (1) | MGC 1h: short London-PM window 15->17 ET, 1 ct | 400 | -4,242 | 0.88 | -3,908 / -334 | selected window ranks 17/24 among same-duration windows | none | `tests/h_gold_session.md` |
| 21 | latpfn_reversal_fade, Part B (3–4) | HL 1h, 20 coins: trade LaT-PFN direction where it disagrees with 24-bar trend, H=12, taker | 5,184 | -16,708 | 0.74 | -8,407 / -8,301 | worse than random bars (p 1.00); raw hit rate 0.49–0.51; INV_HI inverse arm +8,595 both folds positive but its fold 1 was -1,983 -> never selectable, post-hoc | none | `tests/h_latpfn_reversal_fade_hl_1h.md` |
| 22 | xsec_mom_longhist (4) | Binance spot 2019–2026, 655 pairs incl. delisted: long top-20% z(30d)-z(1d), 14d rebalance, $1k/name | 1,720 (122 rebalances) | -89,156 | 0.58 | -29,431 / -13,972 / -17,063 / -38,765 / -16,528 | 0/69 variants positive; 5 sd worse than random buckets; Q5-Q1 spread negative every OOS year | none | `tests/h_xsec_mom_longhist.md` |

Also present but never run to a result: `tests/h_xsec_wide_book_altshedge.py` (round 3, alt-basket-hedged wide-book version of #3; superseded by #22). Two Polymarket hypotheses (#9, #18) and two LaT-PFN parts (#4, #21) are counted separately because they were pre-registered separately.

## 3. Candidate detail

For each: rule, execution, horizon, instruments, OOS after fees, skeptics' numbers, what it would earn per month at a stated size, and risks. Monthly figures divide OOS net by the OOS window length; they are descriptive, not forecasts.

### 3.1 overnight_drift — rank 1, "weak" (beta, not timing)

- **Rule.** Buy 1 contract at the open of the 16:00 ET hourly bar, sell at the open of the 09:00 ET bar next session, every session, no filter (`session=on_16_9, side=+1, filt=all`, selected on fold 1 for every instrument; MGC's own pick was `no_fri`). Data: yfinance 1h continuous front-month `MNQ=F, MES=F, MYM=F, MGC=F`, 2024-04-05 -> 2026-08-27; folds = calendar thirds; OOS = 2025-01-21 -> 2026-08-27 (19.2 months).
- **Execution.** Market at bar open, `cme_fee` round trip (commission + 1 tick/side). Horizon 17 h. Instruments MNQ, MES, MYM, MGC.
- **OOS (author).** Basket n=1,592, **+$38,368**, PF 1.23, WR 0.56, folds +13,664 / +24,704, maxDD 13,003. Per instrument: MNQ +13,428 (PF 1.24), MGC +11,096 (`no_fri`; `all` = +21,026), MES +3,319 (PF 1.12), MYM +594 (PF 1.03, fold 2 -942).
- **Skeptics.** (a) *Statistics* (`verify_overnight_drift_statistics.json`): iid bootstrap p 0.006, night-cluster p 0.030, block p 0.015; ex-top-3 +32,010; 16/20 months positive; n_eff ~ 621 (avg pairwise corr 0.52); **excess over pro-rata buy-and-hold: MNQ t 0.11, MES -0.45, MYM -0.74, MGC 0.92 — none significant**; White reality-check p 0.18; 16:00->16:00 buy-and-hold at the same execution +42,476. (b) *Execution* (`verify_overnight_drift_execution.py`, lab rows `verify_exec_*`): Yahoo's continuous series is un-adjusted and rolls inside the overnight window, so the long books each quarterly calendar basis as PnL — 11,026 USD of OOS gross identified as roll jumps. Roll-adjusted +27,290 (PF 1.16); **roll-adjusted +1 tick/side +24,703 (PF 1.15, folds +7,861 / +16,842; MNQ +10,295, MES +949, MYM -904, MGC +14,363)**; +2 ticks +22,116. (c) *Leakage* (`verify_overnight_drift_leakage.py`, lab rows `verify_leak_*`): dropping the 159 legs overlapping roll / contract-mixing windows -> +15,404 (PF 1.10; MNQ +4,894, MES -151, MYM -1,699, MGC +12,361); paired overnight-minus-intraday on clean legs: MNQ t 0.20, MES -0.33, MYM -0.85, **MGC t 1.46 p 0.145** (raw 2.15 p 0.032).
- **Sanity.** Shuffle: the 16->9 window beats only 67% of 21 random same-length windows (basket), 24% for MES/MYM. Neighbours +/-1 h all positive (as expected for beta). Sub-periods: 2025-04 -6,350, 2026-03 -4,457 (raw month PnL).
- **Earnings.** Corrected basket ~ **$1,290/month per 1-lot set** (4 contracts, $171k notional at 2026-08-27 closes: MNQ $59.3k, MES $38.7k, MYM $26.8k, MGC $46.6k); MNQ+MGC only ~ $1,285/month on $106k notional. On the project's `default_equity: 50000` that is ~2.6%/month against a corrected basket maxDD of $14,477 (~29% of $50k). Liquidity is not the limit for micros (MNQ median 2.76M contracts/day, MES 1.04M, MYM 129k over the last 60 sessions; Yahoo's MGC volume field, 126/day, is not credible and MGC capacity is unverified here).
- **Risks.** It is long beta held 69% of the time: a down-trending index or gold regime turns it negative (fold 2 for MYM and MES already are after correction). The live system's Apex account **cannot hold overnight** (`config/settings.yaml: prop_firm.flatten_eod: true, flatten_time 16:55`), so this needs a non-prop account. Real rolls cost the calendar basis the backtest earned. Gap risk with no stop.

### 3.2 mean_reversion_zscore (1h) — rank 2, "weak" -> zero after realistic execution

- **Rule.** z = 2-bar return / rolling std(100); when |z| > 3 (and bar range >= 1.0 x ATR), place a limit at the signal close against the move; fill only if bar t+1 trades through it; exit taker at 0.5x retrace of the move or at the open 4 bars later. $1,000 notional, one position per coin, 50 HL perps (end-of-period top-50 snapshot), 2026-01-31 -> 08-27. Horizon <= 4 h.
- **OOS (author).** n=1,754, **+$1,214** (+6.9 bps/trade), PF 1.08, WR 0.57, folds +1,526 / -311. 15m version -869 (PF 0.92).
- **Skeptics.** *Execution* (`verify_mean_reversion_zscore_execution.json`): fill needs 2 bps trade-through + open-through as taker + 2 bps & half-spread exit slippage + real funding -> **+$140, PF 1.01, folds +1,027 / -887**; 5 bps fill margin -> -154; liquid-only +433. *Statistics*: bootstrap P(net <= 0) 0.16 (iid) to 0.31 (week clusters); ex-top-10 trades -26; drop best week -321; months: Apr +472, May 0, Jun +1,800, Jul +393, Aug -1,450. *Leakage* (lab rows `1h_verify_*`): rolling WF (select on fold 2, test fold 3) **-1,026**; point-in-time top-50 universe +937 (fold 3 -993); coins ranked 51–100 -467; delisted +360 (n=160). Shuffle passes only against an adverse-selection baseline (random resting limits lose -4,682), which is the wrong bar.
- **Earnings.** Realistic +$140 over 4.6 months ~ **$30/month** on $1k/trade with mean 2.2 (max 26) concurrent positions — i.e. ~0.1%/month on a $26k reserve. Not deployable.
- **Risks.** Fold 1 (Feb–Apr) was negative for every grid cell; the result is regime luck plus queue-position assumptions that cannot be verified from candles.

### 3.3 xsec_mom30_rev1_hedged — rank 3, "weak" in round 2, refuted in round 4

- **Rule.** At 23:00 UTC, score = z(30d return) - z(1d return) across the point-in-time HL universe (24h vol >= $5M, top-50 by 30d vol); long top 20% (~4 names), $1k each, fill at the 00:00 bar open, weekly rebalance, equal-notional BTC short hedge. Horizon 1 week+.
- **OOS (author).** n=73 rows (53 longs + 20 hedge intervals), **+$3,738**, PF 1.74, folds +603 / +3,135, shuffle p 0.00, 4/4 neighbours positive, all 7 rebalance phases positive (mean +1,808).
- **Skeptics.** *Statistics* (`verify_xsec_mom30_rev1_hedged_statistics.json`): PUMP +1,727, CASHCAT +1,035, ACE +683 = 92% of net; **ex-top-3 +294, PF 1.06, p 0.43**; 20 weekly decisions, t 1.39; hidden search: the signal was assembled from the two best round-1 OOS cells (`L1_R7_q0.2_rev`, `L30_R7_q0.2_mom`) on the same folds, so folds 2+3 are not out-of-sample for the hypothesis choice. *Execution*: realized-only (open positions excluded) +725, PF 1.16; worst-fill +2,408. *Leakage*: fills and signal alignment clean (0 bad rows); 1-day signal lag +1,548 (fold 2 +2). **Round 4** (`h_xsec_mom_longhist.md`): same structure on 655 Binance USDT pairs incl. 249 delisted, IS 2019–21 (+54.9k, all 2021), OOS 2022 -> 2026-08: **-$89,156 on a ~$20k book, negative every year, 0/69 variants positive, 5 sd below random buckets; the 2026 slice of the panel is -22.0k.**
- **Earnings.** Round 2 would have read ~ $800/month on a ~$5k book; the honest expectation from round 4 is ~ **-$1,600/month per $20k book**.
- **Risks.** Long-alt beta with negative drift outside 2020–21/2023; funding on hyped longs makes it worse on perps.

### 3.4 latpfn_reversal_fade, Part A (CME mirror) — rank 4, "none"

- **Rule.** Take the saved LaT-PFN lagged-mode backtest trades (300 trades, 60 days of 5m bars to 2026-08-26, MNQ/MES/MYM/MBT) and trade the **opposite** direction when model confidence >= 0.52, closing when the model's trade closes; 1 contract, `cme_fee`. Selected on the first third of trades.
- **OOS (thirds 2+3).** n=114, **+$971**, PF 1.32, WR 0.47, folds **-457 / +1,428**; MNQ +1,368, MES -78, MYM -281, MBT -38; top-3 removal +1,059; shuffle (sides permuted) p 0.072; coin-flip p 0.11.
- **Earnings.** ~ $740/month per 1-contract mirror over the 40-day OOS, all from MNQ. Meaningless at this n and span.
- **Risks.** 60 days, four instruments on the same days (effective n far below 114), one fold negative, one instrument. The HL half of the same hypothesis (Part B, rank 21) is decisively negative, and its only positive cell (`INV_HI`) was unselectable on fold 1.

### 3.5 cme_weekend_gap_btc — rank 5, "none"

- **Rule.** Gap = Sun 21:00 close / Fri 20:00 close (UTC) - 1 on Binance BTCUSDT 1h (2018 -> 2026-08). Fold-1 pick: **continuation** arm — enter with the gap at the Sun 22:00 open if |gap| > 0.5%, no stop, exit after 48 h. $10k, HL taker fees.
- **OOS.** n=202, **+$6,234** (+31 bps/trade), PF 1.18, folds +1,226 / +5,008; all 16 same-arm neighbours positive. The fade arm (the pre-registered idea) loses in all 16 cells and every fold.
- **Skeptics/sanity.** Top-3 removal -> **+316, PF 1.01, folds -4,691 / +5,008**; random-window shuffle p 0.21; side shuffle p 0.15; weekday Tue/Wed/Thu control shows the same sign (+4,953 OOS) -> generic 48 h momentum after a >0.5% move; by year 2021 -2,199, 2025 -805, 2026 -408; real Hyperliquid perp bars (17 weekends) **-671**; MBT=F 1 contract -1,143.
- **Earnings.** ~ $90/month per $10k notional over 69 OOS months; ~ $5/month ex-top-3.
- **Risks.** Gap-fill rates do rise on weekends (38% vs 25% within 24 h for |gap| > 1%), but unfilled gaps run far enough that fading loses; the continuation arm is three trades and a bull market.

### 3.6 month_end_rebalance_flow — rank 6, "none"

- **Rule.** ES+NQ pooled; arm A: long from T-1 close to T+4 close (k=4) every month, 1 contract, daily settlement fills (roll days verified not to touch the window). Folds 2016–19 / 2019–23 / 2023–26.
- **OOS.** n=160, **+$96,684**, PF 1.23, folds +101,101 / **-4,416**. Gates: pro-rata drift over the same sessions +125,027 (excess -28k); 1,000 random same-side same-length windows mean +141,862 (p 0.66). Micros MES/MNQ OOS -784 / -683.
- **Post-hoc.** Arm B (`B_thr3_k4`, long T-3 after MTD <= -3%, short T-3 -> T-1 after MTD >= +3%) +151,356, PF 1.44, both folds positive, MTD-permutation p 0.04 — but random-window p 0.21 and all of it is the 43 "long after a >=3% drawdown" legs; the short leg loses in-sample. Chosen after seeing OOS.
- **Earnings.** ~ $1,200/month on 1 ES + 1 NQ, which is less than holding them.
- **Risks.** Pure equity beta over 5 sessions; 16:00 ET fills lower the daily-close numbers by 0–25%.

### 3.7 premium_dislocation_revert — rank 7, "none"

- **Rule.** HL 1h, 138 coins (PIT >= $5M): long a flush bar (<= -2.5 ATR24) whose end-of-bar premium <= -30 bps, maker at the close, exit when premium normalises / 6 h. OOS **n=7, -$210**, shuffle p 0.955. The premium is dislocated on 18 of 425 flushes, and those flushes *continue* (-97 to -879 bps forward).
- **Spawned, untested as a hypothesis.** Flush with quiet premium (`spot_led`): n=272, +397, PF 1.29, folds +436 / -39, shuffle p 0.005, hour-level t 0.82. Market-wide flush (>=5 coins same hour): n=149, +540, PF 2.53, folds +207 / +333, but **12 signal hours**, t 1.73; fills assumed for full size in the most stressed hours. Effective rule in both: bid at the flush close, sell at open t+2 (2.3–2.7 h hold). ~ $117/month on $1k/name. Needs a fresh pre-registered test scored per hour with a fill haircut.

### 3.8 The rest (ranks 8–22) — "none", nothing to size

- **btc_alt_leadlag**: 15m +225 (PF 1.10, shuffle p 0.17/0.31), 5m -966; leaders beat laggards and the all-alt basket beats both -> generic BTC spillover, long-only, 4 names.
- **polymarket_5m_updown_maker**: +62 on 54 windows; 191/192 cells negative; resting bids are hit only after Binance has moved against them; maker fee 0 is two orders of magnitude smaller than adverse selection. Closes the Polymarket line together with **poly_lastminute_1s** (-2,255; the +$11.6k pre-registered result was look-ahead from settlement-time stamps; the market's last-90-s price has Brier 0.068 vs the model's 0.108).
- **perp_spot_basis**: -3,915 (maker -3,919); long-only +2,716 is beta (null +2,288). Basis sub-arm on BTC/ETH +95/+117 on 36 trades, fold 2 negative, ETH-only.
- **flush_reversal_long**: -142 (n=26), shuffle pct 0.03; the descriptive +136/+50/+123 bps that motivated it was market-wide beta.
- **xsec_momentum**: -178; **orb_crypto**: -570; **volume_shock_reversal**: -695 (gross ~ 0, fees 634); **range_edge_maker_fade**: -558 / -697; **funding_xsec_carry**: -1,866 (carry +728, price -2,487: funding is fair compensation); **funding_extreme**: -2,254 (funding $0.49 vs fees $0.90 per trade); **crypto_seasonality**: -2,980 (also negative at zero fees); **gold_session**: -4,242 (window ranks 17/24); **latpfn_reversal_fade Part B**: -16,708 (worse than random bars, raw hit rate 0.49–0.51 at every horizon); **xsec_mom_longhist**: -89,156.

## 4. What the campaign established (cross-cutting findings)

1. **Every positive crypto number on the 2026 HL sample was beta or three names.** Long-only arms of five different hypotheses (funding_extreme, perp_spot_basis, flush, xsec_momentum, xsec_mom30) were positive and each failed a random-timing/random-bucket null on the same coins. Round 4's 8-year panel shows the top-100-by-volume alt basket loses ~2.5%/week outside 2020–21 and 2023.
2. **Fees are rarely the binding constraint; information is.** Maker arms were within $100 of taker arms in xsec carry, funding_extreme and range_edge (hourly bars almost always trade through their open); Polymarket maker fee is zero and still loses; month-end fees are 0.2–0.5 bps vs 20–40 bps gross. The binding constraints were adverse selection, look-ahead in timestamps, roll splices and regime.
3. **Data artefacts found and fixed:** yfinance continuous futures roll inside hourly bars (11k of 38k overnight gross); Polymarket data-api print stamps are Polygon settlement times (~3–5 s late, fat tail); end-of-period HL top-50 snapshot is survivorship-biased (PIT universes were built for rounds 2–4); HL hourly funding index carries ms offsets.
4. **LaT-PFN itself carries no directional information at 1h on HL** (hit rate 0.499–0.513, n ~ 11.7k) and the CME mirror inverse is one instrument for 60 days.

## 5. How to exploit the top candidate (overnight_drift), if it is exploited at all

Be clear about what this is: a scheduled long in micro index/gold futures that earned ~ $1.3k/month per 1-lot set OOS after corrections, with no evidence that the *timing* adds anything over holding. The plan below is what it takes to run it correctly inside `/Users/molt_bot/latpfn-trading`; the honest alternative is to not run it and simply hold beta elsewhere.

**Instruments and rule.** MNQ and MGC only (MES ~ 0, MYM negative after corrections). Long 1 contract each from 16:00 ET to 09:00 ET next session, every session, no filter (`vix_ge` cut fold 2 to -2,598 in the author's grid; `no_fri` halves basket net).

**Account.** Not the Apex account: `config/settings.yaml` `prop_firm.flatten_eod: true` / `flatten_time: "16:55"` and Apex trailing-drawdown rules forbid the hold. Use a non-prop Tradovate cash account through `execution/tradovate_client.py` (`place_market_order`, `flatten_position`, `find_contract`) or the existing TradersPost webhook (`execution/traderspost_client.py`); `tradovate.mode` is currently `demo` — run demo first.

**Data feed.** Do not drive live decisions from yfinance continuous symbols. Use Tradovate market data (`tradovate.md_url` websocket) on the specific front-month contract resolved by `orchestrator/main_loop._resolve_contracts()`; for monitoring, compare fills against the ETF proxies the verifier used (QQQ/GLD close->open).

**Orders.** Entry: market order at 16:00:00 ET on the front month (Globex equity halt is 16:15–16:30 ET; MGC trades through). Exit: market order at 09:00:00 ET. Rolls: never inside the overnight window — roll during RTH on the Thursday before the equity roll (`EQ_EXPIRY` dates in `verify_overnight_drift_leakage.py`: 3rd Friday of Mar/Jun/Sep/Dec) and for MGC before the bi-monthly expiry; expect to pay the calendar basis (~0.7–1.0% per equity roll, 0.65–1.65% per MGC roll) that the backtest booked as profit.

**Sizing.** 1 contract each per $50k of equity (`execution.default_equity: 50000`): notional $106k, corrected OOS maxDD $14.5k for the 4-lot basket (~ $15k for MNQ+MGC per-instrument maxDDs 6.7k + 8.5k). Scale linearly only; liquidity is not the constraint at this size (MNQ 2.8M contracts/day). Disable the LaT-PFN signal path for these two symbols while the overnight position is on (`risk.max_net_mes_equivalent` / `portfolio_exposure.py` would otherwise double-count).

**Kill-switch (all four, wired through `risk/circuit_breaker.py` and `risk/manager.py`).**
1. Daily: existing `CircuitBreaker` with `max_daily_loss_pct` (3%) and `max_daily_loss_usd` — trip -> `flatten_position()` and no entry that day.
2. Drawdown: halt the strategy when cumulative net from equity peak < -$15,000 per 1-lot set (the corrected OOS maxDD); require a manual restart.
3. Expectancy: after 60 nights, if rolling 60-night net < 0 **and** the roll-adjusted 16->9 return is below the same-night 16->16 buy-and-hold return, stop — the only reason to hold overnight instead of always is that ratio, and it was <= 1 for MNQ/MES/MYM in the verify.
4. Data/ops: no entry if the last received bar is older than 10 min at 15:59 ET, if the resolved contract is within 3 sessions of expiry, or if `monitoring/health_monitor` heartbeat is stale; positions reconciled at 09:05 ET via `_reconcile_positions()`.

**Record-keeping.** Log every fill to quant-lab (`common.record_to_lab`, strategy `overnight_drift`, variant `live_*`) so live nights can be compared with `verify_exec_D_roll_adj_plus1tick` after 60 nights.

## 6. What is and is not proven

**Proven (to the campaign's standard):**
- 21 of 22 hypotheses have no out-of-sample edge after fees on the data cached here; most are negative before fees or fail a random-timing null.
- Long overnight micro-futures was positive OOS over 19 months after roll and slippage corrections (+$24.7k on 4 lots, both OOS folds positive, block-bootstrap p 0.015 on the raw series), **and** it is statistically indistinguishable from holding the same beta continuously.

**Not proven:**
- That any of the three "weak" results has positive expectation net of everything going forward. mean_reversion_zscore is +$140 with a 0.16–0.31 chance of being <= 0; xsec_mom30 was refuted; overnight_drift's timing component is insignificant on every instrument once roll legs are removed (best case MGC p 0.145).
- The two spawned crypto ideas (market-wide flush 1–2 bar fade; long-Q1/short-Q5 reversed combo on HL with funding) — they are observations made after seeing OOS tables and have not been pre-registered or tested.
- Anything sub-5-second on Polymarket: it cannot be tested on the public prints feed at all (settlement stamps); it needs a live book/Chainlink recorder.
- Capacity beyond 1–10 micro contracts (fine) or beyond ~$1k/name on HL alts below $10M/day (thin-bucket results were where the round-2 lottery tickets lived).

Sources: every `tests/h_*.md` and `tests/verify_*.{py,json}` listed in the tables above; `data/MANIFEST.md`; quant-lab `lab.db` rows cited by variant name.
