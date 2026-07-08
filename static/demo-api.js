(function () {
  let apiKey = null;
  let initPromise = null;

  async function init() {
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
    const request = { ...options };
    const headers = withAuthHeaders(options.headers || {});
    if (request.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    request.headers = headers;
    return fetch(url, request);
  }

  window.DemoApi = {
    init,
    fetch: apiFetch,
    withAuthHeaders,
  };
})();
