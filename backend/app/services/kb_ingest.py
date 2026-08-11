"""Chunking + embedding for KB documents. Milestone 6.

Real embedding calls (OpenAI) are not wired up here — when
`settings.embedding_fake` (the dev/test default, mirroring `loki_fake`), a
deterministic hash-based vector stands in so ingestion, storage, and future
retrieval code can be built and tested without an API key.
"""

import hashlib

from app.config import get_settings
from app.db.models.kb import EMBEDDING_DIM

CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 100


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE_CHARS
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP_CHARS
    return chunks


def _fake_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # repeat the 32-byte digest to fill EMBEDDING_DIM floats in [-1, 1]
    values = [digest[i % len(digest)] for i in range(EMBEDDING_DIM)]
    return [(v / 127.5) - 1.0 for v in values]


async def embed(text: str) -> list[float]:
    settings = get_settings()
    if settings.embedding_fake:
        return _fake_embedding(text)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.embeddings.create(
        model=settings.embedding_model, input=text, dimensions=settings.embedding_dim
    )
    return resp.data[0].embedding
