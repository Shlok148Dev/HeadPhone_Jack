"""JNG-01-15 profile photos: validated by content, re-encoded (no EXIF), replaced, removed, purged."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


def photo(fmt="JPEG", size=(800, 600), color=(200, 80, 40), exif=False) -> SimpleUploadedFile:
    b = io.BytesIO()
    img = Image.new("RGB", size, color)
    kw = {}
    if exif:
        ex = Image.Exif()
        ex[0x8825] = {2: (19, 4, 0)}  # GPSInfo: a location that must not survive
        ex[0x010F] = "SecretCam"
        kw["exif"] = ex.tobytes()
    img.save(b, fmt, **kw)
    return SimpleUploadedFile(f"me.{fmt.lower()}", b.getvalue(), content_type="image/jpeg")


def test_upload_makes_square_jpegs_without_exif(media):
    u = UserFactory()
    r = client(u).post("/api/v1/me/avatar", {"file": photo(exif=True)}, format="multipart")
    assert r.status_code == 200 and r.json()["avatar_url"].startswith(f"/media/avatars/{u.pk}/")
    files = sorted(p.name for p in (media / "avatars" / str(u.pk)).iterdir())
    assert len(files) == 2 and files[0].endswith("-128.jpg") and files[1].endswith("-512.jpg")
    with Image.open(media / "avatars" / str(u.pk) / files[1]) as out:
        assert out.size == (512, 512) and out.format == "JPEG"
        assert not out.getexif()  # GPS and camera data are gone
    # Friends and everyone who can see the person get the photo.
    from social.views import person

    u.refresh_from_db()
    assert person(u, "friends")["avatar_url"] == r.json()["avatar_url"]


@pytest.mark.parametrize(
    ("upload", "status", "code"),
    [
        (
            SimpleUploadedFile("evil.jpg", b"<?php echo 'x'; ?>", content_type="image/jpeg"),
            400,
            "UNSUPPORTED_IMAGE",
        ),
        (
            SimpleUploadedFile("doc.pdf", b"%PDF-1.4 not an image", content_type="application/pdf"),
            400,
            "UNSUPPORTED_IMAGE",
        ),
        (None, 400, "VALIDATION_ERROR"),
    ],
)
def test_rejects_non_images(upload, status, code):
    data = {"file": upload} if upload else {}
    r = client(UserFactory()).post("/api/v1/me/avatar", data, format="multipart")
    assert r.status_code == status and r.json()["error"]["code"] == code


def test_rejects_too_large_and_too_small(settings):
    settings.AVATAR_MAX_BYTES = 1000
    r = client(UserFactory()).post(
        "/api/v1/me/avatar", {"file": photo(fmt="PNG", size=(400, 400))}, format="multipart"
    )
    assert r.status_code == 413
    settings.AVATAR_MAX_BYTES = 5 * 1024 * 1024
    r = client(UserFactory()).post(
        "/api/v1/me/avatar", {"file": photo(size=(40, 40))}, format="multipart"
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "IMAGE_TOO_SMALL"


def test_replace_keeps_only_the_new_pair_and_delete_removes(media):
    u = UserFactory()
    c = client(u)
    first = c.post(
        "/api/v1/me/avatar", {"file": photo(color=(10, 10, 10))}, format="multipart"
    ).json()["avatar_url"]
    second = c.post(
        "/api/v1/me/avatar", {"file": photo(fmt="PNG", color=(250, 250, 0))}, format="multipart"
    ).json()["avatar_url"]
    assert first != second and len(list((media / "avatars" / str(u.pk)).iterdir())) == 2
    r = c.delete("/api/v1/me/avatar")
    assert r.status_code == 200 and r.json()["avatar_url"] is None
    assert not (media / "avatars" / str(u.pk)).exists()


def test_unauthenticated_upload_is_rejected():
    assert (
        APIClient().post("/api/v1/me/avatar", {"file": photo()}, format="multipart").status_code
        == 401
    )


def test_purge_deletes_the_photo(media):
    from django.utils import timezone

    from accounts.services import purge_account

    u = UserFactory()
    client(u).post("/api/v1/me/avatar", {"file": photo()}, format="multipart")
    u.refresh_from_db()
    u.deleted_at = timezone.now()
    u.save(update_fields=["deleted_at"])
    assert purge_account(u.pk) is True
    assert not (media / "avatars" / str(u.pk)).exists()
