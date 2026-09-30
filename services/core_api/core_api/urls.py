from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import FlagsView, healthz

urlpatterns = [
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="schema-docs"),
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
    # Service-to-service only (X-Service-Token); never routed by the edge.
    path("internal/", include("core_api.internal")),
]
