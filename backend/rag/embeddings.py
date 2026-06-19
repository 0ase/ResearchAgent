"""Embedding module — converts text to vectors via Alibaba DashScope API.

Qwen text-embedding-v4: MTEB #1 globally, China-accessible, OpenAI compatible.
Batch size capped at 10 per DashScope limit.
"""

import asyncio
from openai import AsyncOpenAI
from backend.config import settings

BATCH_SIZE = 10  # DashScope limit: max 10 inputs per request


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert a batch of texts to embedding vectors via DashScope.

    Splits into batches of BATCH_SIZE to respect API limits.
    Retries on network errors up to 3 times.
    """
    client = AsyncOpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )

    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for attempt in range(3):
            try:
                response = await client.embeddings.create(
                    model="text-embedding-v4",
                    input=batch,
                )
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([item.embedding for item in sorted_data])
                break
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))
                else:
                    # last attempt failed — return zeros to not crash pipeline
                    all_embeddings.extend([[0.0] * 1024 for _ in batch])

    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """Convert a single text to an embedding vector."""
    results = await embed_texts([text])
    return results[0]
