from django.urls import path

from . import views

urlpatterns = [
    path("exports/config", views.ExportConfigView.as_view(), name="exports-config"),
    path("exports/apple/token", views.AppleTokenView.as_view(), name="exports-apple-token"),
    path(
        "circles/<uuid:circle_id>/playlist/youtube-matches",
        views.YouTubeMatchView.as_view(),
        name="exports-youtube-matches",
    ),
    path(
        "circles/<uuid:circle_id>/playlist/exports",
        views.PlaylistExportView.as_view(),
        name="playlist-exports",
    ),
    path(
        "circles/<uuid:circle_id>/playlist/exports/<str:platform>",
        views.PlaylistExportView.as_view(),
        name="playlist-export",
    ),
]
