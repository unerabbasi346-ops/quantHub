# Governing specification: Doc 03 — Technology Stack §Quantitative Libraries.
# Per Doc 00 §14.11
from __future__ import annotations

import pytest

from quant_hub.ml.ml_engine import HMMRegimeDetector, LSTMPredictor, XGBoostMetaLabeler
from quant_hub.ml.model_factory import create_model, registered_model_types


def test_registered_model_types_lists_all_three():
    assert registered_model_types() == ["HMM_RegimeDetector", "LSTM_Predictor", "XGBoost_MetaLabeler"]


def test_create_xgboost_metalabeler():
    model = create_model("XGBoost_MetaLabeler")
    assert isinstance(model, XGBoostMetaLabeler)
    assert model.model_name == "XGBoost_MetaLabeler"
    assert model.is_trained is False


def test_create_lstm_predictor():
    model = create_model("LSTM_Predictor", {"input_dim": 3, "seq_length": 5})
    assert isinstance(model, LSTMPredictor)
    assert model.params["input_dim"] == 3
    assert model.params["seq_length"] == 5


def test_create_hmm_regime_detector():
    model = create_model("HMM_RegimeDetector")
    assert isinstance(model, HMMRegimeDetector)


def test_create_model_unknown_type_raises_value_error():
    with pytest.raises(ValueError, match="Unknown model_type"):
        create_model("NotARealModel")


def test_create_model_hyperparams_override_defaults():
    model = create_model("XGBoost_MetaLabeler", {"max_depth": 9})
    assert model.params["max_depth"] == 9
    assert model.params["n_estimators"] == 200  # unspecified default preserved
