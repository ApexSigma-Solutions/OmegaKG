document.addEventListener('DOMContentLoaded', () => {
  const statusDiv = document.getElementById('status');
  const apiKeyInput = document.getElementById('apiKeyInput');

  // Load saved API Key
  chrome.storage.sync.get(['omegaApiKey'], (result) => {
    if (result.omegaApiKey) {
      apiKeyInput.value = result.omegaApiKey;
    }
  });

  // Save API Key
  document.getElementById('saveKeyBtn').addEventListener('click', () => {
    const key = apiKeyInput.value.trim();
    if (key) {
      chrome.storage.sync.set({ omegaApiKey: key }, () => {
        statusDiv.textContent = "API Key saved!";
        setTimeout(() => statusDiv.textContent = "Ready.", 2000);
      });
    }
  });

  document.getElementById('captureBtn').addEventListener('click', async () => {
    const apiKey = apiKeyInput.value.trim();

    // 1. EXTRACT HTML
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const injection = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        html: document.documentElement.outerHTML,
        title: document.title,
        url: window.location.href
      })
    });
    const pageData = injection[0].result;

    // Import configuration module
    const config = await import('./config.js');

    // 2. AUTHENTICATE
    const tokenUrl = await config.config.getEndpointUrl('AUTH_TOKEN');
    const authResp = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'x-api-key': apiKey }
    });
    const token = (await authResp.json()).access_token;

    // 3. SEND
    const captureUrl = await config.config.getEndpointUrl('CAPTURE');
    const res = await fetch(captureUrl, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: "Extension", source: "chrome_ext", platform: "web",
        url: pageData.url, title: pageData.title, raw_html: pageData.html
      })
    });

    statusDiv.textContent = (res.ok) ? "✅ Success" : "❌ Failed";
  });
});
