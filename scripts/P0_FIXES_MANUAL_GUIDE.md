# P0 Critical Fixes - Manual Application Guide

Due to complexity of the automated edits causing file corruption, here are the 5 P0 critical fixes to apply manually:

## ✅ Fix #1: smart_parser.py (Line 202)
**Issue**: Calling private method `_resolve_path` instead of public `resolve_path`
**Impact**: 100% failure rate for all sync operations

```python
# BEFORE (Line 202):
full_path = self.vault._resolve_path(note_path)

# AFTER:
full_path = self.vault.resolve_path(note_path)
```

---

## ✅ Fix #2: linear_sync.py (Lines 7 & 88)
**Issue**: Blocking I/O on async event loop
**Impact**: Performance degradation, event loop blocking

```python
# BEFORE (Line 7):
from fastapi import Request, HTTPException

# AFTER (add import):
from fastapi import Request, HTTPException
from starlette.concurrency import run_in_threadpool

# BEFORE (Line 88):
self.handle_linear_webhook(payload)

# AFTER:
await run_in_threadpool(self.handle_linear_webhook, payload)
```

---

## ✅ Fix #3: capture_server.py (Multiple locations)
**Issue**: No HTML size limits, sensitive log leakage
**Impact**: DoS vulnerability, information disclosure

### 3a. Add imports and constants (Lines 9-11, after line 32):
```python
# BEFORE (Line 9):
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

# AFTER (add Request):
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid
from fastapi import Request

# BEFORE (Line 32):
# Session tracking for batch percolation
pending_sessions: Dict[str, List[Neo4jSessionData]] = {}

# AFTER (add security constant):
# Session tracking for batch percolation
pending_sessions: Dict[str, List[Neo4jSessionData]] = {}

# Security limits
MAX_HTML_SIZE_BYTES = 500_000  # 500KB
```

### 3b. Update capture endpoint signature (Line 478):
```python
# BEFORE:
async def capture_conversation(
    data: ConversationData,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> CaptureResponse:

# AFTER:
async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> CaptureResponse:
```

### 3c. Add HTML size validation (Lines 483-491):
```python
# BEFORE:
    # 1. PARSING LOGIC
    if (not data.messages) and data.raw_html:
        logger.info(f"Detecting Raw HTML. Attempting server-side parsing for: {data.url}")
        try:
            data.messages = parse_html_content(data.raw_html, data.url or "unknown")
            logger.info(f"✓ Successfully parsed {len(data.messages)} messages.")
        except Exception as e:
            logger.error(f"HTML Parsing failed: {e}")
            data.messages = [{"role": "system", "content": f"Parsing failed: {e}"}]

# AFTER:
    # 1. SECURITY: Check request body size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_HTML_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="HTML payload too large (max 500KB)")

    # 2. PARSING LOGIC
    if (not data.messages) and data.raw_html:
        if len(data.raw_html) > MAX_HTML_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="HTML content too large (max 500KB)")
        # Sanitize URL for logging (prevent log injection)
        safe_url = (data.url or "unknown").replace('\n', '').replace('\r', '')[:100]
        logger.info(f"Detecting Raw HTML. Attempting server-side parsing for: {safe_url}")
        try:
            data.messages = parse_html_content(data.raw_html, data.url or "unknown")
            logger.info(f"✓ Successfully parsed {len(data.messages)} messages.")
        except Exception as e:
            # Don't leak exception details to client
            logger.error(f"HTML Parsing failed for {safe_url}: {type(e).__name__}")
            data.messages = [{"role": "system", "content": "Unable to parse provided HTML"}]
```

---

## ✅ Fix #4: auth_utils.py (Line 57)
**Issue**: Using deprecated `datetime.utcnow()`
**Impact**: Python 3.12+ deprecation warnings

```python
# BEFORE (Line 57):
expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

# AFTER:
expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

# Also ensure timezone is imported (Line 3):
from datetime import datetime, timedelta, timezone
```

---

## ✅ Fix #5: capture_server.py (Lines 47-65 - Debug Prints)
**Issue**: Debug print statements instead of proper logging
**Impact**: Code quality, inconsistent logging

```python
# BEFORE (Lines 47-65):
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to schedule batch percolation on server startup."""
    print("DEBUG: Entering lifespan")
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            batch_percolate_sessions, "interval", minutes=5, id="session_percolation"
        )
        scheduler.start()
        logger.info("✓ Session percolation scheduled (every 5 minutes)")
        print("DEBUG: Scheduler started")
        yield
        print("DEBUG: Yield returned")
        scheduler.shutdown()
    except Exception as e:
        print(f"DEBUG: Lifespan error: {e}")
        import traceback
        traceback.print_exc()
        raise

# AFTER:
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to schedule batch percolation on server startup."""
    logger.debug("Entering lifespan")
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            batch_percolate_sessions, "interval", minutes=5, id="session_percolation"
        )
        scheduler.start()
        logger.info("✓ Session percolation scheduled (every 5 minutes)")
        logger.debug("Scheduler started")
        yield
        logger.debug("Yield returned")
        scheduler.shutdown()
    except Exception as e:
        logger.exception(f"Lifespan error: {e}")
        raise
```

---

## Summary

| Fix# | File | Lines | Issue | Estimated Time |
|------|------|-------|-------|----------------|
| 1 | `omega_kg/smart_parser.py` | 202 | Method name typo | 30 seconds |
| 2 | `omega_kg/linear_sync.py` | 7, 88 | Blocking I/O | 1 minute |
| 3 | `omega_kg/capture_server.py` | 9-11, 32-35, 478, 483-495 | Security (DoS, logging) | 5 minutes |
| 4 | `omega_kg/auth_utils.py` | 3, 57 | Deprecated datetime | 1 minute |
| 5 | `omega_kg/capture_server.py` | 47-65 | Debug prints | 2 minutes |

**Total Estimated Time**: ~10 minutes

After applying these fixes, run:
```bash
poetry run python scripts/smoke_test.py
```

This will validate all critical components before merging.
