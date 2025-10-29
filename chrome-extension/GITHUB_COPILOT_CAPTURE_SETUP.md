# GitHub Copilot Capture Configuration

## Overview

This document describes the GitHub Copilot conversation capture setup for the Omega_KG Chrome extension.

## DOM Structure Analysis (Oct 2025)

Based on console log analysis from `https://github.com/copilot/tasks/pull/PR_kwDOQH9oC86wdWN3`:

### Key Container Elements
- **Root Container**: `DIV.TaskChat-module__root--i8enD`
- **Chat Container**: `DIV.TaskChat-module__container--n3jVO`
- **Scroll Container**: `DIV.ChatScrollContainer-module__container--z_iNX TaskChat-module__scrollContainer--ENR5a`
- **Content**: `DIV.TaskChat-module__content--X5M4z`

### Message Types

#### User Messages
- **Container**: `DIV.UserInitialMessage-module__container--j2mCV`
- **Started Task Indicator**: `DIV.UserInitialMessage-module__startedTaskMessage--Llm_V`
- **Message Text**: `P.UserInitialMessage-module__message--WKLo0`
- **Markdown Content**: `DIV.markdown-body MarkdownRenderer-module__container--dNKcF UserInitialMessage-module__markdown--adqIo`

Example structure:
```html
<div class="UserInitialMessage-module__container--j2mCV">
  <div class="UserInitialMessage-module__startedTaskMessage--Llm_V">
    <p class="UserInitialMessage-module__message--WKLo0">SteynSean11 started a task</p>
  </div>
  <div class="markdown-body MarkdownRenderer-module__container--dNKcF UserInitialMessage-module__markdown--adqIo">
    @Co-pilot address all comments and merge these PR's
  </div>
</div>
```

#### Copilot Response Messages
- **Initial Messages Container**: `DIV.TaskChat-module__initialMessages--zIGn9`
- **Markdown Content**: `DIV.markdown-body MarkdownRenderer-module__container--dNKcF`

## Implemented Selectors

### Message Selection
```javascript
messages: '.UserInitialMessage-module__container--j2mCV, [class*="TaskChat-module"][class*="message"], .markdown-body.MarkdownRenderer-module__container--dNKcF'
```

This selector targets:
1. User initial message containers
2. Any TaskChat module message elements
3. Markdown body containers with rendered content

### User Detection
```javascript
isUser: (el) => {
  return (
    el.classList.contains("UserInitialMessage-module__container--j2mCV") ||
    el.querySelector(".UserInitialMessage-module__startedTaskMessage--Llm_V") !== null ||
    el.closest('[class*="UserInitialMessage"]') !== null
  );
}
```

Logic:
- Direct match on `UserInitialMessage-module__container--j2mCV` class
- Presence of "started task" message element
- Ancestor with UserInitialMessage class pattern

### Text Extraction
```javascript
getText: (el) => {
  // Try to extract from markdown content first
  const markdown = el.querySelector(".markdown-body.MarkdownRenderer-module__container--dNKcF");
  if (markdown) return markdown.textContent;
  
  // Otherwise get from the message container
  const content = el.querySelector('[class*="message"]') || el;
  return content.textContent;
}
```

Priority:
1. Extract from markdown-body container (clean formatted content)
2. Fall back to message container
3. Fall back to element itself

## Testing Instructions

### 1. Reload Extension
```bash
# In Chrome
1. Navigate to chrome://extensions/
2. Find "Omega_KG AI Conversation Capture"
3. Click reload icon (circular arrow)
```

### 2. Test on GitHub Copilot
1. Navigate to any GitHub Copilot task page:
   - Format: `https://github.com/copilot/tasks/pull/{PR_ID}`
   - Example: `https://github.com/copilot/tasks/pull/PR_kwDOQH9oC86wdWN3`

2. Open browser DevTools console (F12)

3. Look for capture logs:
   ```
   [Omega_KG] Initialized for GitHub_Copilot
   [Omega_KG] Page loaded, scheduling initial capture
   [Omega_KG] Found X message elements on GitHub_Copilot
   [Omega_KG] Attempting capture: {platform: 'GitHub_Copilot', messageCount: X, ...}
   ```

### 3. Verify Capture
Expected behavior:
- ✅ Should see `Found X message elements` (where X > 0)
- ✅ Should see `Captured conversation` with actual message count
- ✅ Should NOT see "No messages extracted, skipping capture"

### 4. Check Captured Data
1. Open FastAPI capture server logs or database
2. Look for POST requests to `/capture`
3. Verify conversation structure:
```json
{
  "platform": "GitHub_Copilot",
  "url": "https://github.com/copilot/tasks/pull/...",
  "messages": [
    {
      "role": "user",
      "content": "@Co-pilot address all comments...",
      "timestamp": "..."
    },
    {
      "role": "assistant", 
      "content": "Copilot response...",
      "timestamp": "..."
    }
  ]
}
```

## Troubleshooting

### Issue: "No selector config for platform: GitHub_Copilot"
**Solution**: Extension code not updated. Reload extension completely.

### Issue: "No messages extracted, skipping capture"
**Possible causes**:
1. **Wrong page**: Not on a GitHub Copilot Tasks page
2. **Messages not loaded**: Wait for page to fully load
3. **DOM changed**: GitHub updated their UI (see Updating Selectors below)

### Issue: All messages captured as "assistant" role
**Cause**: `isUser()` function not correctly identifying user messages
**Debug**:
```javascript
// In console, test selector manually:
document.querySelectorAll('.UserInitialMessage-module__container--j2mCV')
// Should return user message elements
```

## Updating Selectors (If GitHub Changes DOM)

### 1. Enable Debug Mode
The debug output in console logs shows:
```
=== Selector Patterns Found ===
1x: DIV.TaskChat-module__root--i8enD []
1x: DIV.UserInitialMessage-module__container--j2mCV []
...
```

### 2. Identify Patterns
Look for:
- User message containers (usually have "user" or "initial" in class)
- Response containers (usually have "response", "assistant", or "copilot")
- Markdown/content containers (where actual text lives)

### 3. Update Selectors in content.js
Modify the `GitHub_Copilot` configuration in the `selectors` object.

## Known Limitations

1. **CSS Module Hashes**: Class names like `TaskChat-module__root--i8enD` include hash suffixes that may change
   - **Mitigation**: Use attribute selectors with wildcards `[class*="TaskChat-module"]`

2. **Dynamic Content**: Messages may load asynchronously
   - **Mitigation**: MutationObserver watches for DOM changes and retries capture

3. **PR-Specific URLs**: Currently only works on PR task pages
   - **Future**: Extend to other GitHub Copilot interfaces (workspace chat, inline suggestions)

## Next Steps

- [ ] Test on multiple GitHub Copilot task pages
- [ ] Verify user/assistant role detection accuracy
- [ ] Test with longer conversations (>10 messages)
- [ ] Add support for GitHub Copilot Workspace chat
- [ ] Add support for inline Copilot suggestions capture

## Related Files

- **Selector Config**: `chrome-extension/content.js` (lines 120-145)
- **Platform Detection**: `chrome-extension/content.js` (lines 15-25)
- **Capture Logic**: `chrome-extension/content.js` (lines 200-250)
- **Server Endpoint**: `omega_kg/capture_server.py`

---

**Last Updated**: October 29, 2025  
**Tested On**: GitHub Copilot Tasks (PR pages)  
**Status**: ✅ Configured, awaiting testing
