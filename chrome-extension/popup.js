/**
 * Popup script for Omega_KG Chrome extension
 * Handles capture button interaction and debug mode toggle
 */

const STORAGE_KEYS = {
    API_KEY: 'omega_api_key',
    LAST_CAPTURE: 'omega_last_capture',
};

// DOM Elements
const statusDiv = document.getElementById('status');
const captureBtn = document.getElementById('captureBtn');
const logoHeader = document.getElementById('logoHeader');
const debugPanel = document.getElementById('debugPanel');
const configLink = document.getElementById('configLink');

let debugMode = false;

/**
 * Update status message
 * @param {string} message - Status message
 * @param {string} type - Message type ('success', 'error', 'info')
 */
function updateStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
}

/**
 * Load and display debug information
 */
async function loadDebugInfo() {
    try {
        const data = await chrome.storage.local.get([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
            STORAGE_KEYS.LAST_CAPTURE,
        ]);

        const apiKey = data[STORAGE_KEYS.API_KEY];
        const serverUrl = data['omega_server_url'] || 'http://localhost:8765';
        const lastCapture = data[STORAGE_KEYS.LAST_CAPTURE] || 'Never';

        // Update debug panel
        document.getElementById('debugApiKey').textContent = apiKey ? '✓ Configured' : '✗ Not configured';
        document.getElementById('debugServer').textContent = serverUrl;
        document.getElementById('debugLastCapture').textContent = lastCapture;

        // Test server health
        try {
            const healthUrl = new URL('/health', serverUrl).toString();
            const response = await fetch(healthUrl, { method: 'GET' });
            if (response.ok) {
                document.getElementById('debugServerStatus').textContent = '✓ Online';
            } else {
                document.getElementById('debugServerStatus').textContent = '✗ Error';
            }
        } catch {
            document.getElementById('debugServerStatus').textContent = '✗ Offline';
        }
    } catch (error) {
        console.error('[Omega_KG] Error loading debug info:', error);
    }
}

/**
 * Check if API key is configured
 */
async function checkConfiguration() {
    const data = await chrome.storage.local.get(STORAGE_KEYS.API_KEY);
    const isConfigured = !!data[STORAGE_KEYS.API_KEY];

    if (!isConfigured) {
        updateStatus('⚠️ API Key not configured. Click "Configure API Key" to set up.', 'error');
        captureBtn.disabled = true;
        captureBtn.textContent = '🔒 Configure First';
    } else {
        updateStatus('Ready to capture conversations.');
        captureBtn.disabled = false;
        captureBtn.textContent = '📸 Capture Conversation';
    }
}

/**
 * Trigger conversation capture
 */
async function captureConversation() {
    updateStatus('⏳ Capturing...', 'info');
    captureBtn.disabled = true;

    try {
        // Send message to content script to capture
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Execute capture in content script
        const response = await chrome.tabs.sendMessage(tab.id, {
            type: 'TRIGGER_CAPTURE',
        });

        if (response?.success) {
            // Update last capture timestamp
            const now = new Date().toLocaleString();
            await chrome.storage.local.set({ [STORAGE_KEYS.LAST_CAPTURE]: now });
            
            updateStatus('✅ Conversation captured successfully!', 'success');
            
            // Update debug panel if visible
            if (debugMode) {
                document.getElementById('debugLastCapture').textContent = now;
            }
        } else {
            updateStatus('❌ Capture failed: ' + (response?.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('[Omega_KG] Capture error:', error);
        updateStatus('❌ Error: ' + error.message, 'error');
    } finally {
        captureBtn.disabled = false;
    }
}

/**
 * Toggle debug panel
 */
function toggleDebugMode() {
    debugMode = !debugMode;
    if (debugMode) {
        debugPanel.classList.add('show');
        loadDebugInfo();
    } else {
        debugPanel.classList.remove('show');
    }
}

/**
 * Open extension options page
 */
function openOptions() {
    chrome.runtime.openOptionsPage();
}

// Event listeners
captureBtn.addEventListener('click', captureConversation);

logoHeader.addEventListener('click', (e) => {
    e.preventDefault();
    captureConversation();
});

logoHeader.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    toggleDebugMode();
});

configLink.addEventListener('click', openOptions);

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkConfiguration();
    console.debug('[Omega_KG] Popup initialized');
});

console.debug('[Omega_KG] Popup script loaded');

