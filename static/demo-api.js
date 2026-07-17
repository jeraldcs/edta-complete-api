(function () {
  let apiKey = null;
  let initPromise = null;
  let serverAwake = false;
  let wakeInFlight = null;

  function applyInlineConfig() {
    const inline = window.__EDTA_DEMO_CONFIG__;
    if (!inline) {
      return false;
    }
    apiKey = inline.api_key || null;
    return true;
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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

  async function pingHealth(timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch("/health", { signal: controller.signal });
      return response.ok;
    } catch (_error) {
      return false;
    } finally {
      clearTimeout(timer);
    }
  }

  async function ensureServerAwake(onProgress) {
    if (serverAwake) {
      return true;
    }
    if (wakeInFlight) {
      return wakeInFlight;
    }

    wakeInFlight = (async () => {
      onProgress?.(
        "Starting demo server — first visit after idle may take up to 30 seconds. Please wait…",
      );
      for (let attempt = 0; attempt < 4; attempt += 1) {
        const ok = await pingHealth(15000);
        if (ok) {
          serverAwake = true;
          onProgress?.(null);
          return true;
        }
        if (attempt < 3) {
          onProgress?.(
            `Still waking up the demo server (attempt ${attempt + 2} of 4)…`,
          );
          await sleep(2500);
        }
      }
      onProgress?.(null);
      return false;
    })();

    try {
      return await wakeInFlight;
    } finally {
      wakeInFlight = null;
    }
  }

  function resolveApiPath(path) {
    const inline = window.__EDTA_DEMO_CONFIG__;
    const proxyEnabled = inline?.demo_proxy_enabled;
    const needsProxy = proxyEnabled && !apiKey;
    if (needsProxy && typeof path === "string" && path.startsWith("/") && !path.startsWith("/demo-api")) {
      return `/demo-api${path}`;
    }
    return path;
  }

  async function apiFetch(url, options = {}) {
    await init();
    const requestUrl = resolveApiPath(url);
    const timeoutMs = options.timeoutMs ?? 90000;
    const wakeUp = options.wakeUp !== false;
    const onProgress = options.onProgress;
    delete options.timeoutMs;
    delete options.wakeUp;
    delete options.onProgress;

    if (wakeUp && !serverAwake && typeof url === "string" && !url.includes("/health")) {
      await ensureServerAwake(onProgress);
    }

    async function attemptFetch() {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      const request = { ...options };
      const headers = withAuthHeaders(options.headers || {});
      if (request.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
      request.headers = headers;
      request.signal = controller.signal;

      try {
        return await fetch(requestUrl, request);
      } finally {
        clearTimeout(timer);
      }
    }

    try {
      let response = await attemptFetch();
      if (!response.ok && [502, 503, 504].includes(response.status)) {
        onProgress?.("Demo server is still starting — retrying once…");
        serverAwake = false;
        await ensureServerAwake(onProgress);
        response = await attemptFetch();
      }
      return response;
    } catch (error) {
      if (error && error.name === "AbortError") {
        throw new Error(
          "Request timed out. The server may still be waking up — wait a few seconds and click Recommend again.",
        );
      }
      if (wakeUp && !serverAwake) {
        onProgress?.("Demo server is still starting — retrying once…");
        serverAwake = false;
        await ensureServerAwake(onProgress);
        try {
          return await attemptFetch();
        } catch (retryError) {
          if (retryError && retryError.name === "AbortError") {
            throw new Error(
              "Request timed out. The server may still be waking up — wait a few seconds and click Recommend again.",
            );
          }
          throw retryError;
        }
      }
      throw error;
    }
  }

  window.DemoApi = {
    init,
    fetch: apiFetch,
    withAuthHeaders,
    ensureServerAwake,
  };
})();
