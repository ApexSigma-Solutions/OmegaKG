import hmac
import hashlib
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from omega_kg.database.session import get_db
from omega_kg.settings import settings
from omega_kg.models.linear import RawLinearEvent

# Setup Logger
logger = logging.getLogger(__name__)

router = APIRouter()

async def verify_signature(request: Request):
    # Check for standard and alternate headers
    signature = request.headers.get("Linear-Signature") or request.headers.get("X-Linear-Signature")
    
    if not signature:
        logger.warning(f"Missing Linear-Signature. Headers: {request.headers.keys()}")
        raise HTTPException(status_code=400, detail="Missing Linear-Signature header")

    body_bytes = await request.body()
    
    expected_signature = hmac.new(
        settings.linear_webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid Signature")
        
    return body_bytes, signature

@router.post("/webhooks/linear", status_code=200)
async def receive_linear_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    verification: tuple = Depends(verify_signature)
):
    payload_bytes, signature = verification
    
    try:
        payload = json.loads(payload_bytes)
        headers = dict(request.headers)
        
        # Extract External Timestamp
        ext_ts = None
        data_obj = payload.get("data", {})
        if "createdAt" in data_obj:
            try:
                # Linear sends ISO 8601 strings e.g. "2020-01-01T00:00:00.000Z"
                ext_ts = datetime.fromisoformat(data_obj["createdAt"].replace("Z", "+00:00"))
            except ValueError:
                pass 
        
        db_event = RawLinearEvent(
            signature=signature,
            external_timestamp=ext_ts,
            event_type=payload.get("type", "unknown"),
            action=payload.get("action", "unknown"),
            headers=headers,
            body=payload,
            processed=False
        )
        
        db.add(db_event)
        await db.commit()
        
        return {"status": "persisted", "id": db_event.id}

    except Exception as e:
        logger.error(f"Persistence Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Persistence Failure")