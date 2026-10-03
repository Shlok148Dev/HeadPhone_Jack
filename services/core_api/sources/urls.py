from django.urls import path

from . import connect_views, views

urlpatterns = [
    path("sources/companion/token", views.CompanionTokenView.as_view(), name="companion-token"),
    path(
        "sources/listenbrainz",
        connect_views.ListenBrainzLinkView.as_view(),
        name="link-listenbrainz",
    ),
    path("sources/lastfm/username", connect_views.LastfmUsernameView.as_view(), name="link-lastfm"),
    path("sources/apple/link", connect_views.AppleLinkView.as_view(), name="link-apple"),
    path(
        "sources/connect-config", connect_views.ConnectConfigView.as_view(), name="connect-config"
    ),
    path(
        "sources/spotify/callback",
        connect_views.SpotifyCallbackView.as_view(),
        name="spotify-callback",
    ),
    path(
        "sources/lastfm/callback",
        connect_views.LastfmCallbackView.as_view(),
        name="lastfm-callback",
    ),
    path(
        "sources/<str:platform>/connect",
        connect_views.ConnectStartView.as_view(),
        name="connect-start",
    ),
    path("connections/<str:platform>", connect_views.UnlinkView.as_view(), name="unlink"),
    path("imports/youtube", connect_views.YouTubeImportView.as_view(), name="import-youtube"),
    path("imports/<str:job_id>", connect_views.ImportStatusView.as_view(), name="import-status"),
]
