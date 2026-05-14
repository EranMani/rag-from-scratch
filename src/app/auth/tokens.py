"""
JWT (JSON Web Tokens) — the digital passport linking identity to live interaction.

A JWT is a temporary, signed credential that lets the API verify who is calling
without hitting the database on every single request. This file owns the creation
and verification of those tokens.

How this file connects the auth pipeline to the agent:
    1. Identity:  db.py provides a permanent user_id.
    2. Issuance:  tokens.py wraps that user_id in a signed, time-limited token.
    3. Usage:     On each request, deps.py decodes the token and injects the
                  user_id into AgentState — giving the graph its thread anchor.
    4. Personalization: The user_id lets profile_update_node persist learning
                  data to the correct user across turns.

Decoupling value:
    Token logic lives in its own module so you can change security policy
    (e.g., add admin-role claims, adjust expiry, rotate signing keys) without
    touching the agent code or the database layer.
"""


from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings


def create_access_token(sub: str, extra: dict | None = None) -> str:
    """Sign a JWT containing the user_id (`sub` claim) and an expiration time.

    The `extra` dict allows injecting additional claims (e.g., roles, permissions)
    without modifying the function signature — open for extension, closed for modification.
    """
    # Expiry limits the damage window if a token is leaked
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # Standard JWT claims:
    #   sub (subject)   — the user_id, becomes the agent's thread anchor
    #   exp (expires)   — after this time, decode will reject the token
    #   iat (issued at) — records creation time for auditing / revocation checks
    payload = {"sub": sub, "exp": expire, "iat": datetime.now(timezone.utc)}
    if extra:
        payload.update(extra)

    # jwt.encode signs the payload with the server's secret key.
    # Only the server can produce a valid signature — an attacker cannot alter
    # the user_id (or any claim) without invalidating the signature.
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verify signature + expiry, then return the payload dict.

    If the token is expired or the signature doesn't match the secret,
    PyJWT raises an exception — caught upstream in deps.py as a 401.
    The returned payload contains 'sub' (user_id), which deps.py uses
    to load the user and inject identity into the agent's state.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
