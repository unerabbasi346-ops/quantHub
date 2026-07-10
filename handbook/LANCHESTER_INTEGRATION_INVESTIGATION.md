# Lancaster ML Strategy — Integration Investigation

**Prepared for:** QuantHub
**Status:** Investigation complete. Decisions recorded below. Adapter NOT yet implemented.
**Subject:** `research/PROJECT_LANCHESTER` (git submodule `lancaster_ml`) — an existing, pre-QuantHub, ML-based Random Forest paper-trading system — evaluated as a candidate real QuantHub Strategy plugin.
**Sources:** `research/PROJECT_LANCHESTER`'s own specs (`model_specification.md`, `feature_specification.md`, `strategy_specification.md`, `data_requirements.md`, `architecture.md`), its implementation (`lancaster_ml/feature_engine.py`, `training_engine.py`, `model_engine.py`, `signal_engine.py`, `data/crypto_loader.py`, `config.py`), its own forensic audit (`lancaster_ml/reports/forensic_audit_report.md`) and leakage regression suite (`lancaster_ml/tests/test_data_leakage.py`); QuantHub's `domain/strategy_engine/strategy.py`, `domain/strategy_engine/entities.py`, `application/strategy_engine/reference_strategies/{funding_rate_basis,moving_average_crossover}.py`, `infrastructure/strategy_engine/{plugin_registry,market_data_view}.py`.

---

## 1. Executive Summary

PROJECT_LANCHESTER is a full research-to-production pipeline (~118 Python files) built around one core: a **Random Forest classifier** that predicts the probability a security's price rises over the next 5 days, ranks a universe cross-sectionally by that probability, and equal-weights the top N. It has already been ported from its original 16-equity universe to **10 Binance USDT perpetual swaps** (`BTC/USDT:USDT` … `APT/USDT:USDT`), which aligns with the owner's actual trading style.

It implements **none** of QuantHub's `Strategy` plugin contract today: it reads market data directly via `ccxt` (a P-1/Dependency-Rules violation if reused as-is), trains inside its own signal-generation path, and emits a ranked probability table rather than a signed `Signal.value ∈ [-1, +1]`. All of that is adaptable without touching Lanchester's own model/feature logic.

**Data gap:** QuantHub ingests OHLCV and funding rates (sufficient for 12 of Lanchester's 14 core features plus the funding features) but does **not** ingest open interest, which two of Lanchester's crypto-specific features depend on (`open_interest_change_1d`, `oi_volume_ratio`).

**Forensic cross-reference (the owner's own prior review, cross-checked against the actual code, not re-litigated):** look-ahead / label-contamination — the flaw originally flagged in the research — is **fixed** in this implementation (verified target construction, walk-forward boundary, and normalization discipline, backed by a dedicated leakage regression suite). **Survivorship bias is real and unaddressed** — the universe is a hardcoded list of instruments that exist today, with no delisted-instrument handling. **Lanchester's own backtest engine has no mark-to-market**, which independently invalidates its published performance numbers (599% return, Sharpe 1.898) regardless of the ML pipeline's own correctness — this is a reason to backtest through QuantHub's engine, not Lanchester's, and to report survivorship bias as a standing caveat on any result.

**Recommendation:** build a thin adapter plugin that imports Lanchester's `FeatureEngine`/`ModelEngine` as an external library (no vendoring, no changes to Lanchester's own logic), loads a pre-trained model with its training-time normalization parameters, reads market data only through `MarketDataView`, and emits signed `Signal`s. Decisions on the open questions this raised are recorded in Section 8.

---

## 2. What PROJECT_LANCHESTER Contains

**Model** (`lancaster_ml/model_engine.py`, `model_specification.md`):
- Random Forest classifier (scikit-learn), 50 trees, `max_depth=8`, `min_samples_leaf=10`, `class_weight="balanced"`, `random_state=42`. LightGBM and an ensemble mode are selectable alternatives (`config.model_type`); pre-trained artifacts already exist on disk (`output/models/rf_latest.joblib`, `lgbm_latest.joblib`).
- **Target** (`training_engine._build_target`): binary `sign(5-day forward return)` — `1` if `(P_{t+5} - P_t) / P_t > 0` else `0`. Directional, not magnitude.

**Features** (`feature_engine.py`, `feature_specification.md`): 14 core features — 5 momentum windows (5/10/21/63/126d), 3 volatility windows, 2 SMA-gap features, RSI(14), 252-day max-drawdown, volume z-score — plus crypto-specific extensions computed when the input columns exist: `funding_rate_ma_7`, `funding_rate_zscore`, `open_interest_change_1d`, `oi_volume_ratio`, `volatility_regime`.

**Universe:** originally 16–53 US equities; the live `CryptoUniverseConfig` (`config.py`) is 10 Binance USDT-margined perpetuals, daily (`1d`) bars, via `ccxt`.

**What the prediction output actually is today:** `ModelEngine.predict_proba(X)[:, 1]` — a **probability in [0, 1]** per symbol that price rises over the next 5 days. Not a buy/sell decision, not a raw unbounded score. `SignalEngine.generate_signals` wraps these into a ranked DataFrame, computes `confidence = abs(prob - 0.5) * 2`, cross-sectionally ranks by probability, and `compute_conviction_scores` z-scores probability across the current cross-section. The native pipeline is therefore inherently **batch and cross-sectional** — it evaluates a whole universe at once, not one symbol in isolation.

---

## 3. Gap Against QuantHub's Strategy Interface

QuantHub's plugin contract (`domain/strategy_engine/strategy.py`): `async generate_signals(view: MarketDataView, config) -> Sequence[Signal]`, where `Signal.value` is a signed conviction clamped to `[-1, +1]` (`domain/strategy_engine/validation.py`), and the plugin's only channel to market data is the read-only `MarketDataView` (`latest_bars`, `latest_tick`, `latest_funding_rates`).

Lanchester conforms to none of this natively:

| QuantHub requires | Lanchester does today | What adapting requires |
|---|---|---|
| Read-only via `MarketDataView` | `CryptoLoader` (`data/crypto_loader.py`) calls `ccxt` directly | Discard Lanchester's data layer; feed it bars/funding sourced from the view |
| `Signal(value ∈ [-1, +1])` | Ranked DataFrame of probabilities `[0, 1]` | Map `prob → (prob − 0.5) × 2`, clamp — `confidence` already computes this shape |
| Stateless per call, no training inside `generate_signals` | `WalkForwardEngine` trains an 84-month RF at each step | Model must be pre-trained and loaded (joblib); the plugin only performs inference |
| No feature store — bars only (current Phase 2 scope) | Recomputes 14+ features itself from OHLCV | Compatible as-is: the plugin recomputes features from raw bars, matching the interface's own documented scope |
| Conviction magnitude = signal strength | Cross-sectional z-score of probability | Requires reading the full configured universe within one `generate_signals` call |

**Net:** Lanchester's feature-engineering and model-inference logic is reusable unchanged. Its data-loading, training-loop, backtest, and execution layers are bypassed or replaced by QuantHub's own governed equivalents.

---

## 4. Data Requirements vs. QuantHub Phase 1 Ingestion

| Input | QuantHub ingests it? | Notes |
|---|---|---|
| Daily OHLCV | **Yes** — `latest_bars(asset, interval, limit)`, `interval="1d"` supported | Needs ≥ ~252–260 bars of history per symbol (`momentum_126`, `max_drawdown_1y=252`; Lanchester's own `WalkForwardEngine.MIN_HISTORY = 260`) |
| Funding rate | **Yes** — `latest_funding_rates(asset, limit)` (migration `e7a3c1f5b9d2`) | QuantHub stores the raw funding series; Lanchester expects **daily-summed** funding (3× 8h payments/day) — the adapter must resample |
| **Open interest** | **No** — not ingested anywhere in `backend/src` | Blocks `open_interest_change_1d` and `oi_volume_ratio` as specified. Resolved in Section 8, Decision 1 |

The plugin also needs the **entire configured universe within one `generate_signals` call**, since ranking/z-scoring is cross-sectional — the adapter loops the config's symbol list against the view rather than treating one symbol per call.

**Normalization dependency:** features must be transformed using the model's **training-time** `_norm_params` (`FeatureEngine.transform`, never `.normalize` at inference), which the forensic audit (Section 5, item 1.7) found is easy to get wrong. These parameters must ship with the model artifact, or every inference silently mis-scales the feature vector.

---

## 5. Forensic Cross-Reference: Survivorship Bias & Look-Ahead Label Contamination

The owner's own prior forensic review of this strategy exists in the repository itself — `research/PROJECT_LANCHESTER/lancaster_ml/reports/forensic_audit_report.md` — backed by a dedicated regression suite, `lancaster_ml/tests/test_data_leakage.py`. This section cross-checks that review's two flagged concerns against the **actual code**, for the sake of interpreting any future backtest result honestly — not to decide whether to proceed.

### 5.1 Look-ahead / label contamination — FIXED in this implementation

- `_build_target` uses `close.shift(-horizon)`: the **label** is forward-looking by design (that is correct — leakage is a *feature* or *training window* seeing the future, not the label).
- `_assemble_panel` aligns and drops NaN rows, so the trailing rows with unrealized (future) labels never enter training.
- `run_walk_forward` trains only on `df[df.index < date]` — the training window ends strictly before the prediction date.
- Feature computation uses forward-fill only (`ffill`), never backward-fill; `test_data_leakage.py` asserts this directly, along with zero temporal overlap between walk-forward folds and normalization fit strictly on training data.
- Forensic audit verdict (§2.2, §7.1): **"No look-ahead bias found."**

**Conclusion:** the label-contamination flaw originally identified in the research has been remediated in this codebase. This holds provided any QuantHub-side backtest preserves the same train-boundary discipline when re-deriving features/labels — it does not automatically transfer if the pipeline is reimplemented carelessly.

### 5.2 Survivorship bias — REAL and unaddressed

- Forensic audit (§7.2): confirmed, no delisted-security handling; the walk-forward loop silently skips symbols missing on a given date rather than accounting for their exit.
- The live crypto universe (`CryptoUniverseConfig.symbols`) is a **hardcoded list of 10 coins that exist today**. Any perpetual that was delisted or failed historically is simply absent from the universe used to compute any backtest — this inflates measured returns and is exactly the owner's originally flagged concern. It is present, unresolved, in the current configuration.

### 5.3 Additional finding that independently invalidates Lanchester's own published numbers

- Forensic audit (§5.1–§5.3): Lanchester's own backtest engine tracks holdings at **entry notional, not mark-to-market** — the equity curve is a step function with zero daily variance between monthly rebalances. This **artificially inflates the Sharpe ratio and understates drawdown**, and transaction costs are never applied. The paper's headline metrics (599.94% return, Sharpe 1.898) **cannot be trusted as reported**, independent of whether the ML pipeline itself is sound.

**Honest interpretive bottom line:** the feature/label pipeline is point-in-time clean, but (a) the universe is survivorship-biased and (b) Lanchester's own backtest engine is broken. A QuantHub backtest is worth running specifically *because* it replaces the broken engine with QuantHub's own mark-to-market pipeline — but survivorship bias will remain baked into any result until the universe is reconstructed point-in-time (materially harder for crypto perpetuals than equities), and should be stated as a standing caveat on any reported performance, not silently fixed or silently ignored.

---

## 6. Placeholder / Non-Functional Components (context, not blocking)

The forensic audit additionally found several Lanchester subsystems that are stubs and are irrelevant to signal generation but worth noting so they are not mistaken for usable infrastructure: broker implementations (`execution/broker.py`) return hardcoded fills or empty positions; `PaperBroker._unrealized_pnl` is hardcoded `0.0`; probability calibration (Platt/isotonic) is not applied to raw RF output. None of these affect the feature → model → probability path the adapter depends on.

---

## 7. Proposed Adapter Shape

A single new plugin class, e.g. `LancasterMLStrategy(Strategy)`, added on the QuantHub side alongside the existing reference plugins (`funding_rate_basis.py`, `moving_average_crossover.py`). Lanchester's own logic is **not modified** — it is imported as an external dependency, per Decision 2 below.

1. **Load once** (from a config-specified artifact path): a pre-trained model via `ModelEngine.load(...)` **and** its fitted `_norm_params`. No training occurs inside `generate_signals`.
2. **`generate_signals(view, config)`**: for each symbol in `config["universe"]`, read `view.latest_bars(asset, "1d", limit≈260)` and `view.latest_funding_rates(asset)` — only through the view, never `ccxt` or a repository directly.
3. **Reconstruct the feature frame** by calling Lanchester's own `FeatureEngine.compute_all(df)` then `.transform(...)` using the model's training-time norm params (loaded in step 1). The open-interest features are handled per Decision 1 below.
4. **Infer**: `ModelEngine.predict_proba(X)` → probability per symbol.
5. **Translate to signed `Signal`s** across the universe read in this call: `value = clamp((probability − 0.5) × 2, −1, +1)` — per Decision 3 below, both directions are emitted (no long-only clamp). Attach `probability`, `confidence`, and cross-sectional `rank` to `Signal.metadata`.

Position sizing, order generation, signal validation, and recording remain entirely downstream, governed platform stages — unchanged from how `funding_rate_basis.py` and `moving_average_crossover.py` already work. The adapter's responsibility ends at emitting signed convictions.

---

## 8. Decisions

The following were open questions raised by this investigation. They are now decided and recorded here as the basis for implementation when it proceeds.

**Decision 1 — Open interest:** retrain a **no-OI model variant** for the first honest QuantHub backtest run. Do not build open-interest ingestion yet. `open_interest_change_1d` and `oi_volume_ratio` are dropped from the feature vector for this variant; `funding_rate_ma_7`, `funding_rate_zscore`, and `volatility_regime` are retained since their inputs (OHLCV, funding) are already ingested.

**Decision 2 — Import mechanism:** `lancaster_ml` is consumed as a **submodule-as-dependency** (imported as an external library from `backend`), not vendored or copied into the platform. This is the concrete enforcement of "Lanchester's logic stays external" (P-1) — the platform depends on it the way it depends on any third-party package, rather than absorbing strategy-specific logic into `quant_hub`.

**Decision 3 — Signal direction:** the adapter is **long/short-capable**. `Signal.value` is emitted signed across the full `[-1, +1]` range (no long-only clamp to `[0, 1]`), matching the owner's actual perpetual-futures trading style, even though Lanchester's original research paper was long-only equities. `probability < 0.5` produces a negative (short-leaning) conviction rather than being floored to zero.

---

## 9. Status

Investigation complete. **No adapter code has been written.** Section 7 describes the proposed shape for when implementation is authorized; Section 8's decisions are binding inputs to that implementation, not yet executed.
