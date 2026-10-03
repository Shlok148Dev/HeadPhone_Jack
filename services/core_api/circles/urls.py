from django.urls import path

from . import views

urlpatterns = [
    path("circles", views.CirclesView.as_view(), name="circles"),
    path("circles/invites", views.MyInvitesView.as_view(), name="circle-invites-mine"),
    path(
        "circles/invites/<uuid:invite_id>/<str:action>",
        views.MyInviteActionView.as_view(),
        name="circle-invite-action",
    ),
    path("circles/suggested", views.SuggestedCirclesView.as_view(), name="circles-suggested"),
    path(
        "circles/suggested/<uuid:suggestion_id>/<str:action>",
        views.SuggestedCircleActionView.as_view(),
        name="circles-suggested-action",
    ),
    path("circles/join/<str:token>", views.JoinView.as_view(), name="circle-join"),
    path("circles/<uuid:circle_id>", views.CircleDetailView.as_view(), name="circle"),
    path("circles/<uuid:circle_id>/feed", views.CircleFeedView.as_view(), name="circle-feed"),
    path(
        "circles/<uuid:circle_id>/playlist",
        views.CirclePlaylistView.as_view(),
        name="circle-playlist",
    ),
    path(
        "circles/<uuid:circle_id>/playlist/<uuid:item_id>",
        views.CirclePlaylistItemView.as_view(),
        name="circle-playlist-item",
    ),
    path(
        "circles/<uuid:circle_id>/invites", views.CircleInvitesView.as_view(), name="circle-invites"
    ),
    path("circles/<uuid:circle_id>/links", views.CircleLinkView.as_view(), name="circle-links"),
    path("circles/<uuid:circle_id>/transfer", views.TransferView.as_view(), name="circle-transfer"),
    path(
        "circles/<uuid:circle_id>/members/<uuid:user_id>",
        views.MemberView.as_view(),
        name="circle-member",
    ),
]
