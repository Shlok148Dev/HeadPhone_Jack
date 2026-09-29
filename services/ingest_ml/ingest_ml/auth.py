"""Scrobble-token and service-token authentication (CONTRACTS.md §3).

Tokens are never logged and never placed in exception messages.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from .db import now, scrobble_tokens
from .resources import Resources, get_resources

TOKEN_PREFIX = "jng_"  # noqa: S105 - public prefix, not a secret


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def mint_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def parse_token_header(authorization: str | None) -> str | None:
    """``Authorization: Token <token>`` exactly as ListenBrainz clients send it."""
    if not authorization:
        return None
    scheme, _, value = authorization.strip().partition(" ")
    value = value.strip()
    if scheme.casefold() != "token" or not value or len(value) > 200:
        return None
    return value


@dataclass(frozen=True)
class TokenPrincipal:
    token_id: UUID
    user_id: UUID


async def lookup_token(
    engine: AsyncEngine, token: str, *, touch: bool = True
) -> TokenPrincipal | None:
    digest = hash_token(token)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                select(
                    scrobble_tokens.c.id,
                    scrobble_tokens.c.user_id,
                    scrobble_tokens.c.token_sha256,
                )
                .where(scrobble_tokens.c.token_sha256 == digest)
                .where(scrobble_tokens.c.revoked_at.is_(None))
            )
        ).first()
        if row is None or not hmac.compare_digest(row.token_sha256, digest):
            return None
        if touch:
            ts = now()
            await conn.execute(
                update(scrobble_tokens)
                .where(scrobble_tokens.c.id == row.id)
                .values(last_used_at=ts, updated_at=ts)
            )
        return TokenPrincipal(token_id=row.id, user_id=row.user_id)


def require_service_token(
    x_service_token: str | None = Header(default=None),
    res: Resources = Depends(get_resources),  # noqa: B008
) -> None:
    expected = res.settings.service_token
    if not x_service_token or not hmac.compare_digest(x_service_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="SERVICE_TOKEN_INVALID")
