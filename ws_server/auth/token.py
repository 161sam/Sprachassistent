import os
from typing import Optional

try:  # pragma: no cover - optional dependency
    import jwt as pyjwt
except Exception:  # pragma: no cover
    pyjwt = None


def verify_token(token: Optional[str]) -> bool:
    """Verify a JWT or plain token according to environment settings."""
    if os.getenv("JWT_BYPASS", "0") == "1":
        return True

    if not token:
        if os.getenv("JWT_ALLOW_PLAIN", "0") == "1":
            return True
        return False

    t = token.strip()
    if t.lower().startswith("bearer "):
        t = t[7:].strip()

    secret = os.getenv("JWT_SECRET", "devsecret")

    if os.getenv("JWT_ALLOW_PLAIN", "0") == "1" and t == secret:
        return True

    if pyjwt is not None:
        try:
            pyjwt.decode(t, secret, algorithms=["HS256"], options={"verify_aud": False})
            return True
        except Exception:
            return False

    return False


__all__ = ["verify_token"]
