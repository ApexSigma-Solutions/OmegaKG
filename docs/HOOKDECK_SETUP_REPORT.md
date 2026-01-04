# Hookdeck Webhook Setup Report

## Summary

Successfully configured Linear and GitHub webhooks for the OmegaKG capture server with Hookdeck forwarding.

## Changes Made

### 1. Fixed Linear Webhook Path Mismatch

**File**: `scripts/start_full_stack.ps1`

**Issue**: Startup script was forwarding to `/webhooks/linear` (plural) but the capture server expected `/webhook/linear` (singular).

**Fix**: Updated line 123 from:
```powershell
$HookdeckArgs = "listen 8766 linear --path /webhooks/linear --url http://${env:HOST}:8765/webhooks/linear"
```
to:
```powershell
$HookdeckArgs = "listen 8766 linear --path /webhook/linear --url http://${env:HOST}:8765/webhook/linear"
```

Also updated the log message on line 125 to reflect the correct path.

### 2. Registered GitHub Receiver Router

**File**: `omega_kg/capture_server.py`

**Issue**: The GitHub webhook receiver router was defined but never registered in the FastAPI application.

**Fix**: Added GitHub receiver router registration:
- Line 44: Added import: `from omega_kg.routers import github_receiver, linear_receiver`
- Line 608: Registered router: `app.include_router(github_receiver.router, tags=["GitHub Ingest"])`

Also updated the root endpoint response (line 638) to include the GitHub webhook endpoint.

### 3. Verified Webhook Endpoints

Both webhook endpoints are now properly configured and accessible:

#### Linear Webhook
- **Path**: `POST /webhook/linear`
- **Status**: ✅ Working
- **Port**: 8766 (Hookdeck listener)
- **Forwards to**: `http://localhost:8765/webhook/linear`

#### GitHub Webhook
- **Path**: `POST /webhooks/github`
- **Status**: ✅ Working
- **Port**: 8767 (Hookdeck listener)
- **Forwards to**: `http://localhost:8765/webhooks/github`
- **Note**: Requires `X-Hub-Signature-256` header for verification

## Current Configuration

### Capture Server
- **Host**: `0.0.0.0`
- **Port**: `8765`
- **Status**: ✅ Running
- **Health Check**: `http://localhost:8765/health`

### Hookdeck Listeners

#### Linear Listener
```bash
hookdeck listen 8766 linear \
  --path /webhook/linear \
  --url http://localhost:8765/webhook/linear
```
- **Local Port**: 8766
- **Destination**: `http://localhost:8765/webhook/linear`

#### GitHub Listener
```bash
hookdeck listen 8767 github \
  --path /webhooks/github \
  --url http://localhost:8765/webhooks/github
```
- **Local Port**: 8767
- **Destination**: `http://localhost:8765/webhooks/github`

## Usage Instructions

### Starting the Full Stack

Run the startup script:
```powershell
.\scripts\start_full_stack.ps1
```

This will:
1. Start the capture server on port 8765
2. Display instructions for starting Hookdeck listeners manually (requires interactive terminal)

### Manual Hookdeck Startup

Since Hookdeck CLI requires an interactive terminal, start the listeners in separate terminal windows:

**Terminal 1 - Linear Listener:**
```bash
hookdeck listen 8766 linear --path /webhook/linear --url http://localhost:8765/webhook/linear
```

**Terminal 2 - GitHub Listener:**
```bash
hookdeck listen 8767 github --path /webhooks/github --url http://localhost:8765/webhooks/github
```

### Configuring Webhook Providers

#### Linear
1. Get the source URL from Hookdeck CLI output
2. In Linear webhook settings, set the URL to: `https://<hookdeck-source-url>`
3. Set the secret to your `LINEAR_WEBHOOK_SECRET` from `.env`

#### GitHub
1. Get the source URL from Hookdeck CLI output
2. In GitHub webhook settings, set the URL to: `https://<hookdeck-source-url>`
3. Set the secret to your `GITHUB_WEBHOOK_SECRET` from `.env`
4. Select events to receive (e.g., Push, Pull Request)

### Testing Webhooks

#### Test Linear Webhook
```bash
curl -X POST http://localhost:8765/webhook/linear \
  -H "Content-Type: application/json" \
  -d '{"type": "Issue", "action": "create", "data": {"title": "Test Issue"}}'
```

#### Test GitHub Webhook
```bash
curl -X POST http://localhost:8765/webhooks/github \
  -H "Content-Type: application/json" \
  -d '{"action": "opened", "pull_request": {"title": "Test PR"}}'
```

## Verification

All endpoints are accessible:
- ✅ Root endpoint: `GET http://localhost:8765/`
- ✅ Health check: `GET http://localhost:8765/health`
- ✅ Linear webhook: `POST http://localhost:8765/webhook/linear`
- ✅ GitHub webhook: `POST http://localhost:8765/webhooks/github`

## Troubleshooting

### Hookdeck CLI Not Working
If you see "cannot execute binary file" or "Permission denied" errors:
1. Ensure Hookdeck CLI is properly installed: `npm install -g @hookdeck/cli`
2. Check if running in the correct environment (WSL vs Windows)
3. Try running with `npx @hookdeck/cli listen ...` instead of `hookdeck listen ...`

### Port Already in Use
If you get "port already in use" errors:
1. Check for existing processes: `netstat -ano | grep :8765`
2. Kill existing process: `powershell -Command "Stop-Process -Id <PID> -Force"`

### Webhook Not Received
1. Verify Hookdeck listener is running
2. Check Hookdeck dashboard for received webhooks
3. Review capture server logs
4. Test with curl directly to the endpoint

## Files Modified

1. `scripts/start_full_stack.ps1` - Fixed Linear webhook path
2. `omega_kg/capture_server.py` - Registered GitHub receiver router

## Next Steps

1. Configure your webhook providers (Linear, GitHub) with the Hookdeck source URLs
2. Test webhook delivery by creating events in your providers
3. Monitor webhook processing in the capture server logs
