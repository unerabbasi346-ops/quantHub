# Governing specification: Doc 11 §8 — Error Recovery (Data Engineering)
# Per Doc 00 §14.11
from __future__ import annotations

import logging

import pytest

from quant_hub.infrastructure.market_data.retry import RetryExhaustedError, with_retry


class _RetryableError(Exception):
    pass


class _NonRetryableError(Exception):
    pass


@pytest.mark.asyncio
async def test_succeeds_on_first_attempt_no_retry() -> None:
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retry(fn, retryable=(_RetryableError,), context="test")
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_succeeds_after_transient_failures() -> None:
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _RetryableError(f"fail {calls}")
        return "ok"

    result = await with_retry(
        fn, retryable=(_RetryableError,), context="test", max_attempts=5, base_delay=0.01
    )
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_exhausts_retries_and_raises_retry_exhausted_error() -> None:
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        raise _RetryableError(f"fail {calls}")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await with_retry(
            fn, retryable=(_RetryableError,), context="test-context", max_attempts=3, base_delay=0.01
        )

    assert calls == 3  # bounded, not infinite
    assert exc_info.value.attempts == 3
    assert exc_info.value.context == "test-context"
    assert isinstance(exc_info.value.last_error, _RetryableError)


@pytest.mark.asyncio
async def test_non_retryable_exception_propagates_immediately() -> None:
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        raise _NonRetryableError("not transient")

    with pytest.raises(_NonRetryableError):
        await with_retry(fn, retryable=(_RetryableError,), context="test", max_attempts=5)

    assert calls == 1  # no retry attempted


@pytest.mark.asyncio
async def test_logs_warning_on_each_retry_attempt(caplog) -> None:
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        raise _RetryableError("fail")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(RetryExhaustedError):
            await with_retry(
                fn, retryable=(_RetryableError,), context="test", max_attempts=3, base_delay=0.01
            )

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 2  # logs on attempts 1 and 2 (not the final exhausting attempt)
