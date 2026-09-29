"""Adapter registry. Approval-gated adapters load only when their feature flag is on.

Sprint 1 ships no polling adapters; ListenBrainz, Last.fm and Spotify register here in Sprint 2.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from jingle_common.enums import SourceKind

from .base import COMPANION_ROUTE, CompanionRoute, SourceAdapter

AdapterFactory = Callable[[], SourceAdapter]


@dataclass(frozen=True)
class Registration:
    kind: SourceKind
    factory: AdapterFactory
    flag: str | None = None  # e.g. "amazon_music_enabled"; None = always on


class AdapterRegistry:
    def __init__(self) -> None:
        self._entries: dict[SourceKind, Registration] = {}

    def register(
        self, kind: SourceKind, factory: AdapterFactory, *, flag: str | None = None
    ) -> None:
        if kind in self._entries:
            raise ValueError(f"adapter for {kind} already registered")
        self._entries[kind] = Registration(kind, factory, flag)

    def load(self, flags: Mapping[str, bool]) -> dict[SourceKind, SourceAdapter]:
        """Instantiate every adapter whose flag is on (missing flag ⇒ off)."""
        loaded: dict[SourceKind, SourceAdapter] = {}
        for reg in self._entries.values():
            if reg.flag is not None and not flags.get(reg.flag, False):
                continue
            adapter = reg.factory()
            if adapter.kind is not reg.kind:
                raise ValueError(f"factory for {reg.kind} built a {adapter.kind} adapter")
            loaded[reg.kind] = adapter
        return loaded


registry = AdapterRegistry()

PUSH_ROUTES: dict[SourceKind, CompanionRoute] = {SourceKind.COMPANION: COMPANION_ROUTE}
