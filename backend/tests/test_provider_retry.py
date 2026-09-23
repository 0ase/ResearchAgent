import asyncio
from unittest.mock import AsyncMock

import httpx
from openai import APIStatusError
import pytest

from backend.services.provider_retry import request_with_retry


@pytest.mark.asyncio
@pytest.mark.parametrize("status,attempts", [(401, 1), (403, 1), (429, 2), (503, 2)])
async def test_retry_only_transient_errors(status, attempts):
    response = httpx.Response(status, headers={"retry-after": "0"}, request=httpx.Request("POST", "https://invalid.test"))
    operation = AsyncMock(side_effect=APIStatusError("injected", response=response, body=None))
    with pytest.raises(APIStatusError):
        await request_with_retry(operation)
    assert operation.await_count == attempts


@pytest.mark.asyncio
async def test_retry_wait_obeys_outer_deadline():
    response = httpx.Response(429, headers={"retry-after": "5"}, request=httpx.Request("POST", "https://invalid.test"))
    operation = AsyncMock(side_effect=APIStatusError("injected", response=response, body=None))
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.03):
            await request_with_retry(operation)
    assert operation.await_count == 1
