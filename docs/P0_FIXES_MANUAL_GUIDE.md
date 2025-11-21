# Implementation Protocol

---

MAR (Mandatory Agent Review) Required: Yes - All fixes must pass MAR protocol before marking complete
Validation: Runpoetry run python scripts/smoke_test.py after all fixes
Backup Strategy: Create.backup files before modifications (version control + atomic backup)
Import Standards: Minimal changes only - add imports where needed without reordering

---

## **Fix 1**: smart_parser.py Method Name Correction

**File**:omega_kg/smart_parser.py
**Line**Timer.: 202
**Issue**: Private method usage
**Action**:

```python

# **BEFORE**:
self.vault._resolve_path(note_path)

# **AFTER**:  
self.vault.resolve_path(note_path)
```

Validation: Verify method exists in public API, no_ prefix

---

## **Fix 2**: linear_sync.py Async I/O Conversion

**File**:omega_kg/linear_sync.py
**Lines**: 7, 88
**Issue**: Blocking I/O in async context
**Actions**:

```python
# Line 7 - Add import:
from starlette.concurrency import run_in_threadpool

# Line 88 - Replace sync call:
# BEFORE:
self.handle_linear_webhook(payload)

# AFTER:
await run_in_threadpool(self.handle_linear_webhook, payload)
```

Validation: Confirm function signature accepts payload parameter

---

## **Fix 3**: capture_server.py Security Hardening

**File**:omega_kg/capture_server.py
**Lines**: 16, 33, 478, 483-495
**Issues**: Missing request validation, DoS vulnerability
**Actions**:

```python
# Line 16 - Add to FastAPI imports:
Request

# After line 32 - Add constant:
MAX_HTML_SIZE_BYTES = 500_000

# Line 478 - Update function signature:
def capture_conversation(request: Request, ...):

# Lines 483-495 - Insert validation block:
if request.headers.get('content-length'):
    content_length = int(request.headers.get('content-length'))
    if content_length > MAX_HTML_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Request too large")

try:
    form_data = await request.form()
    html_content = form_data.get('html', '')

    if len(html_content.encode('utf-8')) > MAX_HTML_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="HTML content too large")

    # URL sanitization
    if not self._is_valid_url(form_data.get('url', '')):
        raise HTTPException(status_code=400, detail="Invalid URL format")

except Exception as e:
    # Sanitize exception details
    raise HTTPException(status_code=500, detail="Internal server error")
```

Validation: Test with oversized payloads, malformed URLs

---

## **Fix 4**: auth_utils.py DateTime Modernization

**File**:omega_kg/auth_utils.py
**Lines**: 3, 57
**Issue**: Deprecated datetime.utcnow()
**Actions**:

```python
# Line 3 - Update imports:
from datetime import datetime, timezone

# Line 57 - Replace deprecated call:
# BEFORE:
datetime.utcnow()

# AFTER:
datetime.now(timezone.utc)

Validation: Verify timezone-aware datetime object returned
```

---

## **Fix 5**: capture_server.py Logging Standardization

**File**:omega_kg/capture_server.py
**Lines**: 47-65 (lifespan function)
**Issue**: Print statements instead of proper logging
**Actions**:

```python
# Replace all print() with appropriate logger calls:
# BEFORE:
print(f"Starting up... {some_var}")
traceback.print_exc()

# AFTER:
logger.debug(f"Starting up... {some_var}")
logger.exception("Error occurred")

# Remove:
import traceback
```

## **Validation**: Confirm logger instance available in scope

### Post-Implementation Protocol

**Run smoke tests**: `poetry run python scripts/smoke_test.py`

Verify all imports resolve

Check no syntax errors

Confirm async/await consistency

**Success Criteria (Done Means Done)**

- [ ] All 5 fixes implemented atomically
- [ ] Smoke tests pass
- [ ] No import errors
- [ ] Async functions use await consistently
- [ ] Security validations prevent oversized requests
- [ ] Logging uses structured logger instead of print
- [ ] Backup files created (.backup extension)