"""
Embedding Service - Provider-Agnostic Vector Generation

Generates 1024-dimension embeddings using Nano-GPT (BAAI bge-m3) as primary provider,
with optional Gemini fallback (truncated from 3072 to 1024 dims).

Phase 7: TN-LINEAR-07 - The Enrichment (Embeddings)
"""

import logging
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from omega_kg.settings import settings

logger = logging.getLogger(__name__)

# Provider configuration
NANOGPT_EMBEDDING_URL = "https://nano-gpt.com/api/v1/embeddings"
NANOGPT_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSIONS = 1024


# ----------------------------------------------------------------------
# Primary Provider: Nano-GPT (hosted BAAI bge-m3) - 1024 dimensions
# ----------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _embed_nanogpt(text: str) -> List[float]:
    """
    Generate embedding using Nano-GPT's hosted BAAI bge-m3 model.

    Args:
        text: Input text to embed

    Returns:
        1024-dimension float vector

    Raises:
        RuntimeError: If API key is missing
        ValueError: If response doesn't contain valid 1024-dim embedding
        httpx.HTTPError: On API communication failure
    """
    api_key = settings.nanogpt_api_key
    if not api_key:
        raise RuntimeError("Nano-GPT API key missing (NANOGPT_API_KEY not set)")

    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"model": NANOGPT_MODEL, "input": text}
        headers = {"Authorization": f"Bearer {api_key}"}

        response = await client.post(
            NANOGPT_EMBEDDING_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()

        # Handle OpenAI-compatible response format
        if "data" in data and len(data["data"]) > 0:
            embedding: List[float] = data["data"][0].get("embedding")
        else:
            embedding = data.get("embedding")

        if not embedding or len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Nano-GPT returned invalid embedding "
                f"(expected {EMBEDDING_DIMENSIONS} dims, got {len(embedding) if embedding else 'None'})"
            )

        return embedding


# ----------------------------------------------------------------------
# Fallback Provider: Gemini - 3072 dims → truncated to 1024
# ----------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _embed_gemini(text: str) -> List[float]:
    """
    Generate embedding using Gemini API, truncating to 1024 dimensions.

    Gemini's gemini-embedding-001 returns 3072 dimensions.
    We truncate to the first 1024 to match the Neo4j index.

    Args:
        text: Input text to embed

    Returns:
        1024-dimension float vector (truncated from 3072)

    Raises:
        RuntimeError: If Gemini API key is missing
        ValueError: If response has fewer than 1024 dimensions
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("Gemini API key missing (GEMINI_API_KEY not set)")

    # Use httpx for Gemini API (OpenAI-compatible endpoint)
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"model": "gemini-embedding-001", "input": text}
        headers = {"Authorization": f"Bearer {api_key}"}

        response = await client.post(
            "https://generativelanguage.googleapis.com/v1/embeddings",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()

        # Handle response format
        if "data" in data and len(data["data"]) > 0:
            raw_embedding: List[float] = data["data"][0].get("embedding")
        else:
            raw_embedding = data.get("embedding")

        if not raw_embedding or len(raw_embedding) < EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Gemini returned fewer than {EMBEDDING_DIMENSIONS} dimensions "
                f"(got {len(raw_embedding) if raw_embedding else 'None'})"
            )

        # Truncate to 1024 dimensions to match Neo4j index
        return list(raw_embedding[:EMBEDDING_DIMENSIONS])


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
async def generate_embedding(text: str) -> List[float]:
    """
    Generate a 1024-dimension embedding for the given text.

    Provider hierarchy:
    1. Nano-GPT (BAAI bge-m3) - primary, native 1024-dim
    2. Gemini (gemini-embedding-001) - fallback, truncated from 3072 to 1024

    Args:
        text: Input text to embed (e.g., "Issue Title + Description")

    Returns:
        List of 1024 floats representing the semantic embedding

    Raises:
        RuntimeError: If no embedding provider is available or all providers fail

    Example:
        >>> embedding = await generate_embedding("Fix login button alignment")
        >>> len(embedding)
        1024
    """
    # Try Nano-GPT first (if key is configured)
    if settings.nanogpt_api_key:
        try:
            result: List[float] = await _embed_nanogpt(text)
            logger.debug(f"Generated {EMBEDDING_DIMENSIONS}-dim embedding via Nano-GPT")
            return result
        except Exception as err:
            logger.warning(
                f"Nano-GPT embedding failed ({err}); attempting Gemini fallback"
            )

    # Fallback to Gemini (if key is configured)
    if settings.gemini_api_key:
        try:
            result = await _embed_gemini(text)
            logger.debug(
                f"Generated {EMBEDDING_DIMENSIONS}-dim embedding via Gemini (truncated)"
            )
            return result
        except Exception as err:
            logger.error(f"Gemini embedding also failed: {err}")
            raise RuntimeError(f"All embedding providers failed. Last error: {err}")

    raise RuntimeError(
        "No embedding provider available. "
        "Set NANOGPT_API_KEY or GEMINI_API_KEY in environment."
    )
