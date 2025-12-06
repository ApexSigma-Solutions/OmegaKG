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
    const url = window.location.href;

    if (hostname.includes("claude.ai")) return "Claude.ai";
    if (hostname.includes("openai.com") || hostname.includes("chatgpt.com"))
      return "ChatGPT";
    if (hostname.includes("aistudio.google.com")) return "AI_Studio";
    if (hostname.includes("nano-gpt.com")) return "Nano_GPT";
    if (hostname.includes("gemini.google.com")) return "Gemini";
    if (hostname.includes("perplexity.ai")) return "Perplexity";
    if (hostname.includes("github.com") && url.includes("copilot"))
      return "GitHub_Copilot";
    if (hostname.includes("qwen.ai") || hostname.includes("tongyi.aliyun.com"))
      return "Qwen";
    if (hostname.includes("z.ai")) return "Z.ai";
    if (hostname.includes("kimi.com") || hostname.includes("kimi.moonshot"))
      return "Kimi";
    if (hostname.includes("deepseek.com")) return "DeepSeek";
    if (hostname.includes("mistral.ai")) return "Mistral";

    console.log(
      `[Omega_KG] Unknown platform  hostname: ${hostname}`,
    );
    return "unknown";
  }

  extractMessages() {
    // Platform-specific selectors (updated for current DOM structure - Oct 2025)
    const selectors = {
      "Claude.ai": {
        // Claude.ai Oct 2025 - uses class-based selectors
        messages: ".font-user-message, .font-claude-response",
        isUser: (el) =>
          el.classList.contains("font-user-message") ||
          el.closest('[data-testid*="user"]') !== null,
        getText: (el) => {
          // Try multiple selectors for message content
          const content =
            el.querySelector('[class*="font-claude-message"]') ||
            el.querySelector('div[class*="whitespace-pre-wrap"]') ||
            el;
          return content.textContent;
        },
      },
      ChatGPT: {
        messages: "[data-message-author-role]",
        isUser: (el) => el.getAttribute("data-message-author-role") === "user",
        getText: (el) => el.textContent,
      },
      AI_Studio: {
        // Google AI Studio - uses generic message containers
        messages: '[class*="message"], [class*="response"], [class*="prompt"]',
        isUser: (el) => {
          const text = el.textContent.toLowerCase();
          // Heuristic: look for "user:" or "you:" prefixes
          return text.includes("user:") || text.includes("you:") ||
                 el.closest('[class*="user"]') !== null ||
                 el.closest('[data-role="user"]') !== null;
        },
        getText: (el) => el.textContent,
      },
      Nano_GPT: {
        // Nano-GPT uses Tailwind classes for chat bubbles
        messages: 'div.whitespace-pre-wrap, [class*="message"], [class*="chat"]',
        isUser: (el) => {
          // Alternate messages: odd indices are user, even are assistant
          // Or look for user-specific classes
          return el.closest('[class*="user"]') !== null ||
                 el.closest('[data-role="user"]') !== null;
        },
        getText: (el) => el.textContent,
      },
      Gemini: {
        // Gemini Oct 2025 - uses custom web components
        messages:
          "message-content.model-response-text, .conversation-container, user-query",
        isUser: (el) => {
          return (
            el.tagName.toLowerCase() === "user-query" ||
            el.classList.contains("user-query") ||
            el.closest("user-query") !== null ||
            el.getAttribute("data-message-author-role") === "user"
          );
        },
        getText: (el) => {
          // Try to get clean text content
          const content =
            el.querySelector(".markdown") ||
            el.querySelector('[class*="message-content"]') ||
            el;
          return content.textContent;
        },
      },
      Perplexity: {
        messages: '[class*="Markdown"], .prose',
        isUser: (el) =>
          el.closest('[class*="UserMessage"]') !== null ||
          el.closest('[class*="Query"]') !== null,
        getText: (el) => el.textContent,
      },
      Qwen: {
        // Qwen/Tongyi uses similar patterns to other chat UIs
        messages: '[class*="message"], [class*="chat-message"]',
        isUser: (el) =>
          el.closest('[class*="user"]') !== null ||
          el.getAttribute("data-role") === "user",
        getText: (el) => el.textContent,
      },
      "Z.ai": {
        // Z.ai - will use fallback until we get actual selectors
        messages: '[class*="message"], [role="article"]',
        isUser: (el) => el.closest('[class*="user"]') !== null,
        getText: (el) => el.textContent,
      },
      Kimi: {
        // Kimi (Moonshot AI) - will use fallback until we get actual selectors
        messages: '[class*="message"], [class*="chat"]',
        isUser: (el) => el.closest('[class*="user"]') !== null,
        getText: (el) => el.textContent,
      },
      DeepSeek: {
        // DeepSeek - will use fallback until we get actual selectors
        messages: '[class*="message"], [class*="conversation"]',
        isUser: (el) =>
          el.closest('[class*="user"]') !== null ||
          el.getAttribute("data-role") === "user",
        getText: (el) => el.textContent,
      },
      Mistral: {
        // Mistral AI - will use fallback until we get actual selectors
        messages: '[class*="message"], [class*="chat"]',
        isUser: (el) => el.closest('[class*="user"]') !== null,
        getText: (el) => el.textContent,
      },
    };

    const config = selectors[this.platform];
    if (!config) {
      console.warn(
        `[Omega_KG] No selector config for platform: ${this.platform}`,
      );
      return [];
    }

    // FALLBACK: If no messages found with specific selectors, try generic approach
    let messageElements = document.querySelectorAll(config.messages);

    if (messageElements.length === 0) {
      console.warn(
        `[Omega_KG] No messages found with selectors, trying fallback...`,
      );
      // Try to find any text content that looks like messages
      messageElements = this.fallbackExtraction();
    }

    const messages = [];
    console.log(
      `[Omega_KG] Found ${messageElements.length} message elements on ${this.platform}`,
    );

    messageElements.forEach((element, index) => {
      try {
        const isUser = config.isUser(element);
        const content = config.getText(element);

        if (!content || content.trim().length < 10) {
          return; // Skip empty or very short messages
        }

        messages.push({
          role: isUser ? "user" : "assistant",
          content: this.cleanText(content),
          timestamp: new Date().toISOString(),
          index: index,
        });
      } catch (err) {
        console.warn(
          "[Omega_KG] Error extracting message " + index + ":",
          err,
        );
      }
    });

    console.log(
      `[Omega_KG] Extracted ${messages.length} messages from ${messageElements.length} elements`,
    );
    return messages;
  }

  fallbackExtraction() {
    // Generic fallback: look for common patterns across AI chat UIs
    const candidates = [];

    // Try common wrapper patterns
    const wrappers = document.querySelectorAll(
      '[class*="message"], [class*="chat"], [class*="conversation"], ' +
        '[data-testid*="message"], [data-testid*="chat"], ' +
        '[role="article"], [role="region"]',
    );

    wrappers.forEach((wrapper) => {
      // Look for text content > 20 characters
      const textContent = wrapper.textContent?.trim();
      if (textContent && textContent.length > 20) {
        candidates.push(wrapper);
      }
    });

    console.log(
      `[Omega_KG] Fallback found ${candidates.length} potential message containers`,
    );
    return candidates.slice(0, 50); // Limit to prevent overwhelming
  }

  cleanText(text) {
    // Remove UI artifacts, normalize whitespace
    return text
      .replace(/\s+/g, " ")
      .replace(/Copy code/g, "")
      .replace(/\d+\/\d+/g, "") // Remove message counters
      .trim();
  }

  extractTimestamp(element, selector) {
    if (!selector) return new Date().toISOString();

    const timeEl = element.querySelector(selector);
    if (timeEl) {
      return timeEl.getAttribute("datetime") || new Date().toISOString();
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
      }, 2000); // 2 second delay after last change
    });

    this.observer.observe(targetNode, config);
  }

  async captureConversation() {
    const messages = this.extractMessages();

    console.log(`[Omega_KG] Attempting capture:`, {
      platform: this.platform,
      messageCount: messages.length,
      url: window.location.href,
    });

    if (messages.length === 0) {
      const msg = "No messages extracted";
      console.warn("[Omega_KG] " + msg);
      this.showNotification(msg, "info");
      return false;
    }

    // Generate conversation hash (to detect duplicates)
    const conversationHash = this.hashConversation(messages);

    // Skip if already captured in this session
    if (this.conversationCache.has(conversationHash)) {
      const msg = "Conversation already captured";
      console.log("[Omega_KG] " + msg);
      this.showNotification(msg, "info");
      return false;
    }

    // Prepare data payload matching capture_server.py expectations
    const data = {
      platform: this.platform,
      url: window.location.href,
      title: document.title || `${this.platform} Conversation`,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
      })),
      captured_at: new Date().toISOString(),
      test: false,
    };

    // Send to background script for persistence
    try {
      const response = await chrome.runtime.sendMessage({
        type: "CAPTURE_CONVERSATION",
        data: data,
      });

      if (response?.success) {
        this.conversationCache.set(conversationHash, true);
        console.log(
          `[Omega_KG] ✅ Captured ${messages.length} messages from ${this.platform}`,
        );
        this.showNotification("Conversation captured!", "success");
        return true;
      } else {
        const errorMsg = response?.error || "Capture failed";
        console.error("[Omega_KG] ❌ Capture failed:", errorMsg);
        this.showNotification("Capture failed - check server", "error");
        return false;
      }
    } catch (error) {
      console.error(
        "[Omega_KG] ❌ Error sending to background:",
        error,
      );
      this.showNotification("Extension error - check console", "error");
      return false;
    }
  }

  hashConversation(messages) {
    // Simple hash: last user message + length
    const lastUser = messages.filter((m) => m.role === "user").pop();
    return `${this.platform}-${messages.length}-${lastUser?.content.substring(0, 50)}`;
  }

  showNotification(message, type = "info") {
    // Remove existing notification
    const existing = document.getElementById("omega-kg-notification");
    if (existing) existing.remove();

    // Create notification element
    const notification = document.createElement("div");
    notification.id = "omega-kg-notification";
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 8px;
      background: ${type === "success" ? "#019387" : type === "error" ? "#FF7C87" : "#3799ad"};
      color: white;
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 999999;
      animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = `Ω_KG: ${message}`;

    // Add animation
    const style = document.createElement("style");
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
    `;
    document.head.appendChild(style);
    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => notification.remove(), 3000);
  }

  addCaptureButton() {
    // Add floating capture button
    const button = document.createElement("button");
    button.id = "omega-kg-capture-btn";
    button.innerHTML = "Ω";
    button.title = "Capture conversation to Omega_KG (Right-click for debug)";
    button.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 50px;
      height: 50px;
      border-radius: 50%;
      background: linear-gradient(135deg, #019387 0%, #017a70 100%);
      color: white;
      border: none;
      border: 2px solid #FF7C87;
      font-size: 24px;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(1,147,135,0.4);
      z-index: 999998;
      transition: transform 0.2s, box-shadow 0.2s;
    `;

    button.addEventListener("mouseover", () => {
      button.style.transform = "scale(1.1)";
      button.style.boxShadow = "0 6px 16px rgba(255,124,135,0.6)";
      button.style.borderColor = '#FF7C87';
      button.style.borderWidth = '3px';
    });

    button.addEventListener("mouseout", () => {
      button.style.transform = "scale(1)";
      button.style.boxShadow = "0 4px 12px rgba(1,147,135,0.4)";
      button.style.borderColor = '#FF7C87';
      button.style.borderWidth = '2px';
    });

    button.addEventListener("click", () => {
      button.style.transform = "scale(0.95)";
      setTimeout(() => (button.style.transform = "scale(1)"), 100);
      this.captureConversation();
    });

    // Right-click for debug mode
    button.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.debugDOM();
    });

    document.body.appendChild(button);
  }

  debugDOM() {
    // Debug helper to find message selectors
    console.log("=== Omega_KG Debug Mode === - content.js:408");
    console.log("Platform: - content.js:409", this.platform);
    console.log("URL: - content.js:410", window.location.href);

    // Find all elements with "message" in class or data attributes
    const messageElements = document.querySelectorAll(
      '[class*="message" i], [class*="chat" i], [class*="response" i], ' +
        '[data-testid*="message" i], [data-test-id*="message" i]',
    );
    console.log(
      `Found ${messageElements.length} elements with messagerelated attributes`,
    );

    // Group by selector patterns
    const patterns = new Map();
    messageElements.forEach((el) => {
      const classes = Array.from(el.classList).join(" ");
      const testId =
        el.getAttribute("data-testid") || el.getAttribute("data-test-id") || "";
      const key = `${el.tagName}.${classes} [${testId}]`;

      if (!patterns.has(key)) {
        patterns.set(key, { count: 0, example: el });
      }
      patterns.get(key).count++;
    });

    console.log("\n=== Selector Patterns Found === - content.js:435");
    Array.from(patterns.entries())
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 10)
      .forEach(([pattern, data]) => {
        console.log(`${data.count}x: ${pattern} - content.js:440`);
        console.log(
          "Example text:",
          data.example.textContent.substring(0, 100),
        );
      });

    console.log(
      "\n💡 Copy these selectors and update  extractMessages()",
    );
    console.log("=== End Debug === - content.js:450");

    this.showNotification("Debug info logged to console (F12)", "info");
  }
}

// Initialize
const capture = new ChatCapture();

// Add capture button
if (capture.platform !== "unknown") {
  capture.addCaptureButton();
  console.log(
    `[Omega_KG] Initialized for ${capture.platform}`,
  );
} else {
  console.warn(
    "[Omega_KG] Unknown platform, capture disabled",
  );
}

// Start observing DOM changes
capture.startObserving();

// Capture on page load (delayed to allow content to render)
window.addEventListener("load", () => {
  console.log(
    "[Omega_KG] Page loaded, scheduling initial capture",
  );
  setTimeout(() => capture.captureConversation(), 3000);
});

// Capture on visibility change (tab switch) - user is leaving the tab
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    console.log(
      "[Omega_KG] Tab hidden, capturing conversation",
    );
    capture.captureConversation();
  }
});

// Capture before page unload
window.addEventListener("beforeunload", () => {
  console.log(
    "[Omega_KG] Page unloading, capturing conversation",
  );
  capture.captureConversation();
});

// Listen for messages from popup script (TRIGGER_CAPTURE)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Validate message type
  if (message.type !== 'TRIGGER_CAPTURE') {
    return false; // Not handled
  }

  console.log('[Omega_KG] Received TRIGGER_CAPTURE message from popup');

  // Handle async capture operation
  (async () => {
    try {
      // Trigger capture conversation and get result
      const captureSuccess = await capture.captureConversation();
      
      if (captureSuccess) {
        // Send success response
        sendResponse({ success: true });
      } else {
        // captureConversation returned false, indicating failure (no messages, duplicate, or server error)
        console.error('[Omega_KG] Capture failed (no messages, duplicate, or server error)');
        sendResponse({
          success: false,
          error: 'Capture failed: no messages extracted, duplicate conversation, or server error'
        });
      }
    } catch (error) {
      console.error('[Omega_KG] Error handling TRIGGER_CAPTURE:', error);
      sendResponse({
        success: false,
        error: error.message || 'Unknown error during capture'
      });
    }
  })();

  // Return true to indicate we will send a response asynchronously
  return true;
});
