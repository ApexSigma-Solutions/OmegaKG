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
      `[Omega_KG] Unknown platform  hostname: ${hostname} - content.js:26`,
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
      GitHub_Copilot: {
        // GitHub Copilot Tasks - Oct 2025
        // Messages are in TaskChat with UserInitialMessage and response containers
        messages:
          '.UserInitialMessage-module__container--j2mCV, [class*="TaskChat-module"][class*="message"], .markdown-body.MarkdownRenderer-module__container--dNKcF',
        isUser: (el) => {
          // User messages have UserInitialMessage class or started task message
          return (
            el.classList.contains("UserInitialMessage-module__container--j2mCV") ||
            el.querySelector(".UserInitialMessage-module__startedTaskMessage--Llm_V") !== null ||
            el.closest('[class*="UserInitialMessage"]') !== null
          );
        },
        getText: (el) => {
          // Try to extract from markdown content first
          const markdown = el.querySelector(".markdown-body.MarkdownRenderer-module__container--dNKcF");
          if (markdown) return markdown.textContent;
          
          // Otherwise get from the message container
          const content = el.querySelector('[class*="message"]') || el;
          return content.textContent;
        },
      },
    };

    const config = selectors[this.platform];
    if (!config) {
      console.warn(
        `[Omega_KG] No selector config for platform: ${this.platform} - content.js:110`,
      );
      return [];
    }

    // FALLBACK: If no messages found with specific selectors, try generic approach
    let messageElements = document.querySelectorAll(config.messages);

    if (messageElements.length === 0) {
      console.warn(
        `[Omega_KG] No messages found with selectors, trying fallback... - content.js:118`,
      );
      // Try to find any text content that looks like messages
      messageElements = this.fallbackExtraction();
    }

    const messages = [];
    console.log(
      `[Omega_KG] Found ${messageElements.length} message elements on ${this.platform} - content.js:124`,
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
          "[Omega_KG] Error extracting message " + index + ": - content.js:142",
          err,
        );
      }
    });

    console.log(
      `[Omega_KG] Extracted ${messages.length} messages from ${messageElements.length} elements - content.js:146`,
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
      `[Omega_KG] Fallback found ${candidates.length} potential message containers - content.js:169`,
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

    console.log(`[Omega_KG] Attempting capture: - content.js:211`, {
      platform: this.platform,
      messageCount: messages.length,
      url: window.location.href,
    });

    if (messages.length === 0) {
      console.warn(
        "[Omega_KG] No messages extracted, skipping capture - content.js:218",
      );
      return;
    }

    // Generate conversation hash (to detect duplicates)
    const conversationHash = this.hashConversation(messages);

    // Skip if already captured in this session
    if (this.conversationCache.has(conversationHash)) {
      console.log(
        "[Omega_KG] Conversation already captured (hash collision), skipping - content.js:227",
      );
      return;
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
          `[Omega_KG] ✅ Captured ${messages.length} messages from ${this.platform} - content.js:254`,
        );
        this.showNotification("Conversation captured!", "success");
      } else {
        console.error(
          "[Omega_KG] ❌ Capture failed: - content.js:257",
          response?.error,
        );
        this.showNotification("Capture failed - check server", "error");
      }
    } catch (error) {
      console.error(
        "[Omega_KG] ❌ Error sending to background: - content.js:261",
        error,
      );
      this.showNotification("Extension error - check console", "error");
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
      background: ${type === "success" ? "#10b981" : type === "error" ? "#ef4444" : "#3b82f6"};
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
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      font-size: 24px;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      z-index: 999998;
      transition: transform 0.2s, box-shadow 0.2s;
    `;

    button.addEventListener("mouseover", () => {
      button.style.transform = "scale(1.1)";
      button.style.boxShadow = "0 6px 16px rgba(0,0,0,0.3)";
    });

    button.addEventListener("mouseout", () => {
      button.style.transform = "scale(1)";
      button.style.boxShadow = "0 4px 12px rgba(0,0,0,0.2)";
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
    console.log("=== Omega_KG Debug Mode === - content.js:363");
    console.log("Platform: - content.js:364", this.platform);
    console.log("URL: - content.js:365", window.location.href);

    // Find all elements with "message" in class or data attributes
    const messageElements = document.querySelectorAll(
      '[class*="message" i], [class*="chat" i], [class*="response" i], ' +
        '[data-testid*="message" i], [data-test-id*="message" i]',
    );
    console.log(
      `Found ${messageElements.length} elements with messagerelated attributes - content.js:372`,
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

    console.log("\n=== Selector Patterns Found === - content.js:387");
    Array.from(patterns.entries())
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 10)
      .forEach(([pattern, data]) => {
        console.log(`${data.count}x: ${pattern} - content.js:392`);
        console.log(
          "Example text: - content.js:393",
          data.example.textContent.substring(0, 100),
        );
      });

    console.log(
      "\n💡 Copy these selectors and update  extractMessages() - content.js:396",
    );
    console.log("=== End Debug === - content.js:397");

    this.showNotification("Debug info logged to console (F12)", "info");
  }
}

// Initialize
const capture = new ChatCapture();

// Add capture button
if (capture.platform !== "unknown") {
  capture.addCaptureButton();
  console.log(
    `[Omega_KG] Initialized for ${capture.platform} - content.js:409`,
  );
} else {
  console.warn(
    "[Omega_KG] Unknown platform, capture disabled - content.js:411",
  );
}

// Start observing DOM changes
capture.startObserving();

// Capture on page load (delayed to allow content to render)
window.addEventListener("load", () => {
  console.log(
    "[Omega_KG] Page loaded, scheduling initial capture - content.js:419",
  );
  setTimeout(() => capture.captureConversation(), 3000);
});

// Capture on visibility change (tab switch) - user is leaving the tab
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    console.log(
      "[Omega_KG] Tab hidden, capturing conversation - content.js:426",
    );
    capture.captureConversation();
  }
});

// Capture before page unload
window.addEventListener("beforeunload", () => {
  console.log(
    "[Omega_KG] Page unloading, capturing conversation - content.js:433",
  );
  capture.captureConversation();
});
