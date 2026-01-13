import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from omega_kg.settings import settings
from omega_kg.models.validation_schemas import KnowledgeDigest

logger = logging.getLogger("omega.omegakg_client")


class OmegaKGInternalClient:
    """
    HTTP client for OmegaKG validation API (internal use by workers).

    Standardizes on the API-first pattern even for internal service workers
     to ensure consistent validation and deduplication.
    """

    def __init__(self):
        # Even though we are internal, we call via HTTP to hit the validation logic
        # and stay decoupled from the store implementation.
        self.base_url = f"http://localhost:{settings.app_port}"
        # Use static service token for internal calls
        self.token = settings.static_service_token
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    async def validate_and_store(
        self, digest: KnowledgeDigest, max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Submit knowledge digest to OmegaKG validation API.
        """
        attempt = 0
        backoff = 1

        while attempt <= max_retries:
            try:
                response = await self.client.post(
                    "/validate/validate-and-store", json=digest.model_dump(mode="json")
                )

                if response.status_code in [200, 400, 409]:
                    return response.json()

                if response.status_code >= 500:
                    if attempt < max_retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        attempt += 1
                        continue

                response.raise_for_status()

            except (httpx.HTTPError, Exception) as e:
                if attempt < max_retries:
                    logger.warning(f"Retry {attempt + 1} for OmegaKG API: {e}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    attempt += 1
                else:
                    logger.error(
                        f"OmegaKG API call failed after {max_retries} retries: {e}"
                    )
                    raise

        return {"status": "error", "message": "Max retries exceeded"}

    async def close(self):
        await self.client.aclose()
