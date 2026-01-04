# GitHub Webhook Integration Guide

## Overview

This guide provides step-by-step instructions for configuring and validating the GitHub webhook integration in OmegaKG. The integration enables automatic Linear issue closure and Obsidian note synchronization when PRs with "Fixes [TEAM-ID]" patterns are merged.

## Architecture

The integration follows this flow:

```
GitHub PR Merge → Webhook → Event Storage → Background Processing → Linear Update → Obsidian Sync
```

### Components

1. **Webhook Receiver** (`/webhooks/github`) - Receives GitHub events
2. **Event Processor** - Background worker that processes events
3. **GitHub Processor** - Parses commit messages and updates Linear issues
4. **Linear Sync** - Updates Obsidian notes based on Linear changes

## Configuration

### 1. Environment Variables

Add the following to your `.env` file:

```ini
# GitHub Configuration
GITHUB_WEBHOOK_SECRET=your-unique-webhook-secret-here
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Linear Configuration
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxx
LINEAR_DONE_STATE_ID=state-id-for-done-status
```

### 2. GitHub Personal Access Token

Create a GitHub Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
4. Click "Generate token"
5. **Copy the token immediately** - you won't see it again
6. Add to `.env` file as `GITHUB_TOKEN`

### 3. GitHub Webhook Setup

In your GitHub repository:

1. Go to Settings → Webhooks
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: `https://your-ngrok-url.ngrok.io/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: Same as `GITHUB_WEBHOOK_SECRET` in `.env`
   - **Which events**: Select "Let me select individual events"
     - ✅ Pull requests
   - ✅ Active
4. Click "Add webhook"

### 4. Get Linear Done State ID

Run this command to find the "Done" state ID for your Linear team:

```bash
curl -H "Authorization: ${LINEAR_API_KEY}" \
  -H "Content-Type: application/json" \
  https://api.linear.app/graphql \
  -d '{
    "query": "query { team(id: LINEAR_TEAM_ID) { states { nodes { id name type }}}}"
  }' | jq '.data.team.states.nodes[] | select(.type=="completed") | .id'
```

Copy the result and add to `.env` as `LINEAR_DONE_STATE_ID`.

### 5. Start Capture Server

```bash
# Start with ngrok (for webhook testing)
cd d:\projects\OmegaKG\Omega_KG_stable
poetry run capture-server
```

The server will start ngrok automatically if `ENABLE_NGROK=true` in `.env`.

**Note the ngrok URL from the logs** - you'll need this for the GitHub webhook configuration.

## Usage

### Creating PRs with Issue References

Use one of these keywords followed by the issue ID in brackets:

- `Fixes [PROJ-123]` - Standard format
- `Closes [LIN-456]` - Alternative keyword
- `Resolves [TEAM-789]` - Alternative keyword

**Examples:**

```
Fixes [PROJ-123] - Add authentication fix

Closes [LIN-456] - Update API documentation

Resolves [TEAM-789] - Fix bug in payment processing
```

### Testing the Integration

#### Step 1: Verify Server is Running

```bash
curl http://localhost:8765/health
```

You should see:
```json
{
  "status": "online",
  "version": "4.4.2",
  "database": "connected",
  "event_processor": "running"
}
```

#### Step 2: Create a Test PR

1. Create a branch: `git checkout -b test/fix-issue`
2. Make a small change
3. Commit with message: `Fixes [PROJ-123] - Test fix`
4. Push branch: `git push -u origin test/fix-issue`
5. Create PR on GitHub
6. Merge PR

#### Step 3: Monitor Logs

Watch the capture server logs for:

```
Received GitHub webhook event ID: X
Processing PR merge: user/repo#123
Found 1 issue reference(s): PROJ-123
✓ Successfully updated PROJ-123 to done state
```

#### Step 4: Verify Linear Issue

1. Open Linear issue PROJ-123
2. Verify status is "Done"
3. Check state type is "completed"

#### Step 5: Verify Obsidian Note

1. Find note with `linear_id: PROJ-123` in frontmatter
2. Verify `status: Done` in frontmatter
3. Check note was recently updated

## Validation

### Automated Tests

Run the test suite:

```bash
# Unit tests
poetry run pytest tests/unit/test_github_processor.py -v

# Integration tests
poetry run pytest tests/integration/test_github_webhook.py -v

# All tests
poetry run pytest tests/ -v
```

Expected output:
```
========================= test session starts =========================
tests/unit/test_github_processor.py::TestIssueReferencePattern::test_fixes_pattern PASSED
tests/unit/test_github_processor.py::TestIssueReferencePattern::test_closes_pattern PASSED
tests/integration/test_github_webhook.py::TestGitHubWebhookIntegration::test_webhook_valid_signature PASSED
...
========================= 15 passed in 2.34s ========================
```

### Manual Verification Checklist

- [ ] Capture server running with ngrok
- [ ] GitHub webhook configured with correct URL
- [ ] Webhook secret matches `GITHUB_WEBHOOK_SECRET`
- [ ] GitHub token has `repo` scope
- [ ] Linear API key is valid
- [ ] `LINEAR_DONE_STATE_ID` is configured
- [ ] Test PR created with "Fixes [ISSUE-ID]" message
- [ ] PR merged
- [ ] GitHub webhook received (check logs)
- [ ] Linear issue status changed to "Done"
- [ ] Obsidian note frontmatter updated to "Done"
- [ ] No errors in logs

### Database Verification

Check the raw webhook events table:

```sql
SELECT id, source, processed_status, received_at, error_log
FROM raw_webhook_events
WHERE source = 'github'
ORDER BY received_at DESC
LIMIT 10;
```

Should show:
- `source = 'github'`
- `processed_status = true`
- `error_log = NULL`

### Log Analysis

Common log patterns to look for:

**✅ Success:**
```
Received GitHub webhook event ID: 123
Processing PR merge: user/repo#42
Found 1 issue reference(s): PROJ-123
✓ Successfully updated PROJ-123 to done state
```

**⚠️ Warning:**
```
No issue references found in PR user/repo#42
```

**❌ Error:**
```
Linear issue not found: PROJ-123
```

## Troubleshooting

### Webhook Not Received

**Check:**
1. GitHub webhook URL is correct
2. Server is running with ngrok
3. ngrok URL is public
4. Firewall allows port 8765

**Solution:**
```bash
# Verify server is running
curl http://localhost:8765/health

# Check ngrok tunnel
curl https://abc-def-123.ngrok.io/webhooks/github
# Should return 400 (missing signature) not connection error
```

### Signature Verification Failed

**Error:**
```
HTTPException(status_code=401, detail="Invalid signature")
```

**Causes:**
- Webhook secret in GitHub doesn't match `GITHUB_WEBHOOK_SECRET`
- Secret has special characters

**Solution:**
1. Regenerate webhook secret in GitHub
2. Update `.env` file
3. Restart capture server

### Linear Issue Not Found

**Error:**
```
Linear issue not found: PROJ-123
```

**Causes:**
- Issue identifier is incorrect
- Issue was deleted
- Team ID mismatch

**Solution:**
1. Verify issue exists in Linear
2. Check identifier format (TEAM-NUMBER)
3. Verify Linear API key has access to the issue

### Issue Not Updated

**Error:**
```
Failed to update Linear issue PROJ-123: 401 Unauthorized
```

**Causes:**
- `LINEAR_API_KEY` is invalid
- API key doesn't have write access
- `LINEAR_DONE_STATE_ID` is incorrect

**Solution:**
```bash
# Test Linear API key
curl -H "Authorization: ${LINEAR_API_KEY}" \
  https://api.linear.app/graphql \
  -d '{"query":"{ me { id name } }"}'

# Verify state ID
curl -H "Authorization: ${LINEAR_API_KEY}" \
  https://api.linear.app/graphql \
  -d "{\"query\":\"{ issue(id: ISSUE_ID) { id state { id name type } } }\"}"
```

### No Obsidian Sync

**Check:**
1. Linear issue has `linear_id` in frontmatter
2. Note exists in vault
3. Vault path is correct in settings

**Solution:**
```bash
# Search for note with linear_id
grep -r "linear_id: PROJ-123" vault/
```

## Advanced Configuration

### Multiple Issue References

A single PR can reference multiple issues:

```
Fixes [PROJ-123], [LIN-456], and [TEAM-789]
```

All referenced issues will be updated to "Done".

### Custom Issue Patterns

Modify `ISSUE_REFERENCE_PATTERN` in:
`omega_kg/domain/github/processor.py`

Default pattern:
```python
r"\b(?:fixes|closes|resolves)\s+\[([A-Z]+-\d+)\]"
```

To add more keywords:
```python
r"\b(?:fixes|closes|resolves|fix|close|resolve)\s+\[([A-Z]+-\d+)\]"
```

### Webhook Event Filtering

The processor only handles `action=closed` and `merged=true` events.
Other events (opened, reopened, etc.) are logged but ignored.

## Monitoring

### Metrics

The EventProcessor exposes metrics:

```python
from omega_kg.workers.event_processor import event_processor

stats = event_processor.metrics.get_stats()
print(f"Processed: {stats['processed_total']}")
print(f"Errors: {stats['errors_total']}")
```

### Health Checks

Add to monitoring:
- `GET /health` - Application health
- Database connection status
- Event processor running status

## Security

### Best Practices

1. **Webhook Secret**: Use a strong, unique secret
2. **HTTPS Only**: Always use HTTPS for webhook URLs
3. **Token Security**: Store tokens in `.env` (never commit)
4. **Rate Limiting**: GitHub rate limits webhook deliveries
5. **Replay Protection**: Consider tracking event IDs (not implemented)

### Production Deployment

1. Use GitHub App instead of PAT for better security
2. Implement event ID tracking to prevent replay attacks
3. Add rate limiting per repository
4. Monitor webhook delivery failures
5. Set up alerting for processing errors

## API Reference

### Webhook Endpoint

**URL**: `POST /webhooks/github`

**Headers**:
- `X-Hub-Signature-256`: `sha256=<signature>`
- `Content-Type`: `application/json`

**Response**:
```json
{
  "status": "persisted",
  "id": 123
}
```

**Error Responses**:
- `400`: Missing or invalid signature, invalid JSON
- `401`: Invalid signature

### Supported Events

- `pull_request` with `action=closed` and `merged=true`

## Support

For issues or questions:
1. Check logs in capture server
2. Run tests: `poetry run pytest tests/`
3. Verify configuration with this guide
4. Check GitHub webhook delivery logs
5. Review Linear API key permissions

## Summary

The GitHub webhook integration provides seamless automation from PR merges to Linear issue updates and Obsidian note synchronization. Follow this guide to configure, test, and troubleshoot the integration effectively.
