// AI Chat Capture with Retry Logic
// Supports: Claude, ChatGPT, Gemini, Perplexity, GitHub Copilot, Qwen, Microsoft Copilot
// Features: Auto-retry on context invalidation, exponential backoff, error recovery

class ChatCapture {
  constructor() {
    this.capturedHashes = new Set();
    this.platform = this.detectPlatform();
    this.observer = null;
    this.conversationCache = new Map();
    this.hasShownAutoNotification = false;
    this.initializeCapture();
  }

  detectPlatform() {
    const hostname = window.location.hostname;
    const pathname = window.location.pathname;
    
    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('openai.com')) return 'chatgpt';
    if (hostname.includes('gemini.google.com')) return 'gemini';
    if (hostname.includes('perplexity.ai')) return 'perplexity';
    if (hostname.includes('github.com') && pathname.includes('/copilot/')) return 'github_copilot';
    if (hostname.includes('chat.qwen.ai')) return 'qwen';
    if (hostname.includes('copilot.microsoft.com') || hostname.includes('copilot.com')) return 'microsoft_copilot';
    
    return 'unknown';
  }

  extractMessages() {
    // Platform-specific selectors
    const selectors = {
      claude: {
        container: '[data-testid="conversation"]',
        userMsg: '[data-is-streaming="false"] .font-claude-message:has(> div[data-is-streaming="false"])',
        assistantMsg: '[data-testid="message-content"]',
        timestamp: 'time'
      },
      chatgpt: {
        container: '[role="presentation"]',
        userMsg: '[data-message-author-role="user"]',
        assistantMsg: '[data-message-author-role="assistant"]',
        timestamp: null
      },
      gemini: {
        container: '[role="main"]',
        userMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="user"]',
        assistantMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="model"]',
        timestamp: null
      },
      perplexity: {
        container: '[class*="thread"]',
        userMsg: '[class*="question"]',
        assistantMsg: '[class*="answer"]',
        timestamp: null
      },
      github_copilot: {
        container: '[class*="TaskChat-module"]',
        userMsg: '.UserInitialMessage-module__container--j2mCV',
        assistantMsg: '.markdown-body.MarkdownRenderer-module__container--dNKcF:not(.UserInitialMessage-module__markdown--adqIo)',
        timestamp: null
      },
      qwen: {
        container: '[class*="content"]',
        userMsg: '[class*="user"]',
        assistantMsg: '[class*="bot"]',
        timestamp: null
      },
      microsoft_copilot: {
        container: '[class*="conversation"]',
        userMsg: '[class*="user-message"]',
        assistantMsg: '[class*="assistant-message"]',
        timestamp: null
      }
    };

    const config = selectors[this.platform];
    if (!config) return [];

    const messages = [];
    const container = document.querySelector(config.container);
    if (!container) return [];

    // Extract user messages
    const userMessages = container.querySelectorAll(config.userMsg);
    const assistantMessages = container.querySelectorAll(config.assistantMsg);

    // Interleave user and assistant messages
    const maxLength = Math.max(userMessages.length, assistantMessages.length);
    
    for (let i = 0; i < maxLength; i++) {
      if (userMessages[i]) {
        messages.push({
          role: 'user',
          content: this.cleanText(userMessages[i].textContent),
          timestamp: this.extractTimestamp(userMessages[i], config.timestamp),
          platform: this.platform
        });
      }
      
      if (assistantMessages[i]) {
        messages.push({
          role: 'assistant',
          content: this.cleanText(assistantMessages[i].textContent),
          timestamp: this.extractTimestamp(assistantMessages[i], config.timestamp),
          platform: this.platform
        });
      }
    }

    return messages;
  }

  cleanText(text) {
    // Remove UI artifacts, normalize whitespace
    return text
      .replace(/\s+/g, ' ')
      .replace(/Copy code/g, '')
      .replace(/\d+\/\d+/g, '')  // Remove message counters
      .trim();
  }

  extractTimestamp(element, selector) {
    if (!selector) return new Date().toISOString();
    
    const timeEl = element.querySelector(selector);
    if (timeEl) {
      return timeEl.getAttribute('datetime') || new Date().toISOString();
    }
    return new Date().toISOString();
  }

  startObserving() {
    // Watch for new messages
    const targetNode = document.body;
    const config = { childList: true, subtree: true };

    this.observer = new MutationObserver((mutations) => {
      // Debounce: only capture after user stops typing
      clearTimeout(this.captureTimeout);
      this.captureTimeout = setTimeout(() => {
        this.captureConversationWithRetry();
      }, 2000);  // 2 second delay after last change
    });

    this.observer.observe(targetNode, config);
  }

  async captureConversationWithRetry(maxAttempts = 3, forceCapture = false) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        return await this.captureConversation(forceCapture);
      } catch (error) {
        const isContextInvalid = error.message.includes('Extension context invalidated') || 
                                error.message.includes('Message channel closed');
        
        if (isContextInvalid && attempt < maxAttempts - 1) {
          console.warn(`[Omega_KG] Retry ${attempt + 1}/${maxAttempts} - content.js:167`, error.message);
          // Exponential backoff: 100ms, 200ms, 400ms, 800ms, 1600ms
          const delay = 100 * Math.pow(2, attempt) + Math.random() * 50;
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
        
        // Log error but don't crash - MutationObserver should continue
        if (attempt === maxAttempts - 1) {
          console.error('[Omega_KG] Failed to capture after retries (observer continues) - content.js:176', error.message);
        }
        return null;
      }
    }
  }

  async captureConversation(forceCapture = false) {
    const messages = this.extractMessages();
    if (messages.length === 0) return null;

    // Generate conversation hash (to detect duplicates)
    const conversationHash = this.hashConversation(messages);
    
    // Skip if already captured (unless forcing manual capture)
    if (!forceCapture && this.conversationCache.has(conversationHash)) return null;
    this.conversationCache.set(conversationHash, true);

    // Validate extension context before sending
    if (!chrome?.runtime) {
      throw new Error('Extension context invalidated - chrome.runtime unavailable');
    }

    try {
      // Send to background script for persistence with error handling
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Message channel closed - extension context lost'));
        }, 5000);

        chrome.runtime.sendMessage({
          type: 'CAPTURE_CONVERSATION',
          data: {
            messages,
            platform: this.platform,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            conversationHash
          }
        }, (response) => {
          clearTimeout(timeout);
          
          // Check for chrome.runtime.lastError
          if (chrome.runtime.lastError) {
            reject(new Error(`Chrome API error: ${chrome.runtime.lastError.message}`));
            return;
          }

          if (response?.success) {
            console.log(`[Omega_KG] ✅ Captured ${messages.length} messages from ${this.platform} - content.js:219`);
            this.lastCaptureTime = new Date().toLocaleTimeString();
            // Only show auto-capture notification if forced (manual) or first capture of the session
            if (forceCapture || !this.hasShownAutoNotification) {
              this.showNotification(`🎯 Captured ${messages.length} messages`, 'success', 2000);
              this.hasShownAutoNotification = true;
            }
            resolve(response);
          } else {
            reject(new Error(response?.error || 'Server error'));
          }
        });
      });
    } catch (error) {
      // Re-throw for retry logic to handle
      throw error;
    }
  }

  hashConversation(messages) {
    // Simple hash: last user message + length
    const lastUser = messages.filter(m => m.role === 'user').pop();
    return `${this.platform}-${messages.length}-${lastUser?.content.substring(0, 50)}`;
  }

  initializeCapture() {
    if (this.platform === 'unknown') {
      console.log('[Omega_KG] Platform not supported - content.js:233');
      return;
    }

    console.log(`[Omega_KG] Started capturing: ${this.platform} - content.js:237`);
    
    // Create floating UI elements
    this.createFloatingButton();
    this.createNotificationContainer();
    
    // Initial capture
    this.captureConversationWithRetry();
    
    // Start observing for changes
    this.startObserving();
  }

  createFloatingButton() {
    // Create floating capture button with Omega symbol
    this.floatingButton = document.createElement('div');
    this.floatingButton.innerHTML = 'Ω';
    this.floatingButton.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 50px;
      height: 50px;
      background: linear-gradient(135deg, #019387 0%, #017a70 100%);
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(1,147,135,0.4);
      z-index: 10000;
      transition: all 0.3s ease;
      user-select: none;
      font-family: 'Times New Roman', serif;
      border: 2px solid #FF7C87;
    `;

    // Hover effects
    this.floatingButton.addEventListener('mouseenter', () => {
      this.floatingButton.style.transform = 'scale(1.1)';
      this.floatingButton.style.boxShadow = '0 6px 16px rgba(255,124,135,0.6)';
      this.floatingButton.style.borderColor = '#FF7C87';
      this.floatingButton.style.borderWidth = '3px';
    });

    this.floatingButton.addEventListener('mouseleave', () => {
      this.floatingButton.style.transform = 'scale(1)';
      this.floatingButton.style.boxShadow = '0 4px 12px rgba(1,147,135,0.4)';
      this.floatingButton.style.borderColor = '#FF7C87';
      this.floatingButton.style.borderWidth = '2px';
    });

    // Click handler - manual capture
    this.floatingButton.addEventListener('click', () => {
      this.floatingButton.style.transform = 'scale(0.95)';
      setTimeout(() => {
        this.floatingButton.style.transform = 'scale(1)';
      }, 150);
      this.manualCapture();
    });

    // Right-click handler - debug info
    this.floatingButton.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.showDebugInfo();
    });

    document.body.appendChild(this.floatingButton);
  }

  createNotificationContainer() {
    // Container for success/error notifications
    this.notificationContainer = document.createElement('div');
    this.notificationContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10001;
      pointer-events: none;
    `;
    document.body.appendChild(this.notificationContainer);
  }

  async manualCapture() {
    this.showNotification('🔄 Capturing conversation...', 'info', 1000);
    
    try {
      // Force capture even if already cached (manual override)
      const result = await this.captureConversationWithRetry(3, true); // forceCapture = true
      if (result) {
        this.showNotification('🎯 Conversation captured successfully!', 'success', 3000);
      } else {
        this.showNotification('⚠️ No messages found to capture', 'warning', 2000);
      }
    } catch (error) {
      this.showNotification('❌ Capture failed: ' + error.message, 'error', 4000);
    }
  }

  showDebugInfo() {
    const messages = this.extractMessages();
    const info = {
      platform: this.platform,
      messagesFound: messages.length,
      url: window.location.href,
      cacheSize: this.conversationCache.size,
      lastCapture: this.lastCaptureTime || 'Never'
    };
    
    console.group('[Omega_KG] Debug Info');
    console.table(info);
    console.log('Sample messages:', messages.slice(0, 3));
    console.groupEnd();
    
    this.showNotification(`🔍 Debug: ${messages.length} messages found`, 'info', 3000);
  }

  showNotification(message, type = 'success', duration = 3000) {
    const notification = document.createElement('div');
    
    const colors = {
      success: '#019387',
      error: '#FF7C87', 
      warning: '#ff9800',
      info: '#2196F3'
    };
    
    notification.textContent = message;
    notification.style.cssText = `
      background: ${colors[type]};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      margin-bottom: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      max-width: 300px;
      word-wrap: break-word;
      animation: slideIn 0.3s ease-out;
      pointer-events: auto;
      cursor: pointer;
    `;

    // Add slide-in animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
    `;
    if (!document.head.querySelector('[data-omega-styles]')) {
      style.setAttribute('data-omega-styles', '');
      document.head.appendChild(style);
    }

    this.notificationContainer.appendChild(notification);

    // Click to dismiss
    notification.addEventListener('click', () => {
      notification.style.animation = 'slideOut 0.3s ease-in';
      setTimeout(() => notification.remove(), 300);
    });

    // Auto-remove after duration
    setTimeout(() => {
      if (notification.parentNode) {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
      }
    }, duration);
  }
}

// Initialize
const capture = new ChatCapture();

// Capture on visibility change (tab switch)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    capture.captureConversationWithRetry().catch(() => {
      // Error already logged in retry function
    });
  }
});