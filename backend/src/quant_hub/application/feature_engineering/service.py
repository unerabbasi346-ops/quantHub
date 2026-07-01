# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Feature Engineering — Doc 07 §Core Services
# Background processing: long-running ML feature jobs — Doc 07 §Background Processing
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.feature_engineering.interfaces import FeaturePipelineInterface


class FeatureEngineeringService:
    """Application service stub — business logic not implemented in Step 0.4."""

    def __init__(self, pipeline: FeaturePipelineInterface) -> None:
        self._pipeline = pipeline
