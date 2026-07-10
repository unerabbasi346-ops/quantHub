# Lancaster ML Strategy — Integration Build & Out-of-Sample Backtest Results

**Prepared for:** QuantHub
**Status:** Built, registered, live-verified, and backtested out-of-sample through QuantHub's own MTM engine. Results below are real and reported honestly, good or bad.
**Companion doc:** `handbook/LANCHESTER_INTEGRATION_INVESTIGATION.md` (the investigation and the §8 decisions this build executed).
**Governing:** P-1 (Strategy Independence), Doc 14 §10.3 (Backtesting), §10.6.4 (Signal Generation). Per Doc 00 §14.11.

---

## 1. Executive Summary

The PROJECT_LANCHESTER Random-Forest momentum model was wrapped as a real QuantHub strategy and backtested **out-of-sample** through QuantHub's own mark-to-market Step 3.7 engine (not Lancaster's own forensically-broken backtester). Across the 10-perp universe over ~11 months of out-of-sample data (2025-08-01 → 2026-07-09):

- **Long/short (owner's regime, Decision 3): aggregate +0.022% — essentially breakeven.** 5/10 sleeves positive, best +0.694% (DOGE), worst −0.558% (BTC). Net PnL $216.87 on $1.0M deployed.
- **Long-only (the paper's original validated regime): aggregate −0.368% — a net loss.** Only 2/10 sleeves positive; worst APT −0.982%. Notably **worse** than long/short, i.e. on this window the (flagged, extrapolated) short leg *helped*.

**The honest read: no meaningful edge out-of-sample, before costs.** And "before costs" is load-bearing — the strategy traded on **343 of 343 bars per sleeve** (it re-sizes every day), and QuantHub's Step 3.7 fills are zero-slippage/zero-commission by design (F-16). A strategy that flips its position daily and only reaches breakeven *before* costs would lose money once real perpetual trading costs (spread, taker fees, funding) are applied. This result must also be read under the **survivorship-bias caveat carried over from the investigation doc (§6 below), which remains real and unaddressed.**

This is a successful *integration* (the model runs as a real, governed QuantHub strategy, producing real recorded signals through the real pipeline) and an *honest, unflattering performance result*.

---

## 2. What Was Built

| Artifact | Location | Notes |
|---|---|---|
| No-OI model + norm params | `artifacts/lancaster_ml/{model.joblib, manifest.json}` | Trained by the script below; RF, 50 trees, depth 8, `min_samples_leaf` 10, `class_weight=balanced` — Lancaster's own hyperparameters. |
| Training script | `scripts/train_lancaster_model.py` | Uses Lancaster's OWN FeatureEngine/ModelEngine unchanged (imported); excludes only the 2 OI features (Decision 1). Trains on bars **before 2025-08-01** so the backtest is out-of-sample. |
| Strategy plugin | `backend/src/quant_hub/application/strategy_engine/strategies/lancaster_ml_momentum.py` | `LancasterMLStrategy(Strategy)`. Reads only via `MarketDataView`; imports `lancaster_ml` as a submodule dependency (Decision 2); emits signed long/short `Signal` (Decision 3). |
| Unit tests | `backend/tests/unit/test_lancaster_ml_strategy.py` | 9 hermetic tests (fake model + fake view); all pass. |
| Registration | `scripts/register_strategy.py` (manifest entry `lancaster-ml-momentum`) | Registered into `core.strategies`. |
| Universe ingestion | `scripts/ingest_lancaster_universe.py` | Ingested 1000 daily bars/perp (2023-10 → 2026-07). |
| Live-verify runner | `scripts/run_lancaster_live_verify.py` | Produced 10 real recorded signals. |
| Backtest runner | `scripts/run_lancaster_backtest.py` | Drives the real Step 3.7 `BacktestEngine`. |

**P-1 compliance:** Lancaster's feature and model logic were imported and run unchanged — none of it was copied into `quant_hub`. The only new platform-side logic is the adapter's translation between the `MarketDataView`/`Signal` surfaces and Lancaster's batch API.

---

## 3. The No-OI Model (Decision 1)

Trained on the 10 Binance USDT perps, daily bars, **before the 2025-08-01 cutoff**: 5,310 pooled samples × 16 features, class balance P(up)=0.493 (well-balanced). Top feature importances: `rsi_14`, `volatility_63`, `volatility_regime`, `momentum_126`, `sma_gap_5_21`.

**Honest note on funding features:** the two funding features were kept (only OI was excluded, per Decision 1), but Binance funding history only reaches back ~166 days, which is entirely *after* the training window. So in training the funding features are **constant 0 with 0.0 model importance** — the model is effectively a 14-feature price/volatility/momentum model. This is actually a benefit for correctness: the plugin feeds 0 for funding at inference too (the point-in-time backtest view serves no funding), so there is **zero train/serve skew** on those features.

**Flagged judgment call — pooled normalization:** normalization params are fit once on the pooled pre-cutoff panel (statistically correct "training-time norm params"), not via Lancaster's per-symbol-overwrite quirk in `WalkForwardEngine._assemble_panel` (which the forensic audit §1.7 flagged). Lancaster's `FeatureEngine.normalize/.transform` do the work unchanged.

---

## 4. The Probability → Signed-Conviction Mapping (Decision 3, flagged judgment call)

Lancaster's model emits P(up over 5 days) ∈ [0,1]. QuantHub's `Signal.value` is a signed conviction ∈ [−1,+1]. The adapter maps:

```
value = clamp( (probability − 0.5) × 2 , −1, +1 )
```

`p=0.5 → 0` (flat), `p>0.5 → long`, `p<0.5 → short`; magnitude equals Lancaster's own `confidence = |p−0.5|×2`. **Only the sign is the QuantHub-side extension.**

**Explicitly flagged extrapolation:** the paper traded this model **long-only**. Mapping `p<0.5` to a *short* assumes the model's sub-0.5 probabilities are as directionally informative for shorts as its super-0.5 are for longs. For a balanced binary classifier that is a reasonable symmetry, but it is **not separately validated** — the short leg runs the model outside its original validated regime. A `long_only` config switch runs it inside that regime (§5.2 quantifies the difference).

---

## 5. Out-of-Sample Backtest Results (QuantHub Step 3.7 MTM engine)

**Setup:** 10 single-instrument backtests, $100,000/sleeve, window 2024-11-23 → 2026-07-10 (the 252-bar feature warmup completes ~2025-08-01, so the first tradeable signal lands at the training cutoff → the replay is out-of-sample). Fills are full-size at bar close, **zero slippage/commission (F-16)**. Deterministic replay (reproducibility hash per §10.3.6). 3,440 signals recorded in `core.signals`, spanning 2025-08-01 → 2026-07-09 (confirming OOS).

### 5.1 Long/short (Decision 3 — owner's perpetual regime)

| Symbol | Return % | Realized PnL | Trades |
|---|---:|---:|---:|
| BTC/USDT:USDT | −0.558 | −558.88 | 343 |
| ETH/USDT:USDT | −0.529 | −530.19 | 343 |
| SOL/USDT:USDT | −0.518 | −518.07 | 343 |
| DOGE/USDT:USDT | +0.694 | +732.41 | 343 |
| XRP/USDT:USDT | +0.285 | +300.18 | 343 |
| BNB/USDT:USDT | −0.302 | −302.92 | 343 |
| ADA/USDT:USDT | +0.209 | +209.01 | 343 |
| LINK/USDT:USDT | +0.581 | +567.46 | 343 |
| AVAX/USDT:USDT | +0.507 | +506.81 | 343 |
| APT/USDT:USDT | −0.150 | −160.33 | 343 |

**Aggregate (10 equal-capital sleeves):** total net PnL **$216.87** on $1,000,000 → **+0.022%** over ~11 months. Winning sleeves 5/10; best +0.694% / worst −0.558%; mean per-sleeve +0.022%, median +0.029%.

### 5.2 Long-only (paper's original validated regime)

Same setup, with `long_only=true` (shorts clamped to flat — the model's original validated use).

| Symbol | Return % | Trades |
|---|---:|---:|
| BTC/USDT:USDT | −0.583 | 313 |
| ETH/USDT:USDT | −0.594 | 228 |
| SOL/USDT:USDT | −0.631 | 194 |
| DOGE/USDT:USDT | +0.143 | 197 |
| XRP/USDT:USDT | +0.113 | 253 |
| BNB/USDT:USDT | −0.136 | 265 |
| ADA/USDT:USDT | −0.473 | 187 |
| LINK/USDT:USDT | −0.178 | 222 |
| AVAX/USDT:USDT | −0.354 | 202 |
| APT/USDT:USDT | −0.982 | 199 |

**Aggregate:** net PnL **−$3,675** on $1,000,000 → **−0.368%**. Winning sleeves 2/10; best +0.143% / worst −0.982%; median −0.414%.

**Interpretation:** long-only is *worse* than long/short here (−0.368% vs +0.022%). On this particular OOS window the short leg — the extrapolation flagged in §4 — happened to help, because the window contained down-moves the shorts caught. This is **not** evidence the short leg is validated; it is one window. It does show the long-only signal (the model's original validated regime) was net-negative out-of-sample on these survivors.

### 5.3 Reading the numbers

- **Effectively breakeven, before costs.** ±0.02% aggregate is noise, not edge. The model does not demonstrate a profitable directional signal on this OOS window.
- **Extreme churn.** 343 trades on 343 tradeable bars = the sleeve re-sizes every single day (conviction changes each bar, so the target notional moves each bar). With QuantHub's zero-cost fills this is free; in reality daily position flips on perps incur spread + taker fees + funding, which would turn this breakeven-before-cost result negative.
- **Small exposures.** The reference `LinearConvictionSizer` targets `value × 0.05 × capital` per name, so notional is sub-1% of capital — the return magnitudes are small by construction of the sizing methodology, not a bug. The *sign and breakeven character* of the result are the signal, not the tiny magnitude.

---

## 6. Caveats — Read the Results Only With These

1. **SURVIVORSHIP BIAS (restated from `LANCHESTER_INTEGRATION_INVESTIGATION.md` §5.2, unchanged and unaddressed).** The 10-perp universe is instruments that **survived to today**. Perps that were delisted or died over 2023–2026 are absent from both training and backtest, so *every* number here is optimistic relative to what a point-in-time-survivorship-free universe would have produced. This was a known flaw of the original research and it is **not fixed** by running the model through QuantHub — fixing it requires reconstructing a point-in-time universe (materially hard for crypto perps) and is out of scope for this integration. **No result in this document should be presented without this caveat.**

2. **Single-instrument engine ≠ cross-sectional strategy.** QuantHub's Step 3.7 engine backtests one instrument at a time; it cannot reproduce Lancaster's defining mechanic — cross-sectional ranking and top-N selection. Each perp here is traded independently on its own signed conviction, and the "portfolio" is 10 equal-capital independent sleeves. This is a *proxy* for, not a replica of, the paper's cross-sectional long-only top-N portfolio.

3. **Zero transaction costs (F-16).** As above — the reported breakeven is a *pre-cost* figure and the strategy's daily churn makes it cost-sensitive.

4. **Lancaster's own published numbers remain untrustworthy** (investigation doc §5.3: no mark-to-market, no costs). The point of this exercise was to replace that broken backtester with QuantHub's MTM engine — which is exactly what produced the honest breakeven figure above. The paper's 599%/Sharpe-1.9 should be disregarded.

5. **Short leg is an extrapolation** (§4) and **funding features are inert** (§3) on this data.

---

## 7. Conclusion

The integration works: Lancaster's model is now a real, registered, governed QuantHub strategy that produces real recorded signals through the real signal→sizing→order→risk→fill→MTM pipeline, and it can be backtested honestly through QuantHub's deterministic MTM engine. The **performance result is unflattering** — essentially breakeven out-of-sample before costs, with cost-sensitive daily churn, under a survivorship-biased universe. That is the honest answer to "backtest it and see real results," and it is far more trustworthy than the original paper's numbers precisely because it was produced by the MTM-correct engine rather than Lancaster's broken one.
