"""SQLAlchemy Core mirrors of the Django-owned ingestion tables (ADR-0006).

Django owns the migrations (services/core_api/sources/models.py). These definitions must match
its column names exactly; they are only ``create_all``-ed in tests (SQLite). Django fills
``created_at``/``updated_at`` and blank CharFields in Python, not as DB defaults, so every insert
here must supply them (see :func:`now` and the ``''`` defaults below).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

metadata = MetaData()

# BigAutoField in Postgres; SQLite only autoincrements INTEGER PRIMARY KEY.
_BigAuto = BigInteger().with_variant(Integer(), "sqlite")
_Json = JSON().with_variant(postgresql.JSONB(), "postgresql")


def _ts() -> list[Column[Any]]:
    return [
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    ]


# Read-only mirror (Django owns and writes users); username is shown by validate-token.
users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("username", String(150), nullable=True),
)

platform_connections = Table(
    "platform_connections",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("platform", String(20), nullable=False),
    Column("status", String(24), nullable=False),
    Column("first_play_at", DateTime(timezone=True), nullable=True),
    Column("last_signal_at", DateTime(timezone=True), nullable=True),
    *_ts(),
    UniqueConstraint("user_id", "platform", name="platform_connection_unique"),
)

linked_sources = Table(
    "linked_sources",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("external_user_id", String(200), nullable=False, default=""),
    Column("token_ciphertext", Text, nullable=False, default=""),
    Column("token_key_id", String(40), nullable=False, default=""),
    Column("status", String(24), nullable=False),
    Column("last_ok_at", DateTime(timezone=True), nullable=True),
    Column("meta", _Json, nullable=False),
    *_ts(),
    UniqueConstraint("user_id", "kind", name="linked_source_user_kind"),
)

scrobble_tokens = Table(
    "scrobble_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_sha256", String(64), nullable=False, unique=True),
    Column("label", String(60), nullable=False),
    Column("last_used_at", DateTime(timezone=True), nullable=True),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    *_ts(),
)

artists = Table(
    "artists",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("mbid", Uuid, nullable=True),
    Column("name", String(300), nullable=False),
    *_ts(),
    Index(
        "artists_mbid",
        "mbid",
        unique=True,
        postgresql_where=text("mbid IS NOT NULL"),
        sqlite_where=text("mbid IS NOT NULL"),
    ),
)

artist_tags = Table(
    "artist_tags",
    metadata,
    Column("id", _BigAuto, primary_key=True, autoincrement=True),
    Column("artist_id", Uuid, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False),
    Column("tag", String(80), nullable=False),
    Column("weight", Float, nullable=False),
    UniqueConstraint("artist_id", "tag", name="artist_tag_unique"),
)

recordings = Table(
    "recordings",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("isrc", String(12), nullable=True),
    Column("mbid", Uuid, nullable=True),
    Column("title", String(500), nullable=False),
    Column("artist_name", String(500), nullable=False),
    Column("album", String(500), nullable=False, default=""),
    Column("release_mbid", Uuid, nullable=True),
    Column("duration_ms", Integer, nullable=True),
    Column("artwork_url", String(800), nullable=False, default=""),
    Column("artist_id", Uuid, ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
    Column("norm_key", String(600), nullable=False, index=True),
    Column("resolution", String(16), nullable=False),
    *_ts(),
    Index(
        "recordings_isrc",
        "isrc",
        unique=True,
        postgresql_where=text("isrc IS NOT NULL"),
        sqlite_where=text("isrc IS NOT NULL"),
    ),
    Index(
        "recordings_mbid",
        "mbid",
        unique=True,
        postgresql_where=text("mbid IS NOT NULL"),
        sqlite_where=text("mbid IS NOT NULL"),
    ),
)

recording_links = Table(
    "recording_links",
    metadata,
    Column("id", _BigAuto, primary_key=True, autoincrement=True),
    Column("recording_id", Uuid, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False),
    Column("platform", String(20), nullable=False),
    Column("external_id", String(200), nullable=False, default=""),
    Column("url", String(800), nullable=False),
    Column("is_search", Boolean, nullable=False, default=False),
    UniqueConstraint("recording_id", "platform", name="recording_link_platform"),
)


def now() -> datetime:
    return datetime.now(UTC)


def normalize_database_url(url: str) -> str:
    """Accept Django/Heroku style ``postgres://`` URLs and select the psycopg 3 async driver."""
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    if url.startswith("sqlite://") and not url.startswith("sqlite+"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    return url


def make_engine(url: str) -> AsyncEngine:
    url = normalize_database_url(url)
    if url.startswith("sqlite"):
        return create_async_engine(
            url, poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
    # PgBouncer-friendly: no prepared statements (Tech Bible 8.3).
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"prepare_threshold": None},
    )


def dialect_insert(conn: AsyncConnection, table: Table) -> Any:
    """``INSERT … ON CONFLICT`` builder for the connection's dialect (Postgres or SQLite)."""
    if conn.dialect.name == "postgresql":
        return postgresql.insert(table)
    return sqlite.insert(table)
