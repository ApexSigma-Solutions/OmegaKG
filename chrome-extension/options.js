/**
 * Options page script for Omega_KG Chrome extension
 * Handles secure storage and retrieval of bootstrap API key
 */

const STORAGE_KEYS = {
    API_KEY: 'omega_api_key',
    JWT_TOKEN: 'omega_jwt_token',
    JWT_EXPIRY: 'omega_jwt_expiry',
};

// DOM Elements
const form = document.getElementById('configForm');
const apiKeyInput = document.getElementById('apiKey');
const serverUrlInput = document.getElementById('serverUrl');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');
const statusMessage = document.getElementById('statusMessage');
const apiKeyStatus = document.getElementById('apiKeyStatus');
const serverUrlStatus = document.getElementById('serverUrlStatus');

/**
 * Load stored API key and server URL into the options form and update field statuses.
 *
 * If an API key exists in storage, populates `apiKeyInput`, marks the API key field as saved,
 * and updates the internal `savedApiKey`. Sets `serverUrlInput` to the stored server URL or
 * a default (`http://localhost:8765`), updates `savedServerUrl`, and marks the server URL
 * field as loaded when present. On failure logs the error and shows an error status.
 */
async function initializeForm() {
    try {
        console.debug('[Omega_KG] Loading stored configuration...');
        const data = await chrome.storage.local.get([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
        ]);

        if (data[STORAGE_KEYS.API_KEY]) {
            apiKeyInput.value = data[STORAGE_KEYS.API_KEY];
            updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
            savedApiKey = data[STORAGE_KEYS.API_KEY];
        }

        // Get current server URL from storage or use default
        const currentServerUrl = data['omega_server_url'] || 'http://localhost:8765';
        serverUrlInput.value = currentServerUrl;
        savedServerUrl = currentServerUrl;
        if (data['omega_server_url']) {
            updateFieldStatus(serverUrlStatus, 'saved', 'Server URL loaded ✓');
        }

        console.debug('[Omega_KG] Configuration loaded');
    } catch (error) {
        console.error('[Omega_KG] Failed to load configuration:', error);
        showStatus('error', `Failed to load configuration: ${error.message}`);
    }
}

/**
 * Updates a field status indicator element's appearance and text.
 * @param {HTMLElement} element - The status indicator element to update.
 * @param {'saved'|'unsaved'|'error'} status - Status type that sets the element's CSS class.
 * @param {string} message - Text to display inside the status element.
 */
function updateFieldStatus(element, status, message) {
    element.className = `field-status ${status}`;
    element.textContent = message;
}

/**
 * Show a user-facing status message of the given type.
 *
 * The `type` determines the visual style and behavior: 'success' auto-hides after 3 seconds,
 * 'error' and 'info' remain visible until replaced. Logs the message for debugging.
 * @param {('success'|'error'|'info')} type - Visual/message category.
 * @param {string} message - Text to display to the user.
 */
function showStatus(type, message) {
    statusMessage.className = `status-message ${type}`;
    statusMessage.textContent = message;
    console.debug(`[Omega_KG] Status (${type}): ${message}`);

    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusMessage.className = 'status-message';
        }, 3000);
    }
}

/**
 * Determines whether an API key meets the minimum length requirement.
 * @param {string} apiKey - The API key to check (will be trimmed before measuring).
 * @returns {boolean} `true` if `apiKey` trimmed has length of at least 10, `false` otherwise.
 */
function validateApiKey(apiKey) {
    return apiKey && apiKey.trim().length >= 10;
}

/**
 * Determine whether a string is a valid absolute URL.
 * @param {string} url - The string to validate as a URL.
 * @returns {boolean} `true` if the string can be parsed as a URL, `false` otherwise.
 */
function validateServerUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

/**
 * Verify the API key by requesting an access token from the server.
 *
 * @param {string} apiKey - API key sent in the `X-API-Key` header.
 * @param {string} serverUrl - Server base URL; the function POSTs to the `/auth/token` endpoint on this host.
 * @returns {Promise<boolean>} `true` if the server returned an access token.
 * @throws {Error} If the network request fails or the server responds with a non-OK status or without an `access_token`; the error message includes the HTTP status and response body when available.
 */
async function testServerConnection(apiKey, serverUrl) {
    try {
        console.debug('[Omega_KG] Testing server connection...');
        const tokenUrl = new URL('/auth/token', serverUrl).toString();

        const response = await fetch(tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey,
            },
        });

        if (response.ok) {
            const data = await response.json();
            if (data.access_token) {
                console.debug('[Omega_KG] Connection test passed, token received');
                // Store JWT token for later use
                await storeJwtToken(data.access_token, data.expires_in || 86400);
                return true;
            }
        }

        const errorText = await response.text();
        throw new Error(`Server returned ${response.status}: ${errorText}`);
    } catch (error) {
        console.error('[Omega_KG] Connection test failed:', error);
        throw error;
    }
}

/**
 * Save a JWT and its computed expiry timestamp to chrome.storage.local.
 *
 * The expiry timestamp is calculated as the current time plus `expiresIn` seconds.
 * @param {string} token - The JWT to store.
 * @param {number} expiresIn - Lifetime of the token in seconds used to compute the expiry timestamp.
 */
async function storeJwtToken(token, expiresIn) {
    const expiryTime = Date.now() + (expiresIn * 1000);
    await chrome.storage.local.set({
        [STORAGE_KEYS.JWT_TOKEN]: token,
        [STORAGE_KEYS.JWT_EXPIRY]: expiryTime,
    });
    console.debug('[Omega_KG] JWT token stored');
}

/**
 * Validate inputs, verify the server connection, and persist the API key and server URL to chrome.storage.local.
 *
 * On success updates field status indicators, updates in-memory saved values, notifies the background script of the new configuration, and shows a success message.
 * On failure marks the API key field as errored and shows an error message.
 */
async function saveConfiguration() {
    const apiKey = apiKeyInput.value.trim();
    const serverUrl = serverUrlInput.value.trim();

    // Validate inputs
    if (!validateApiKey(apiKey)) {
        updateFieldStatus(apiKeyStatus, 'error', 'API key too short (min 10 chars)');
        showStatus('error', 'Please enter a valid API key');
        return;
    }

    if (!validateServerUrl(serverUrl)) {
        updateFieldStatus(serverUrlStatus, 'error', 'Invalid URL format');
        showStatus('error', 'Please enter a valid server URL');
        return;
    }

    // Disable save button during test
    saveBtn.disabled = true;
    showStatus('info', 'Testing server connection...');

    try {
        // Test connection to server
        await testServerConnection(apiKey, serverUrl);

        // Save API key to chrome.storage.local
        await chrome.storage.local.set({
            [STORAGE_KEYS.API_KEY]: apiKey,
            'omega_server_url': serverUrl,
        });

        // Update saved values for synchronous comparison
        savedApiKey = apiKey;
        savedServerUrl = serverUrl;

        console.debug('[Omega_KG] Configuration saved successfully');
        updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
        updateFieldStatus(serverUrlStatus, 'saved', 'Server URL saved ✓');
        showStatus('success', '✓ Configuration saved and verified!');

        // Notify background script of new configuration
        try {
            await chrome.runtime.sendMessage({
                type: 'CONFIG_UPDATED',
                config: { apiKey, serverUrl },
            });
            console.debug('[Omega_KG] Background script notified');
        } catch (err) {
            console.debug('[Omega_KG] Could not notify background (may be inactive)');
        }
    } catch (error) {
        console.error('[Omega_KG] Save failed:', error);
        updateFieldStatus(apiKeyStatus, 'error', 'Connection failed');
        showStatus('error', `Failed: ${error.message}`);
    } finally {
        saveBtn.disabled = false;
    }
}

/**
 * Prompt for confirmation and remove saved extension configuration, then reset the options UI.
 *
 * If the user confirms, removes stored API key, server URL, JWT token, and expiry from chrome.storage,
 * clears the API key and server URL inputs (resetting server URL to the default), resets per-field status
 * indicators and cached saved values, and displays a status message. On error, logs and displays an error message.
 */
async function clearConfiguration() {
    if (!confirm('Are you sure you want to clear all configuration?')) {
        return;
    }

    try {
        await chrome.storage.local.remove([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
            STORAGE_KEYS.JWT_TOKEN,
            STORAGE_KEYS.JWT_EXPIRY,
        ]);

        apiKeyInput.value = '';
        serverUrlInput.value = 'http://localhost:8765';
        savedApiKey = '';
        savedServerUrl = 'http://localhost:8765';
        apiKeyStatus.className = 'field-status';
        apiKeyStatus.textContent = '';
        serverUrlStatus.className = 'field-status';
        serverUrlStatus.textContent = '';

        showStatus('info', '✓ Configuration cleared');
        console.debug('[Omega_KG] Configuration cleared');
    } catch (error) {
        console.error('[Omega_KG] Clear failed:', error);
        showStatus('error', `Failed to clear: ${error.message}`);
    }
}

// Saved values for synchronous comparison (avoid race conditions)
let savedApiKey = '';
let savedServerUrl = 'http://localhost:8765';

/**
 * Update per-field status indicators to reflect whether form inputs differ from the saved configuration.
 *
 * Compares the current API key and server URL inputs to the stored saved values and sets each field's
 * status to 'unsaved' when different or 'saved' when identical. This includes detecting when a saved
 * value has been cleared in the input.
 */
function markUnsaved() {
    // Get current input values
    const currentApiKey = apiKeyInput.value.trim();
    const currentServerUrl = serverUrlInput.value.trim();

    // Strict equality comparison for API key (detects both changes and clearing)
    if (currentApiKey !== savedApiKey) {
        updateFieldStatus(apiKeyStatus, 'unsaved', 'Changes not saved');
    } else {
        // Reset to saved state if values match
        updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
    }

    // Strict equality comparison for server URL
    if (currentServerUrl !== savedServerUrl) {
        updateFieldStatus(serverUrlStatus, 'unsaved', 'Changes not saved');
    } else {
        // Reset to saved state if values match
        updateFieldStatus(serverUrlStatus, 'saved', 'Server URL saved ✓');
    }
}

// Event listeners
form.addEventListener('submit', (e) => {
    e.preventDefault();
    saveConfiguration();
});

clearBtn.addEventListener('click', clearConfiguration);

apiKeyInput.addEventListener('change', markUnsaved);
serverUrlInput.addEventListener('change', markUnsaved);

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeForm);

console.debug('[Omega_KG] Options page loaded');