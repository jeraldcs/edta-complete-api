(function () {
  let apiKey = null;
  let initPromise = null;

  function applyInlineConfig() {
    const inline = window.__EDTA_DEMO_CONFIG__;
    if (!inline) {
      return false;
    }
    apiKey = inline.api_key || null;
    return true;
  }

  async function init() {
    if (applyInlineConfig()) {
      return;
    }
    if (!initPromise) {
      initPromise = (async () => {
        try {
          const response = await fetch("/demo-config");
          if (!response.ok) {
            return;
          }
          const config = await response.json();
          apiKey = config.api_key || null;
        } catch (_error) {
          apiKey = null;
        }
      })();
    }
    return initPromise;
  }

  function withAuthHeaders(headers = {}) {
    const merged = { ...headers };
    if (apiKey) {
      merged["X-API-Key"] = apiKey;
    }
    return merged;
  }

  async function apiFetch(url, options = {}) {
    await init();
    const timeoutMs = options.timeoutMs ?? 90000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const request = { ...options };
    delete request.timeoutMs;
    const headers = withAuthHeaders(options.headers || {});
    if (request.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    request.headers = headers;
    request.signal = controller.signal;

    try {
      return await fetch(url, request);
    } catch (error) {
      if (error && error.name === "AbortError") {
        throw new Error(
          "Request timed out. The server may still be waking up — wait a few seconds and click Recommend again.",
        );
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  window.DemoApi = {
    init,
    fetch: apiFetch,
    withAuthHeaders,
  };
})();
