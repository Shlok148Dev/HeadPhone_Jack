"""Name rules and profanity filtering (JNG-12-07)."""

from __future__ import annotations

import re
from datetime import date

from better_profanity import profanity
from django.conf import settings
from django.core.exceptions import ValidationError

USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,20}$")
RESERVED_USERNAMES = frozenset(
    {
        "admin", "administrator", "api", "jingle", "support", "help", "root", "system", "staff",
        "moderator", "mod", "official", "security", "privacy", "settings", "me", "null",
        "undefined",
        "deleted", "anonymous", "internal", "static", "login", "logout", "signup", "register",
    }
)

_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        profanity.load_censor_words()
        _loaded = True


def contains_profanity(text: str) -> bool:
    """True if the text contains profanity or slurs, including inside ``a_b.c`` style handles."""
    if not text:
        return False
    _ensure_loaded()
    spaced = re.sub(r"[_.\-]+", " ", text)
    squashed = re.sub(r"[^a-zA-Z]", "", text)
    return any(profanity.contains_profanity(t) for t in {text, spaced, squashed} if t)


def validate_username(value: str) -> None:
    if not USERNAME_RE.fullmatch(value or ""):
        raise ValidationError(
            "Usernames are 3-20 characters: lowercase letters, numbers, _ and . only.",
            code="invalid_username",
        )
    if value in RESERVED_USERNAMES:
        raise ValidationError("That username is reserved.", code="reserved_username")
    if contains_profanity(value):
        raise ValidationError("Please choose a different username.", code="profane_username")


def validate_clean_text(value: str) -> None:
    """For display names, college and city: reject profanity and slurs."""
    if contains_profanity(value):
        raise ValidationError("Please choose different wording.", code="profane_text")


def age_from_birth_year(birth_year: int, today: date | None = None) -> int:
    return (today or date.today()).year - birth_year


def is_old_enough(birth_year: int, today: date | None = None) -> bool:
    """NFR-PRIV-02: sign-up limited to users aged 18 or over, checked from birth year."""
    return age_from_birth_year(birth_year, today) >= settings.MINIMUM_AGE
