// Background service worker - sends to localhost server

const CAPTURE_ENDPOINT = 'http://localhost:8765/capture';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CAPTURE_CONVERSATION') {
    saveToLocalhost(message.data)
      .then(response => {
        console.log('[Omega_KG] Captured: - background.js:9', response);
        sendResponse({ success: true });
      })
      .catch(error => {
        console.error('[Omega_KG] Capture failed: - background.js:13', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;  // Keep channel open for async response
  }
});

async function saveToLocalhost(data) {
  try {
    const response = await fetch(CAPTURE_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    // Server might not be running - fail silently
    console.warn('[Omega_KG] Server unavailable: - background.js:38', error.message);
    throw error;
  }
}

// Periodic health check (ensures server is running)
chrome.alarms.create('health-check', { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'health-check') {
    fetch('http://localhost:8765/health')
      .then(r => r.json())
      .then(data => console.log('[Omega_KG] Server status: - background.js:50', data.status))
      .catch(() => console.warn('[Omega_KG] Server offline - background.js:51'));
  }
});