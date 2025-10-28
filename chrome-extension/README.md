# Omega_KG Chrome Extension

AI conversation capture extension for Omega_KG knowledge graph system.

## Features

- ✅ **Auto-capture** conversations from 6 AI platforms
- ✅ **Manual capture** via floating Ω button (bottom-right)
- ✅ **Visual notifications** when capture succeeds/fails
- ✅ **Duplicate detection** prevents re-capturing same conversation
- ✅ **Neo4j integration** via local capture server

## Supported Platforms

- Claude.ai
- ChatGPT (chat.openai.com & chatgpt.com)
- Gemini
- Perplexity
- GitHub Copilot
- Qwen

## Installation

### 1. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder
5. Extension will appear in your toolbar

### 2. Start Capture Server

The extension sends data to a local FastAPI server on port 8765.

```powershell
# Start server (run from Omega_KG root directory)
poetry run python -m omega_kg.capture_server

# Or use the startup script
.\scripts\start-capture-server.ps1
```

Verify server is running:
```powershell
Invoke-WebRequest http://127.0.0.1:8765/health
# Should return: {"status":"healthy","vault_accessible":true,"neo4j_connected":true}
```

## Usage

### Automatic Capture

The extension automatically captures conversations:
- When page loads (after 3 seconds)
- When you switch tabs (on tab hide)
- When you close/refresh the page
- When new messages appear (2 second debounce)

### Manual Capture

Click the floating **Ω** button (bottom-right corner) to force immediate capture.

### Visual Feedback

- **Green notification**: "Conversation captured!" ✅
- **Red notification**: "Capture failed - check server" ❌
- Check browser console (F12) for detailed logs

## Troubleshooting

### Service Worker Becomes Inactive

**This is normal Chrome behavior!** Service workers go inactive to save resources. The extension will automatically wake up when:
- You visit an AI chat page
- A message is sent from content script
- The periodic health check alarm fires (every 5 minutes)

To verify service worker status:
1. Go to `chrome://extensions/`
2. Find "Omega_KG Chat Capture"
3. Click "service worker" link
4. Check console for logs

### No Conversations Captured

**Check these in order:**

1. **Is the capture server running?**
   ```powershell
   Invoke-WebRequest http://127.0.0.1:8765/health
   ```

2. **Are you on a supported platform?**
   - Look for the floating Ω button (bottom-right)
   - If no button appears, platform is not supported

3. **Check browser console (F12)**
   ```
   [Omega_KG] Initialized for Claude.ai  ✅ Good
   [Omega_KG] Extracted 4 messages       ✅ Good
   [Omega_KG] ✅ Captured successfully   ✅ Good
   ```

4. **Check server logs**
   - Server should show: `INFO - Received capture request: Claude.ai (X messages)`
   - If no logs, extension isn't sending requests

5. **Reload the extension**
   - Go to `chrome://extensions/`
   - Click refresh icon on Omega_KG extension
   - Reload the AI chat page

### DOM Selectors Out of Date

AI platforms frequently change their HTML structure. If messages aren't being extracted:

1. Open browser console (F12)
2. Look for: `[Omega_KG] Found 0 message elements`
3. Update selectors in `content.js` → `extractMessages()` function
4. Reload extension

### Server Connection Failed

**Error**: `❌ Server error: Failed to fetch`

**Causes**:
- Capture server not running on port 8765
- Firewall blocking localhost connections
- CORS issues (should not happen with localhost)

**Fix**:
```powershell
# Restart server
poetry run python -m omega_kg.capture_server

# Check if port 8765 is in use
Get-NetTCPConnection -LocalPort 8765
```

## Architecture

```
Chrome Extension (content.js)
    ↓ Extract messages from DOM
    ↓ Send to background.js
Background Service Worker (background.js)  
    ↓ POST to http://localhost:8765/capture
Capture Server (capture_server.py)
    ↓ Format as markdown
    ↓ Write to Obsidian vault
    ↓ Percolate to Neo4j
Knowledge Graph (Neo4j)
    ↓ ChatSession + Decision nodes
```

## Files

- `manifest.json` - Extension configuration (Manifest V3)
- `background.js` - Service worker (sends to capture server)
- `content.js` - DOM extraction and capture logic
- `icon*.svg` - Extension icons (Ω symbol)
- `README.md` - This file

## Development

### Enable Debug Logging

All logs are prefixed with `[Omega_KG]` for easy filtering.

**Content script logs** (F12 on AI chat page):
```javascript
[Omega_KG] Initialized for Claude.ai
[Omega_KG] Found 6 message elements on Claude.ai
[Omega_KG] Extracted 6 messages from 6 elements
[Omega_KG] ✅ Captured 6 messages from Claude.ai
```

**Service worker logs** (`chrome://extensions/` → service worker):
```javascript
[Omega_KG] Service worker received message: CAPTURE_CONVERSATION
[Omega_KG] Attempting to save to localhost...
[Omega_KG] Server response: {success: true, file_path: "...", nodes_created: 3}
[Omega_KG] ✅ Captured successfully
```

### Adding New Platforms

1. Add hostname to `detectPlatform()` in `content.js`
2. Add selectors to `extractMessages()` config
3. Add URL pattern to `manifest.json` (both `host_permissions` and `content_scripts`)
4. Create folder in Obsidian vault: `AI_Conversations/{Platform}/`
5. Reload extension and test

## Known Limitations

- **Service worker goes inactive** - This is normal Manifest V3 behavior, not a bug
- **DOM changes break extraction** - AI platforms update frequently, selectors need maintenance
- **No offline support** - Requires running capture server
- **Single conversation per page** - Doesn't handle multiple simultaneous chats

## License

Part of the Omega_KG project. See root LICENSE file.

## Version History

- **1.1.0** (2025-10-28)
  - Fixed service worker inactive issue with better logging
  - Updated DOM selectors for current Claude.ai structure
  - Added manual capture button (floating Ω)
  - Added visual notifications
  - Added support for 6 AI platforms
  - Improved error handling and debugging

- **1.0.0** (Initial release)
  - Basic conversation capture
  - 4 platform support
