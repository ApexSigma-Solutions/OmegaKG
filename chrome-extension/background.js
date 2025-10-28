// Background service worker - sends to localhost server
// Manifest V3 service workers go inactive - this is NORMAL Chrome behavior
// The extension will wake up when messages arrive or alarms fire

const CAPTURE_ENDPOINT = "http://localhost:8765/capture";

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log(
    "[Omega_KG] Service worker received message: - background.js:9",
    message.type,
  );

  if (message.type === "CAPTURE_CONVERSATION") {
    saveToLocalhost(message.data)
      .then((response) => {
        console.log(
          "[Omega_KG] ✅ Captured successfully: - background.js:14",
          response,
        );
        sendResponse({ success: true, response });
      })
      .catch((error) => {
        console.error(
          "[Omega_KG] ❌ Capture failed: - background.js:18",
          error,
        );
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep channel open for async response
  }

  if (message.type === "PING") {
    console.log("[Omega_KG] Service worker is alive - background.js:26");
    sendResponse({ alive: true, timestamp: new Date().toISOString() });
    return true;
  }
});

/**
 * Saves conversation data to the localhost capture server.
 * @async
 * @param {Object} data - The conversation data to save
 * @returns {Promise<Object>} Promise that resolves to the JSON-decoded response from the server
 * @throws {Error} If the server request fails or returns an error status
 */
async function saveToLocalhost(data) {
  console.log(
    "[Omega_KG] Attempting to save to localhost... - background.js:33",
    {
      platform: data.platform,
      messageCount: data.messages?.length,
      url: data.url,
    },
  );

  try {
    const response = await fetch(CAPTURE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log("[Omega_KG] Server response: - background.js:54", result);
    return result;
  } catch (error) {
    console.error(
      "[Omega_KG] ❌ Server error: - background.js:57",
      error.message,
    );
    throw error;
  }
}

// Periodic health check (ensures server is running)
chrome.alarms.create("health-check", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "health-check") {
    fetch("http://localhost:8765/health")
      .then((r) => r.json())
      .then((data) =>
        console.log(
          "[Omega_KG] Server status: - background.js:69",
          data.status,
        ),
      )
      .catch(() =>
        console.warn("[Omega_KG] Server offline - background.js:70"),
      );
  }
});
