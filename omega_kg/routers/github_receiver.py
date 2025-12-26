"""
GitHub Webhook Receiver

Receives GitHub webhook events (PR merges, pushes, etc.) and persists them
to the database for background processing. Follows the same pattern as
linear_receiver.py for consistency.

 TN-103: The Refinery - Webhook Reception Layer
"""
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.session import get_db
from omega_kg.models.webhook import RawWebhookEvent
from omega_kg.settings import settings

# Setup Logger
logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_github_signature(request: Request) -> bytes:
    """
    Verify GitHub webhook signature (X-Hub-Signature-256).

    Args:
        request: FastAPI request object

    Returns:
        Raw request body bytes

    Raises:
        HTTPException: If signature is missing or invalid
    """
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        logger.warning(
            f"Missing X-Hub-Signature-256 header. Available headers: {list(request.headers.keys())}"
        )
        raise HTTPException(
            status_code=400, detail="Missing X-Hub-Signature-256 header"
        )

    body_bytes = await request.body()

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    expected_header = f"sha256={expected_signature}"

    if not hmac.compare_digest(signature, expected_header):
        logger.warning("GitHub webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body_bytes


@router.post("/webhooks/github", status_code=200)
async def receive_github_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    verification: bytes = Depends(verify_github_signature),
) -> dict:
    """
    Dumb and fast GitHub webhook endpoint.

    This endpoint follows the exact pattern from linear_receiver.py:
    1. Verify signature (via dependency injection)
    2. Persist raw payload to RawWebhookEvent table
    3. Return 200 OK immediately with event ID

    No business logic in hot path - all processing happens in background
    via EventProcessor.

    Args:
        request: FastAPI request object
        db: Database session
        verification: Verified request body bytes

    Returns:
        Dict with event status and ID
    """
    # Parse JSON payload
    import json

    try:
        payload = json.loads(verification.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse GitHub webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Create RawWebhookEvent (dumb and fast)
    db_event = RawWebhookEvent(
        source="github",
        headers=dict(request.headers),
        payload=payload,
        processed_status=False,
    )

    db.add(db_event)
    await db.commit()

    # Log event ID for debugging
    logger.info(f"Received GitHub webhook event ID: {db_event.id}")

    return {"status": "persisted", "id": db_event.id}
