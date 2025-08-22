from typing import Optional

from ws_server.core.config import config

try:  # pragma: no cover - optional dependency
    import jwt as pyjwt
except Exception:  # pragma: no cover
    pyjwt = None


def verify_token(token: Optional[str]) -> bool:
    """Verify a JWT or plain token according to configuration settings."""

    if config.jwt_bypass:
        return True

    if not token:
        return config.jwt_allow_plain

    t = token.strip()
    if t.lower().startswith("bearer "):
        t = t[7:].strip()

    if config.jwt_allow_plain and t == config.jwt_secret:
        return True

    if pyjwt is not None:
        try:
            pyjwt.decode(
                t, config.jwt_secret, algorithms=["HS256"], options={"verify_aud": False}
            )
            return True
        except Exception:
            return False

    return False


__all__ = ["verify_token"]
