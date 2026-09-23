"""Embedding module — converts text to vectors via Alibaba DashScope API.

Qwen text-embedding-v4: MTEB #1 globally, China-accessible, OpenAI compatible.
Batch size capped at 10 per DashScope limit.
"""

import asyncio
from openai import AsyncOpenAI
from backend.config import settings

BATCH_SIZE = 10  # DashScope limit: max 10 inputs per request


class EmbeddingUnavailableError(RuntimeError):
    pass


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert a batch of texts to embedding vectors via DashScope.

    Splits into batches of BATCH_SIZE to respect API limits.
    Allows one transient-error retry within the shared per-paper deadline.
    """
    if not settings.dashscope_api_key:
        raise EmbeddingUnavailableError("DASHSCOPE_API_KEY is not configured")

    from backend.services.provider_retry import request_with_retry
    client = AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url,
                         timeout=settings.embedding_timeout, max_retries=0)
    all_embeddings = []
    try:
        async with asyncio.timeout(settings.embedding_timeout):
            for i in range(0, len(texts), BATCH_SIZE):
                batch = texts[i:i + BATCH_SIZE]
                response = await request_with_retry(lambda: client.embeddings.create(
                    model=settings.embedding_model, input=batch))
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([item.embedding for item in sorted_data])
        return all_embeddings
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise EmbeddingUnavailableError("embedding provider request failed") from exc
    finally:
        await client.close()


async def embed_single(text: str) -> list[float]:
    """Convert a single text to an embedding vector."""
    results = await embed_texts([text])
    return results[0]
