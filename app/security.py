import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

import app.config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Require X-API-Key when EDTA_API_KEY is configured."""
    if not app.config.settings.auth_enabled:
        return
    configured = app.config.settings.api_key or ""
    provided = api_key or ""
    if not secrets.compare_digest(provided, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
