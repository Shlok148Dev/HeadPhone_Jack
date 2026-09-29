"""MongoDB access (listens are written by ingest-ml; core-api reads them, CONTRACTS.md §2).

Every caller must tolerate ``get_db()`` returning ``None`` (Mongo unavailable): the feed then
degrades instead of failing (Technical Bible 9.4).
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

log = logging.getLogger(__name__)

_db: Any = None


def get_db() -> Any:
    global _db
    if _db is None:
        try:
            from pymongo import MongoClient

            client: MongoClient = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=500)
            _db = client.get_default_database(default="jingle")
        except Exception:  # noqa: BLE001
            log.warning("mongo unavailable")
            return None
    return _db


def set_db(db: Any) -> None:
    global _db
    _db = db
