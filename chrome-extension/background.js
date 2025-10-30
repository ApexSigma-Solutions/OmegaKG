// Background service worker - sends to localhost server
// Handles message passing with retry logic and context invalidation recovery

const CAPTURE_ENDPOINT = 'http://localhost:8765/capture';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // ms

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CAPTURE_CONVERSATION') {
    saveToLocalhostWithRetry(message.data, 0)
      .then(response => {
        console.log('[Omega_KG] ✅ Captured: - background.js:12', response);
        sendResponse({ success: true, data: response });
      })
      .catch(error => {
        console.error('[Omega_KG] ❌ Capture failed after retries: - background.js:16', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;  // Keep channel open for async response
  }
});

async function saveToLocalhostWithRetry(data, attempt = 0) {
  try {
    const response = await fetch(CAPTURE_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      timeout: 5000
    });
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    // Retry logic for transient failures
    if (attempt < MAX_RETRIES) {
      console.warn(`[Omega_KG] Retry ${attempt + 1}/${MAX_RETRIES} - background.js:43`, error.message);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)));
      return saveToLocalhostWithRetry(data, attempt + 1);
    }
    
    // Server might not be running - fail after all retries
    console.warn('[Omega_KG] Server unavailable after retries - background.js:49', error.message);
    throw error;
  }
}

// Periodic health check (ensures server is running)
chrome.alarms.create('health-check', { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'health-check') {
    fetch('http://localhost:8765/health')
      .then(r => r.json())
      .then(data => console.log('[Omega_KG] ✓ Server online - background.js:61', data.status))
      .catch(() => console.warn('[Omega_KG] ✗ Server offline - background.js:62'));
  }
});