from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

import app.config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Require X-API-Key when EDTA_API_KEY is configured."""
    if not app.config.settings.auth_enabled:
        return
    if api_key != app.config.settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
