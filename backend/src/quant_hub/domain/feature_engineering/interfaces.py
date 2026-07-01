# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Feature Engineering — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod


class FeaturePipelineInterface(ABC):
    """Contract for feature computation pipelines — Doc 07 §Implementation Rules.

    Feature engineering is compute-bound; no direct persistence table in schema v0.1.
    Outputs are consumed by model training (ML domain) and strategy signals.
    """

    @abstractmethod
    async def compute(self, inputs: dict) -> dict: ...
