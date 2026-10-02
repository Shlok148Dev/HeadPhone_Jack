"""Profile photos (JNG-01-15).

Uploads are untrusted: size-capped before reading, decoded by Pillow with a decompression-bomb
limit, restricted to JPEG/PNG/WebP/GIF by *content* (not name or header), re-encoded from pixels
so EXIF/GPS and any embedded payload are dropped, centre-cropped to a square and stored as two
JPEGs (512 and 128 px) under a content-hash name. Only the path is kept on the user.
"""

from __future__ import annotations

import hashlib
import io
import shutil
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from core_api.errors import ApiError

ALLOWED = {"JPEG", "PNG", "WEBP", "GIF"}
SIZES = (512, 128)
Image.MAX_IMAGE_PIXELS = 40_000_000  # ~6300×6300; anything bigger is rejected as a bomb


def _root() -> Path:
    return Path(settings.MEDIA_ROOT)


def url_for(user) -> str | None:
    return f"{settings.MEDIA_URL}{user.avatar}" if getattr(user, "avatar", "") else None


def save(user, upload) -> str:
    if upload is None:
        raise ApiError("VALIDATION_ERROR", "Choose a photo to upload.", 400)
    if upload.size > settings.AVATAR_MAX_BYTES:
        raise ApiError("FILE_TOO_LARGE", "Photos can be up to 5 MB.", 413)
    raw = upload.read(settings.AVATAR_MAX_BYTES + 1)
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in ALLOWED:
            raise UnidentifiedImageError(fmt)
        img = Image.open(io.BytesIO(raw))
        img.seek(0)  # first frame of a GIF
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError(
            "UNSUPPORTED_IMAGE", "That file isn't a photo we can use (JPEG, PNG, WebP or GIF).", 400
        ) from None
    if min(img.size) < 64:
        raise ApiError("IMAGE_TOO_SMALL", "Use a photo at least 64×64 pixels.", 400)

    square = ImageOps.fit(
        img, (SIZES[0], SIZES[0]), method=Image.Resampling.LANCZOS, centering=(0.5, 0.4)
    )
    digest = hashlib.sha256(square.tobytes()).hexdigest()[:20]
    folder = _root() / "avatars" / str(user.pk)
    folder.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        out = square if size == SIZES[0] else square.resize((size, size), Image.Resampling.LANCZOS)
        out.save(
            folder / f"{digest}-{size}.jpg", "JPEG", quality=86, optimize=True, progressive=True
        )
    # Old photos go now; only the current pair stays on disk.
    for f in folder.iterdir():
        if not f.name.startswith(digest):
            f.unlink(missing_ok=True)
    user.avatar = f"avatars/{user.pk}/{digest}-{SIZES[0]}.jpg"
    user.save(update_fields=["avatar"])
    return user.avatar


def remove(user) -> None:
    shutil.rmtree(_root() / "avatars" / str(user.pk), ignore_errors=True)
    if user.avatar:
        user.avatar = ""
        user.save(update_fields=["avatar"])
