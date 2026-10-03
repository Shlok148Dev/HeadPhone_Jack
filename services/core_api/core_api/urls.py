from django.conf import settings as _settings  # noqa: E402
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny, IsAdminUser  # noqa: E402

from .views import FlagsView, healthz

_DOCS_PERMS = [AllowAny] if _settings.API_DOCS_PUBLIC else [IsAdminUser]

urlpatterns = [
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    # API docs map every endpoint: staff only unless API_DOCS_PUBLIC (security campaign 2026-10).
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=_DOCS_PERMS), name="schema"),
    path(
        "api/schema/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=_DOCS_PERMS),
        name="schema-docs",
    ),
    path("api/v1/flags", FlagsView.as_view(), name="flags"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("feed.urls")),
    path("api/v1/", include("sources.urls")),
    path("api/v1/", include("social.urls")),
    path("api/v1/", include("suggestions.urls")),
    path("api/v1/", include("circles.urls")),
    path("api/v1/", include("sends.urls")),
    path("api/v1/", include("blends.urls")),
    path("api/v1/", include("listening.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("rituals.urls")),
    path("api/v1/", include("moderation.urls")),
    path("api/v1/", include("artwork.urls")),
    path("api/v1/", include("insights.urls")),
    path("api/v1/", include("drops.urls")),
    path("api/v1/", include("charts.urls")),
    path("api/v1/", include("exports.urls")),
    # Service-to-service only (X-Service-Token); never routed by the edge.
    path("internal/", include("core_api.internal")),
]
