import json
from pathlib import Path

from fastapi.responses import HTMLResponse

import app.config as edta_config

DEMO_ASSET_VERSION = "20260719a"
_DEMO_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


def render_scenario_demo() -> HTMLResponse:
    """Serve scenario demo HTML with inline auth config and cache-busted assets."""
    html = Path("static/scenario.html").read_text(encoding="utf-8")
    config = {
        "auth_enabled": edta_config.settings.auth_enabled,
        "demo_proxy_enabled": edta_config.settings.auth_enabled and not edta_config.settings.expose_demo_api_key,
        "api_key": (
            edta_config.settings.api_key
            if edta_config.settings.auth_enabled and edta_config.settings.expose_demo_api_key
            else None
        ),
    }
    boot = (
        f"<script>window.__EDTA_DEMO_CONFIG__ = {json.dumps(config)};</script>"
        f'<script>window.addEventListener("error",function(e){{'
        f'var el=document.getElementById("scenarioRunError");'
        f'if(el){{el.textContent="Page error: "+(e.message||"unknown");'
        f'el.classList.remove("hidden");}}}});</script>'
    )
    html = html.replace("<!--EDTA_DEMO_BOOT-->", boot, 1)
    for asset in ("styles.css", "demo-api.js", "demo-shared.js", "scenario_app.js"):
        html = html.replace(f"/static/{asset}", f"/static/{asset}?v={DEMO_ASSET_VERSION}")
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": _DEMO_CSP,
        },
    )
