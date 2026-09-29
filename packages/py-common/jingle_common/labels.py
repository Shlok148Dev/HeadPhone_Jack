"""Freshness labels (CONTRACTS.md §7). Built server-side only; never contain route words."""

from datetime import datetime

from .enums import PLATFORM_DISPLAY_NAMES, CardState, Platform


def _on(platform: Platform) -> str:
    name = PLATFORM_DISPLAY_NAMES.get(platform, "")
    return f" on {name}" if name else ""


def freshness_label(
    state: CardState,
    platform: Platform,
    observed_at: datetime | None,
    now: datetime,
    show_precise_time: bool = True,
) -> str:
    if state is CardState.HIDDEN:
        return "Hidden"
    if state is CardState.TOP:
        return "Top this month"
    if state is CardState.LIVE:
        return f"Live{_on(platform)}"
    if observed_at is None or not show_precise_time:
        return f"Recently{_on(platform)}"
    secs = max(0, int((now - observed_at).total_seconds()))
    if secs < 60:
        return f"Just now{_on(platform)}"
    if secs < 3600:
        return f"{secs // 60} min ago{_on(platform)}"
    if secs < 86400:
        return f"{secs // 3600} h ago{_on(platform)}"
    return f"{secs // 86400} d ago{_on(platform)}"
