import json
from pathlib import Path

from fastapi.responses import HTMLResponse

from app.config import settings

DEMO_ASSET_VERSION = "20260717l"


def render_scenario_demo() -> HTMLResponse:
    """Serve scenario demo HTML with inline auth config and cache-busted assets."""
    html = Path("static/scenario.html").read_text(encoding="utf-8")
    config = {
        "auth_enabled": settings.auth_enabled,
        "api_key": (
            settings.api_key
            if settings.auth_enabled and settings.expose_demo_api_key
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
    for asset in ("demo-api.js", "demo-shared.js", "scenario_app.js"):
        html = html.replace(f"/static/{asset}", f"/static/{asset}?v={DEMO_ASSET_VERSION}")
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})
