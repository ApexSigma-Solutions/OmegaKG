// Background service worker - sends to localhost server
// Manifest V3 service workers go inactive - this is NORMAL Chrome behavior
// The extension will wake up when messages arrive or alarms fire

const DEFAULT_SERVER_URL = "http://localhost:8765";
const STORAGE_KEYS = {
    SERVER_URL: 'omega_server_url',
    API_KEY: 'omega_api_key',
    JWT_TOKEN: 'omega_jwt_token',
    JWT_EXPIRY: 'omega_jwt_expiry',
};

/**
 * Get the configured server URL or fallback to default
 * @returns {Promise<string>} The server URL
 */
async function getServerUrl() {
    const result = await chrome.storage.local.get([STORAGE_KEYS.SERVER_URL]);
    return result[STORAGE_KEYS.SERVER_URL] || DEFAULT_SERVER_URL;
}

/**
 * Build a full endpoint URL from a path
 * @param {string} path - The endpoint path (e.g., '/capture')
 * @returns {Promise<string>} The full URL
 */
async function getEndpointUrl(path) {
    const serverUrl = await getServerUrl();
    return `${serverUrl}${path}`;
}

// Token cache (short-term cache to avoid excessive /auth/token calls)
let cachedJwtToken = null;
let cachedJwtExpiry = 0;

/**
 * Retrieve and cache JWT token from storage, refreshing if necessary
 * @async
 * @returns {Promise<string|null>} JWT token or null if not configured/available
 */
async function getValidJwtToken() {
  try {
    // Check if cached token is still valid (with 60-second buffer)
    const now = Date.now();
    if (cachedJwtToken && cachedJwtExpiry > (now + 60000)) {
      console.debug('[Omega_KG] Using cached JWT token');
      return cachedJwtToken;
    }

    // Try to load from storage first
    const storedData = await chrome.storage.local.get([
      STORAGE_KEYS.JWT_TOKEN,
      STORAGE_KEYS.JWT_EXPIRY,
    ]);

    const storedToken = storedData[STORAGE_KEYS.JWT_TOKEN];
    const storedExpiry = storedData[STORAGE_KEYS.JWT_EXPIRY];

    if (storedToken && storedExpiry && storedExpiry > (now + 60000)) {
      console.debug('[Omega_KG] Using stored JWT token from storage');
      cachedJwtToken = storedToken;
      cachedJwtExpiry = storedExpiry;
      return storedToken;
    }

    // Token expired or not available - need to refresh
    console.debug('[Omega_KG] JWT token expired or missing, refreshing...');
    return await refreshJwtToken();
  } catch (error) {
    console.error('[Omega_KG] Failed to get valid JWT token:', error);
    return null;
  }
}

/**
 * Refresh JWT token using bootstrap API key
 * @async
 * @returns {Promise<string|null>} New JWT token or null if refresh fails
 */
async function refreshJwtToken() {
  try {
    // Get bootstrap API key from storage
    const storedData = await chrome.storage.local.get(STORAGE_KEYS.API_KEY);
    const apiKey = storedData[STORAGE_KEYS.API_KEY];

    if (!apiKey) {
      console.warn('[Omega_KG] No bootstrap API key configured - cannot refresh token');
      return null;
    }

    // Call /auth/token endpoint
    const authUrl = await getEndpointUrl('/auth/token');
    const response = await fetch(authUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Token refresh failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    const token = data.access_token;
    const expiresIn = data.expires_in || 86400; // Default 24 hours
    const expiry = Date.now() + (expiresIn * 1000);

    // Cache the token
    cachedJwtToken = token;
    cachedJwtExpiry = expiry;

    // Also store in chrome.storage.local for persistence across service worker reloads
    await chrome.storage.local.set({
      [STORAGE_KEYS.JWT_TOKEN]: token,
      [STORAGE_KEYS.JWT_EXPIRY]: expiry,
    });

    console.debug('[Omega_KG] JWT token refreshed successfully');
    return token;
  } catch (error) {
    console.error('[Omega_KG] JWT token refresh failed:', error);
    return null;
  }
}

// Listen for configuration updates from options.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CONFIG_UPDATED') {
    console.debug('[Omega_KG] Configuration updated, clearing cached JWT token');
    cachedJwtToken = null;
    cachedJwtExpiry = 0;
  }
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log(
    "[Omega_KG] Service worker received message:",
    message.type,
  );

  if (message.type === "CAPTURE_CONVERSATION") {
    saveToLocalhost(message.data)
      .then((response) => {
        console.log(
          "[Omega_KG] ✅ Captured successfully:",
          response,
        );
        sendResponse({ success: true, response });
      })
      .catch((error) => {
        console.error(
          "[Omega_KG] ❌ Capture failed:",
          error,
        );
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep channel open for async response
  }

  if (message.type === "PING") {
    console.log("[Omega_KG] Service worker is alive - background.js:36");
    sendResponse({ alive: true, timestamp: new Date().toISOString() });
    return true;
  }
});

/**
 * Saves conversation data to the localhost capture server.
 * Uses JWT Bearer token authentication (exchanges bootstrap key for JWT via /auth/token)
 * @async
 * @param {Object} data - The conversation data to save
 * @returns {Promise<Object>} Promise that resolves to the JSON-decoded response from the server
 * @throws {Error} If the server request fails or returns an error status
 */
async function saveToLocalhost(data) {
  console.log(
    "[Omega_KG] Attempting to save to localhost...",
    {
      platform: data.platform,
      messageCount: data.messages?.length,
      url: data.url,
    },
  );

  try {
    // Get valid JWT token (will refresh if necessary)
    const jwtToken = await getValidJwtToken();
    
    if (!jwtToken) {
      throw new Error(
        'No JWT token available. Please configure API key in extension options.'
      );
    }

    const response = await fetch(await getEndpointUrl('/capture'), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${jwtToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log("[Omega_KG] Server response:", result);
    return result;
  } catch (error) {
    console.error(
      "[Omega_KG] ❌ Server error:",
      error.message,
    );
    throw error;
  }
}

// Periodic health check (ensures server is running)
chrome.alarms.create("health-check", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "health-check") {
    try {
      const healthUrl = await getEndpointUrl('/health');
      const response = await fetch(healthUrl);
      const data = await response.json();
      console.log(
        "[Omega_KG] Server status:",
        data.status,
      );
    } catch (error) {
      console.warn("[Omega_KG] Server offline - background.js:100");
    }
  }
});
