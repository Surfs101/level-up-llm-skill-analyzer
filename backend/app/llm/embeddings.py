"""Text embeddings — the single place text becomes a vector.

Both the offline course seeder and the online RAG retriever embed through here, so
courses and gap queries land in the same vector space and cosine distance is
meaningful. The model and dimensions are fixed: they must match the
course_embeddings column (vector 1536), and changing either means re-embedding the
whole corpus.
"""

from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    """The embeddings client, built once. Lazy so importing this needs no API key."""
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def embed_text(text: str) -> list[float]:
    """Embed a single string into one 1536-dim vector."""
    vectors = await embed_texts([text])
    return vectors[0]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings, returning vectors in the same order as the input."""
    response = await _client().embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
