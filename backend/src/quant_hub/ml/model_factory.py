# Governing specification: Doc 03 — Technology Stack §Quantitative Libraries
# Layer: Domain-adjacent ML models — Doc 04 §Repository Structure
# Invariant: P-1-style registry discipline (mirrors the strategy registry,
#   domain/strategy_engine/interfaces.py::StrategyRepository.upsert — explicit
#   resolve-or-register, never an auto-scanned plugin directory).
# Per Doc 00 §14.11
#
# Explicit dict registry mapping a model_type string to its class — every
# class the Task 0 audit found in ml_engine.py is registered here by its own
# `model_name` (BaseQuantModel.__init__'s first argument), so a caller's
# model_type string always matches what an instantiated model reports as its
# own name. An unregistered name raises ValueError rather than silently
# falling back to a default model or auto-discovering classes by scanning
# the module (same "never auto-scan" discipline as the strategy registry).
from __future__ import annotations

from typing import Any, Mapping

from quant_hub.ml.ml_engine import (
    BaseQuantModel,
    HMMRegimeDetector,
    LSTMPredictor,
    XGBoostMetaLabeler,
)

_REGISTRY: dict[str, type[BaseQuantModel]] = {
    "XGBoost_MetaLabeler": XGBoostMetaLabeler,
    "LSTM_Predictor": LSTMPredictor,
    "HMM_RegimeDetector": HMMRegimeDetector,
}


def registered_model_types() -> list[str]:
    """All model_type names this factory can instantiate, stably ordered."""
    return sorted(_REGISTRY)


def create_model(model_type: str, hyperparams: Mapping[str, Any] | None = None) -> BaseQuantModel:
    """Instantiate a registered model by its exact `model_type` name.

    Raises ValueError with the full list of registered names when
    `model_type` isn't registered — never silently substitutes a default
    model or guesses an intended type from a partial match.
    """
    cls = _REGISTRY.get(model_type)
    if cls is None:
        raise ValueError(
            f"Unknown model_type {model_type!r}. Registered types: {registered_model_types()}"
        )
    return cls(dict(hyperparams) if hyperparams else None)
