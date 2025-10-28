# Chrome Extension Selector Debugging Guide

## Quick Fix: Finding the Right Selectors

When the extension shows "Found 0 message elements", the DOM selectors are outdated.

### Steps to Fix:

1. **Go to the AI platform** (Claude.ai, Gemini, etc.)
2. **Right-click the Ω button** (bottom-right floating button)
3. **Open browser console** (F12)
4. **Check the debug output**:
   ```
   === Omega_KG Debug Mode ===
   Platform: Claude.ai
   
   === Selector Patterns Found ===
   12x: DIV.font-claude-message [user-message]
     Example text: What is the capital of France?
   
   8x: DIV.markdown-content [assistant-response]
     Example text: The capital of France is Paris...
   ```

5. **Update `content.js`** with the found selectors:
   ```javascript
   'Claude.ai': {
     messages: '[data-testid*="user-message"], [data-testid*="assistant-response"]',
     isUser: (el) => el.getAttribute('data-testid')?.includes('user'),
     getText: (el) => el.textContent,
     timestamp: null
   }
   ```

6. **Reload extension** (chrome://extensions/ → refresh icon)
7. **Test capture** (click Ω button)

## Current Status (Oct 28, 2025)

| Platform | Status | Notes |
|----------|--------|-------|
| ChatGPT | ✅ Working | Uses `[data-message-author-role]` |
| Claude.ai | ❌ 0 messages | Needs selector update |
| Gemini | ❌ 0 messages | Needs selector update |
| Perplexity | ❓ Untested | May need update |

## How to Update Selectors

### Method 1: Debug Mode (Recommended)
Right-click Ω button → Check console → Copy selectors

### Method 2: Manual Inspection
1. Open browser DevTools (F12)
2. Click "Inspect Element" on a message
3. Look for:
   - `data-testid` attributes
   - `data-message-*` attributes
   - Class names with "message", "chat", "response"
4. Test selector in console:
   ```javascript
   document.querySelectorAll('[data-testid*="message"]')
   ```
5. Update `content.js` with working selector

## Platform-Specific Tips

### Claude.ai
- Look for: `data-testid` attributes
- User messages often have: `user-message`, `human-message`
- Assistant messages: `assistant-message`, `ai-response`
- Content wrapper: `.font-claude-message`, `.markdown-content`

### Gemini
- Look for: `.model-response-text`, `.user-query`
- May use: `data-message-author-role`
- Content wrapper: `.markdown`, `.message-content`

### Common Patterns
All AI platforms typically use one of these:
- `[data-message-author-role="user|assistant"]` (ChatGPT)
- `[data-testid*="message"]` (Claude, others)
- `.message-content`, `.chat-message` (class-based)
- `[role="article"]` with message content

## Testing Selectors

Run this in browser console on the AI chat page:

```javascript
// Test if selector finds messages
const elements = document.querySelectorAll('YOUR_SELECTOR_HERE');
console.log(`Found ${elements.length} elements`);
elements.forEach((el, i) => {
  console.log(`${i}: ${el.textContent.substring(0, 50)}...`);
});
```

Example for Claude:
```javascript
const messages = document.querySelectorAll('[data-testid*="message"]');
console.log(`Found ${messages.length} messages`);
```

## After Updating Selectors

1. **Save `content.js`**
2. **Reload extension**: chrome://extensions/ → click refresh icon
3. **Reload AI chat page**
4. **Click Ω button** or wait for auto-capture
5. **Check console** for:
   ```
   [Omega_KG] Found X message elements on Platform
   [Omega_KG] Extracted X messages from X elements
   [Omega_KG] ✅ Captured X messages from Platform
   ```

## Fallback Extraction

If specific selectors fail, the extension now uses a fallback that searches for:
- `[class*="message"]`
- `[class*="chat"]`
- `[class*="conversation"]`
- `[data-testid*="message"]`
- `[role="article"]`

This should catch messages even when specific selectors are outdated.

## Need Help?

Run the troubleshoot script:
```powershell
poetry run python troubleshoot_extension.py
```

This checks:
- ✅ Capture server running
- ✅ Obsidian vault accessible
- ✅ Neo4j connected
- 📄 Recent captures

---

**Last Updated**: 2025-10-28 (after fixing ChatGPT selectors)
