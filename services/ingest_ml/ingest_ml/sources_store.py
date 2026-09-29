"""Persistence for routes (``linked_sources``; ADR-0006: ingest-ml writes this table).

``meta`` carries non-secret route bookkeeping: ``platform`` (the Connect button the user pressed),
``recent_cursor`` (epoch seconds of the newest play already fetched), ``reason`` on failure.
"""

from typing import Any
from uuid import UUID, uuid4

from jingle_common.enums import Platform, SourceKind, SourceStatus
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from .adapters.base import LinkedSource
from .db import dialect_insert, linked_sources, now, platform_connections

t = linked_sources


def _row_to_source(row: Any) -> LinkedSource:
    return LinkedSource(
        id=row.id,
        user_id=row.user_id,
        kind=SourceKind(row.kind),
        external_user_id=row.external_user_id or "",
        token_ciphertext=row.token_ciphertext or "",
        token_key_id=row.token_key_id or "",
        status=SourceStatus(row.status),
        last_ok_at=row.last_ok_at,
        meta=dict(row.meta or {}),
    )


async def get_source(engine: AsyncEngine, user_id: UUID, kind: SourceKind) -> LinkedSource | None:
    async with engine.connect() as conn:
        row = (
            await conn.execute(select(t).where(t.c.user_id == user_id, t.c.kind == kind.value))
        ).first()
    return _row_to_source(row) if row else None


async def get_source_by_id(engine: AsyncEngine, source_id: UUID) -> LinkedSource | None:
    async with engine.connect() as conn:
        row = (await conn.execute(select(t).where(t.c.id == source_id))).first()
    return _row_to_source(row) if row else None


async def save_source(engine: AsyncEngine, src: LinkedSource) -> LinkedSource:
    """Insert or replace the user's route of this kind (one per user and kind)."""
    ts = now()
    values = {
        "external_user_id": src.external_user_id,
        "token_ciphertext": src.token_ciphertext,
        "token_key_id": src.token_key_id,
        "status": src.status.value,
        "last_ok_at": src.last_ok_at,
        "meta": src.meta,
        "updated_at": ts,
    }
    async with engine.begin() as conn:
        stmt = dialect_insert(conn, t).values(
            id=src.id or uuid4(), user_id=src.user_id, kind=src.kind.value, created_at=ts, **values
        )
        await conn.execute(
            stmt.on_conflict_do_update(index_elements=["user_id", "kind"], set_=values)
        )
    saved = await get_source(engine, src.user_id, src.kind)
    assert saved is not None
    return saved


async def update_source(
    engine: AsyncEngine,
    source_id: UUID,
    *,
    status: SourceStatus | None = None,
    meta: dict[str, Any] | None = None,
    token_ciphertext: str | None = None,
    token_key_id: str | None = None,
    ok: bool = False,
) -> None:
    values: dict[str, Any] = {"updated_at": now()}
    if status is not None:
        values["status"] = status.value
    if meta is not None:
        values["meta"] = meta
    if token_ciphertext is not None:
        values["token_ciphertext"] = token_ciphertext
    if token_key_id is not None:
        values["token_key_id"] = token_key_id
    if ok:
        values["last_ok_at"] = values["updated_at"]
    async with engine.begin() as conn:
        await conn.execute(update(t).where(t.c.id == source_id).values(**values))


async def list_sources(
    engine: AsyncEngine, kinds: list[SourceKind], statuses: list[SourceStatus] | None = None
) -> list[LinkedSource]:
    stmt = select(t).where(t.c.kind.in_([k.value for k in kinds]))
    if statuses:
        stmt = stmt.where(t.c.status.in_([s.value for s in statuses]))
    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).all()
    return [_row_to_source(r) for r in rows]


async def count_sources(engine: AsyncEngine, kind: SourceKind) -> int:
    return len(
        await list_sources(
            engine, [kind], [SourceStatus.CONNECTED, SourceStatus.PENDING_FIRST_PLAY]
        )
    )


async def ensure_platform_connection(
    engine: AsyncEngine, user_id: UUID, platform: Platform, status: SourceStatus
) -> None:
    """Create the user-visible platform row (BR-13) if missing; never downgrade CONNECTED."""
    if platform is Platform.UNKNOWN:
        return
    ts = now()
    pc = platform_connections
    async with engine.begin() as conn:
        stmt = dialect_insert(conn, pc).values(
            id=uuid4(),
            user_id=user_id,
            platform=platform.value,
            status=status.value,
            first_play_at=None,
            last_signal_at=None,
            created_at=ts,
            updated_at=ts,
        )
        await conn.execute(stmt.on_conflict_do_nothing(index_elements=["user_id", "platform"]))
        if status is SourceStatus.NEEDS_REAUTH:
            await conn.execute(
                update(pc)
                .where(pc.c.user_id == user_id, pc.c.platform == platform.value)
                .values(status=status.value, updated_at=ts)
            )


async def delete_sources(engine: AsyncEngine, user_id: UUID, kinds: list[SourceKind]) -> int:
    async with engine.begin() as conn:
        res = await conn.execute(
            delete(t).where(t.c.user_id == user_id, t.c.kind.in_([k.value for k in kinds]))
        )
    return int(res.rowcount or 0)


async def delete_platform_connection(
    engine: AsyncEngine, user_id: UUID, platform: Platform
) -> None:
    pc = platform_connections
    async with engine.begin() as conn:
        await conn.execute(
            delete(pc).where(pc.c.user_id == user_id, pc.c.platform == platform.value)
        )
