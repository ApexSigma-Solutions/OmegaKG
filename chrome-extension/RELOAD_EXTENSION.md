# 🔄 Chrome Extension Reload Instructions

## ⚡ Quick Reload (After Code Changes)

Your `content.js` file was reformatted and lost the GitHub Copilot selectors. They have been **restored** and you need to reload the extension.

### Steps:

1. **Open Chrome Extensions Page**
   ```
   chrome://extensions/
   ```

2. **Find "Omega_KG AI Conversation Capture"**
   - Look for your extension in the list

3. **Click the Reload Button** 🔄
   - It's a circular arrow icon next to the extension

4. **Verify the Reload**
   - Go back to your GitHub Copilot task page
   - Refresh the page (F5)
   - Open DevTools Console (F12)
   - You should see:
     ```
     [Omega_KG] Initialized for github_copilot
     ```
   - You should **NOT** see:
     ```
     [Omega_KG] No selector config for platform: GitHub_Copilot
     ```

## 🎯 What Was Fixed

The file `chrome-extension/content.js` was simplified by a formatter, removing GitHub Copilot support. The following has been restored:

### 1. Platform Detection (Line ~19)
```javascript
if (hostname.includes('github.com') && pathname.includes('/copilot/')) return 'github_copilot';
```

### 2. Selector Configuration (Lines ~46-51)
```javascript
github_copilot: {
  container: '[class*="TaskChat-module"]',
  userMsg: '.UserInitialMessage-module__container--j2mCV',
  assistantMsg: '.markdown-body.MarkdownRenderer-module__container--dNKcF:not(.UserInitialMessage-module__markdown--adqIo)',
  timestamp: null
}
```

## 🧪 Testing Checklist

After reloading:

- [ ] Extension reloaded successfully
- [ ] Navigate to GitHub Copilot task page
- [ ] Refresh the page
- [ ] Open DevTools Console (F12)
- [ ] See `[Omega_KG] Initialized for github_copilot`
- [ ] See `[Omega_KG] Found X messages from github_copilot` (where X > 0)
- [ ] **No** "No selector config" errors

## ⚠️ If Still Not Working

1. **Hard Reload Extension**
   - Toggle extension off/on in `chrome://extensions/`
   - Then reload again

2. **Check Extension Permissions**
   - Ensure `manifest.json` includes GitHub in `host_permissions`
   - Should have: `"*://github.com/*"`

3. **Verify Content Script Injection**
   - In `chrome://extensions/` → Details → Inspect views
   - Check if content script is running on GitHub pages

4. **Clear Extension Data**
   - Right-click extension icon → Options → Clear Cache (if available)

## 📋 Current Configuration

**Platform Key**: `github_copilot`  
**URL Pattern**: `github.com` + `/copilot/`  
**Container**: Elements with `TaskChat-module` classes  
**User Messages**: `.UserInitialMessage-module__container--j2mCV`  
**Assistant Messages**: Markdown bodies excluding user message markdown  

## 🔍 Debugging

If messages still aren't captured, run this in the console on a GitHub Copilot page:

```javascript
// Check platform detection
console.log('Platform:', window.location.hostname, window.location.pathname);

// Check for containers
console.log('Containers:', document.querySelectorAll('[class*="TaskChat-module"]').length);

// Check for user messages
console.log('User msgs:', document.querySelectorAll('.UserInitialMessage-module__container--j2mCV').length);

// Check for assistant messages
console.log('Assistant msgs:', document.querySelectorAll('.markdown-body.MarkdownRenderer-module__container--dNKcF:not(.UserInitialMessage-module__markdown--adqIo)').length);
```

Expected output:
```
Platform: github.com /copilot/tasks/pull/PR_kwDOQH9oC86wdWN3
Containers: 1 (or more)
User msgs: 1 (at least)
Assistant msgs: 1 (or more)
```

---

**Last Updated**: October 29, 2025  
**Issue**: File reformatted, GitHub Copilot support lost  
**Resolution**: Selectors restored in `content.js`  
**Action Required**: Reload extension in Chrome
