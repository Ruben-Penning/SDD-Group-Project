const { expensesUrl, settlementsUrl, apiKey } = window.APP_CONFIG;
const TIMEOUT_MS = 5000;

// Every call has a timeout, so a service that is down shows a message
// instead of hanging the page.
async function api(baseUrl, path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(baseUrl + path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey, ...options.headers },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function showHealth(elementId, baseUrl) {
  const el = document.getElementById(elementId);
  try {
    await api(baseUrl, "/health");
    el.textContent = "up";
    el.className = "status up";
  } catch {
    el.textContent = "unavailable";
    el.className = "status down";
  }
}

showHealth("expenses-status", expensesUrl);
showHealth("settlements-status", settlementsUrl);
