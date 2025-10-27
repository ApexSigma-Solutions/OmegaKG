// Universal AI Chat Capture
// Detects which platform and extracts conversations

class ChatCapture {
  constructor() {
    this.platform = this.detectPlatform();
    this.observer = null;
    this.conversationCache = new Map();
  }

  detectPlatform() {
    const hostname = window.location.hostname;
    
    if (hostname.includes('claude.ai')) return 'claude';
    if (hostname.includes('openai.com')) return 'chatgpt';
    if (hostname.includes('gemini.google.com')) return 'gemini';
    if (hostname.includes('perplexity.ai')) return 'perplexity';
    
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
        timestamp: null // ChatGPT doesn't expose timestamps in DOM
      },
      gemini: {
        container: '.conversation-container',
        userMsg: '.user-message',
        assistantMsg: '.model-message',
        timestamp: null
      },
      perplexity: {
        container: '[class*="thread"]',
        userMsg: '[class*="question"]',
        assistantMsg: '[class*="answer"]',
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
        this.captureConversation();
      }, 2000);  // 2 second delay after last change
    });

    this.observer.observe(targetNode, config);
  }

  async captureConversation() {
    const messages = this.extractMessages();
    if (messages.length === 0) return;

    // Generate conversation hash (to detect duplicates)
    const conversationHash = this.hashConversation(messages);
    
    // Skip if already captured
    if (this.conversationCache.has(conversationHash)) return;
    this.conversationCache.set(conversationHash, true);

    // Send to background script for persistence
    chrome.runtime.sendMessage({
      type: 'CAPTURE_CONVERSATION',
      data: {
        messages,
        platform: this.platform,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        conversationHash
      }
    });

    console.log(`[Omega_KG] Captured ${messages.length} messages from ${this.platform} - content.js:146`);
  }

  hashConversation(messages) {
    // Simple hash: last user message + length
    const lastUser = messages.filter(m => m.role === 'user').pop();
    return `${this.platform}-${messages.length}-${lastUser?.content.substring(0, 50)}`;
  }
}

// Initialize
const capture = new ChatCapture();
capture.startObserving();

// Capture on page load
window.addEventListener('load', () => {
  setTimeout(() => capture.captureConversation(), 3000);
});

// Capture on visibility change (tab switch)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    capture.captureConversation();
  }
});