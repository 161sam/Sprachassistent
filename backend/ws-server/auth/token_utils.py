import os
from typing import Optional
import logging
import jwt

logger = logging.getLogger(__name__)

_WS_TOKEN = os.getenv("WS_TOKEN")
_JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY")

# TODO (docs/security.md,
#   docs/Projekt-Verbesserungen.md §Backend-Optimierungen):
#   Provide full JWT management with refresh tokens and rate limiting to
#   align with the documented security architecture.

def verify_token(token: Optional[str]) -> bool:
    """Validate the provided authentication token.

    If ``JWT_PUBLIC_KEY`` is set the function will try to verify the token as a
    JWT.  Otherwise the token is compared against ``WS_TOKEN`` from the
    environment.
    """
    if not token:
        return False

    if _JWT_PUBLIC_KEY:
        try:
            jwt.decode(token, _JWT_PUBLIC_KEY, algorithms=["RS256", "HS256"])
            return True
        except Exception:
            logger.warning("JWT verification failed")
            return False

    if _WS_TOKEN is None:
        logger.warning("WS_TOKEN not configured")
        return False
    return token == _WS_TOKEN
