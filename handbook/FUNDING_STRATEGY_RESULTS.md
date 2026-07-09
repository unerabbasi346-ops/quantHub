# Funding-Carry Strategy — Real-Data Re-Verification, Backtest & Dashboard Test

**Prepared for:** QuantHub
**Status:** Real funding data ingested, live-verified, backtested through QuantHub's Step 3.7 MTM engine, and rendered on the dashboard. Results reported plainly — this informs keep/discard.
**Companion:** `handbook/LANCHESTER_BACKTEST_RESULTS.md` (same honest-evaluation discipline). Per Doc 00 §14.11.

---

## 1. Executive Summary

The `reference-funding-basis` perpetual funding-carry strategy now has a **real signal history** and a **real out-of-sample backtest** behind it, and it **renders fully on the dashboard**. But two structural facts dominate the interpretation:

1. **The Step 3.7 backtest measures the wrong thing for this strategy.** QuantHub's trade cycle marks positions to market (price P&L) but does **not settle funding cashflows** into P&L. A funding-carry strategy exists to harvest funding — so the +0.1486% the engine reports is the **price P&L of the funding-motivated positions, not the funding income itself.** The number is real but not the metric that matters.
2. **This was always a data-path proof, not an alpha strategy.** The plugin's own docstring says so ("NOT a real strategy… its sole purpose is to exercise the plumbing"). The evaluation confirms it behaves correctly as plumbing; it does not establish it as a keepable alpha.

**Keep/discard input: keep it as the reference/plumbing proof it was built to be; do not treat it as a validated alpha.** A genuine funding-carry evaluation is blocked on a platform gap (funding-cashflow settlement, §4).

---

## 2. What Was Verified (real, from the DB — not assumed)

| Item | Real value | Source |
|---|---|---|
| Funding rows ingested | **500** for BTC/USDT:USDT, 2026-01-24 → 2026-07-09 (8h periods) | `market_data.funding_rates` |
| Live-verify signal | 1 real VALID signal, value −0.059 (funding positive → lean short) | earlier `run_funding_rate_strategy.py` |
| Backtest signal history | **166 VALID signals**, 2026-01-24 → 2026-07-09 | `core.signals` |
| Backtest | 1 COMPLETED, +0.1486% return, 166 trades, final capital 100,148.56 | `analytics.backtests` |

Scripts: `scripts/run_funding_rate_strategy.py` (ingest + live-verify), `scripts/run_funding_backtest.py` (Step 3.7 backtest + funding diagnostic).

---

## 3. Step 3.7 Backtest Results (BTC/USDT:USDT, 2026-01-25 → 2026-07-10)

| Metric | Value |
|---|---|
| Bars processed | 166 |
| Signals generated | 166 |
| Orders filled | 166 (0 rejected) |
| Final position | −0.0037 BTC (net short — consistent with mostly-positive funding) |
| Realized P&L | +157.05 |
| Unrealized P&L | −8.49 |
| **Total return (price P&L)** | **+0.1486%** |
| Determinism hash | `2c17cb97ece8b36c…` (stable across re-runs) |

**Funding-income diagnostic** (computed directly from the real funding series — the piece Step 3.7 omits): over the 498 8h periods (295 positive, 203 negative), a constant-short position's gross carry was **+0.3956%** per unit notional; the upper bound if always on the collecting side was **+1.9437%**. But the reference `LinearConvictionSizer` holds only ~`value × 0.05 × capital` in notional, so the actual $ carry on these positions is tiny regardless. **Interpretation: the price-P&L backtest (+0.15%) is roughly flat; the funding income the strategy actually targets is not captured by the engine at all.**

---

## 4. Platform Gaps Surfaced (real findings)

**4.1 Funding cashflows are not settled into P&L.** The trade cycle (Step 3.5) applies price marks only; funding is stored as market data but never debited/credited to the position. A funding-carry strategy is therefore **un-evaluable** on its actual return source through Step 3.7 today. This is the single most important finding — a funding strategy cannot be honestly judged until §10.9.5 "Financing Costs" is wired into the position P&L.

**4.2 Signal monotonic-ts validation vs. backtest replay.** Signal recording enforces monotonically-increasing `ts` per (strategy, asset). A historical backtest replays *older* timestamps, so if a newer live signal already exists for the same strategy_id (or the backtest is re-run), the replayed signals are recorded **INVALID** ("before previous recorded signal"). The **economics are unaffected** (the cycle does not gate orders on validation_status — itself worth noting), but the audit trail is polluted. Practical consequence: **backtests must run against a clean signal history for that strategy_id.** This is data hygiene, not an economic error.

**4.3 (Enabling change made this work) Point-in-time funding in the backtest engine.** Before this work, `PointInTimeMarketDataView` served no funding, so a funding-driven strategy emitted zero signals in replay. Added an **additive, backward-compatible** extension (`PointInTimeMarketDataView.funding`/`as_of`, `BacktestEngine.funding`) that clamps funding to each bar's timestamp (§10.3.4). Existing spot/equity backtests are unchanged (funding defaults empty; reproducibility hashes preserved) and covered by new tests in `test_backtesting.py`.

---

## 5. Dashboard Render Test (real data behind it)

Rendered headlessly against the running dev server. **Everything renders; nothing is broken or crashed.**

**Dashboard (`/dashboard`)** — the `reference-funding-basis` card shows **RETURN (BACKTEST) +0.15%** (green) with a conviction sparkline, alongside the MA-crossover and Lancaster cards. Real.

**Detail page (`/strategies/{id}`)** — fully populated with real data:
- Header tiles: RECENT SIGNALS 100, BACKTEST RETURN 0.1486%.
- Stat row: SIGNALS 100, AVG CONVICTION −0.0137, VALID RATE 100% (100/100), FILL RATE 100% (166/166 orders), LATEST SIGNAL Jul 9.
- **Conviction curve** (signed conviction over time), **conviction distribution** histogram (min −0.098 / median −0.013 / max +0.080 — correctly short-skewed), **indicator overlay** ("Mean Funding Rate" series from signal metadata).
- **Backtest order flow**: Created 166 / Filled 166 / Rejected 0; Realized P&L 157.05, Unrealized −8.49.
- **Recent signals table** (all VALID, negative conviction) and **backtest results** (Total return 0.1486%, Fills 166, Final capital 100,148.56, determinism hash).

**Things that are empty — but honestly so (not bugs):**
- **MAX DRAWDOWN and WIN RATE read "Not yet computed"** on every strategy card. Correct: `BacktestResult` (Step 3.7) deliberately does not compute the full metric suite (no per-step equity curve — F-18/S-5 deferred). The UI labels the absence honestly rather than fabricating a zero.
- **"RECENT SIGNALS 100" vs the 166-signal backtest:** the signal feed is capped at the recent 100 by the API, so the conviction curve/distribution/avg-conviction reflect the most-recent 100 of 166 signals, while fill-rate/backtest tiles correctly show 166. Labeled "RECENT", so defensible, but the 100-vs-166 split could momentarily confuse.
- Dashboard portfolio/executions/risk widgets show the main `quanthub-v1` portfolio, not the isolated BACKTEST portfolios — expected (those widgets are portfolio-scoped), not a funding-strategy gap.

---

## 6. Conclusion (keep or discard)

**Keep `reference-funding-basis` as what it is — the perpetual data-path / plumbing reference proof — and do not promote it to a real alpha.** It ingests real funding, emits real signed signals, backtests deterministically, and drives the full dashboard correctly, which is exactly the plumbing it was built to prove. But its actual economic thesis (harvesting funding) **cannot be evaluated** through Step 3.7 until funding-cashflow settlement (§4.1) exists, and its price-P&L backtest is ~flat. The most valuable output of this exercise is not the strategy's number — it is the two concrete platform gaps (§4.1 funding P&L, §4.2 signal/backtest hygiene) it surfaced, plus the point-in-time funding backtest capability (§4.3) it drove into the engine.
