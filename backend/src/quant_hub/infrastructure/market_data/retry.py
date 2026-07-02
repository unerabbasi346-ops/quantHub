# Governing specification: Doc 11 §8 — Error Recovery (Data Engineering)
# Layer: Infrastructure — Doc 07 §Layers
# Per Doc 00 §14.11
#
# SCOPE (Step 1.8, per handbook/KNOWN_LIMITATIONS.md S-2 scope decision):
# implements Doc 11 §8's "exponential backoff" and (via RetryExhaustedError,
# consumed by the caller) "no failed ingestion shall silently discard
# records" requirements at a solo-developer scope — a bounded in-process
# retry loop, not a distributed job-queue retry system. Dead-letter queue
# and operator notification (§8's other two Retry Strategy items) are
# scoped down per S-2: see application/market_data/service.py for how a
# RetryExhaustedError is turned into a structured log entry (the DLQ/
# notification equivalent) rather than a separate store/alerting system.
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """All retry attempts for a transient operation were exhausted — Doc 11 §8.

    Raised instead of re-raising the raw last exception so callers can
    tell "gave up after N retries" apart from "failed immediately,
    non-retryable" without inspecting exception types themselves.
    """

    def __init__(self, context: str, attempts: int, last_error: BaseException) -> None:
        self.context = context
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"{context}: exhausted {attempts} attempt(s), last error: {last_error!r}"
        )


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retryable: tuple[type[BaseException], ...],
    context: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Exponential backoff retry — Doc 11 §8, scoped per S-2.

    Retries `fn()` up to `max_attempts` times (JUDGMENT CALL, Doc 00
    §14.5/§14.7: Doc 11 §8 requires backoff but does not specify a bound
    or a default attempt count — 3 is a small, sane default for a
    solo-developer platform; bounded, not infinite, per the explicit
    "not infinite" instruction) whenever `fn()` raises an exception
    matching `retryable`, sleeping `base_delay * 2**(attempt-1)` seconds
    between attempts. Exceptions NOT in `retryable` propagate immediately
    on the first attempt — Doc 11 §8's trigger list is specifically
    "network errors, rate limits, timeouts", not every possible failure.

    Raises RetryExhaustedError on exhaustion rather than letting a failed
    ingestion cycle silently vanish (Doc 11 §8: "No failed ingestion shall
    silently discard records") — the caller is expected to log it.
    """
    attempt = 0
    last_error: BaseException | None = None
    while attempt < max_attempts:
        attempt += 1
        try:
            return await fn()
        except retryable as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "%s: attempt %d/%d failed (%r), retrying in %.1fs",
                context, attempt, max_attempts, exc, delay,
            )
            await asyncio.sleep(delay)
    assert last_error is not None  # loop always sets it before falling through
    raise RetryExhaustedError(context=context, attempts=attempt, last_error=last_error)
