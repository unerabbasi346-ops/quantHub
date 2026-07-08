# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §Layers: Domain (pure value logic, no I/O). Doc 11 — Data Engineering:
#   OHLCV close prices are the input. Doc 00 §14.11.
#
# A STANDALONE price-return correlation calculator over already-ingested
# Phase-1 OHLCV closes. Owner-requested "simple asset price-correlation view."
#
# EXPLICIT SCOPE BOUNDARY (Doc 00 §14.5/§14.7 — flagged, and surfaced in the
# UI): this is a descriptive PRICE-RETURN correlation matrix between market
# instruments — NOT a portfolio risk metric. It is deliberately unrelated to
# F-18's deferred §11.5.3 risk measures (VaR / CVaR / beta / volatility /
# drawdown), which remain correctly deferred pending a portfolio return-series
# / equity-curve. This module computes only the pairwise Pearson correlation
# of per-bar simple returns of raw close prices; it makes no claim about
# portfolio exposure, tail risk, or capital at risk. Kept in the domain layer
# as a pure, deterministic function so it is unit-testable without a database.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Sequence


@dataclass(frozen=True)
class CorrelationMatrix:
    """Result of a return-correlation computation.

    `labels[i]` names row/column i of `matrix`. A cell is None when the
    coefficient is undefined (a constant series has zero variance, so Pearson
    correlation is division-by-zero — reported honestly as null, never faked
    as 0 or 1). `sample_size` is the number of aligned return observations each
    pair was computed over (one fewer than the aligned price count).
    """

    labels: tuple[str, ...]
    matrix: tuple[tuple[float | None, ...], ...]
    sample_size: int


def _simple_returns(closes: Sequence[float]) -> list[float]:
    """Per-step simple returns r_t = c_t / c_(t-1) - 1.

    A zero/blank prior price is skipped-as-0 change guard: if c_(t-1) == 0 the
    return is undefined, so we treat that step as 0.0 rather than raising —
    real ingested crypto closes are strictly positive, so this only guards
    against a degenerate/synthetic series.
    """
    out: list[float] = []
    for prev, cur in zip(closes, closes[1:]):
        out.append((cur / prev - 1.0) if prev != 0 else 0.0)
    return out


def _pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    n = len(x)
    if n == 0:
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    denom = sqrt(var_x * var_y)
    if denom == 0:
        return None  # at least one series is constant — correlation undefined
    r = cov / denom
    # clamp tiny floating-point overshoot so results stay in [-1, 1]
    return max(-1.0, min(1.0, r))


def compute_return_correlations(
    series: dict[str, Sequence[Decimal | float]],
) -> CorrelationMatrix:
    """Pairwise Pearson correlation of the simple returns of each price series.

    `series` maps a label (e.g. an instrument symbol) to its TIME-ALIGNED close
    prices — every series MUST already be aligned to the same set of
    timestamps and therefore be the same length (the caller intersects
    timestamps before calling this). Determinism (P-13): output depends only on
    the inputs and their insertion order; no clock, no randomness.

    Closes are converted Decimal->float for the statistics (correlation is a
    descriptive statistic, not a monetary value, so float precision is
    appropriate here — this never touches money math).
    """
    labels = tuple(series.keys())
    # returns per label (float)
    returns: dict[str, list[float]] = {
        label: _simple_returns([float(v) for v in values]) for label, values in series.items()
    }
    sample_size = min((len(r) for r in returns.values()), default=0)

    matrix: list[tuple[float | None, ...]] = []
    for a in labels:
        row: list[float | None] = []
        for b in labels:
            if a == b:
                # a series is perfectly correlated with itself — but only if it
                # actually varies; a constant series stays undefined even on
                # the diagonal (honest: we cannot claim r=1 for no-variance).
                row.append(1.0 if _pearson(returns[a], returns[a]) is not None else None)
            else:
                row.append(_pearson(returns[a], returns[b]))
        matrix.append(tuple(row))

    return CorrelationMatrix(labels=labels, matrix=tuple(matrix), sample_size=sample_size)
