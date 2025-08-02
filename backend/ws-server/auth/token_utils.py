import os
import time
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, timedelta
import jwt

logger = logging.getLogger(__name__)

_WS_TOKEN = os.getenv("WS_TOKEN")
_JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY")
_JWT_PRIVATE_KEY = os.getenv("JWT_PRIVATE_KEY", _WS_TOKEN)
_RATE_LIMIT_PER_MIN = int(os.getenv("TOKEN_RATE_LIMIT_PER_MINUTE", "60"))

_RATE_LIMITS: Dict[str, List[float]] = {}
_REFRESH_TOKENS: Dict[str, str] = {}

def _rate_limited(token: str) -> bool:
    now = time.time()
    window_start = now - 60
    timestamps = _RATE_LIMITS.setdefault(token, [])
    while timestamps and timestamps[0] < window_start:
        timestamps.pop(0)
    if len(timestamps) >= _RATE_LIMIT_PER_MIN:
        return True
    timestamps.append(now)
    return False


def verify_token(token: Optional[str]) -> bool:
    """Validate the provided authentication token with optional rate limiting."""
    if not token:
        return False

    if _rate_limited(token):
        logger.warning("Token rate limit exceeded")
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


def generate_token(user_id: str, expires_in: int = 3600) -> Tuple[str, str]:
    """Generate access and refresh tokens."""
    if not _JWT_PRIVATE_KEY:
        raise RuntimeError("JWT_PRIVATE_KEY not configured")
    exp = datetime.utcnow() + timedelta(seconds=expires_in)
    access = jwt.encode({"sub": user_id, "exp": exp}, _JWT_PRIVATE_KEY, algorithm="HS256")
    refresh = jwt.encode({"sub": user_id, "type": "refresh"}, _JWT_PRIVATE_KEY, algorithm="HS256")
    _REFRESH_TOKENS[refresh] = user_id
    return access, refresh


def refresh_token(refresh_token: str) -> Optional[str]:
    user = _REFRESH_TOKENS.get(refresh_token)
    if not user:
        return None
    access, _ = generate_token(user)
    return access
