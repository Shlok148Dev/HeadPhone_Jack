from django.urls import path

from . import views

urlpatterns = [
    path("friends", views.FriendsView.as_view(), name="friends"),
    path("friends/requests", views.FriendRequestsView.as_view(), name="friend-requests"),
    path(
        "friends/requests/<uuid:request_id>",
        views.FriendRequestCancelView.as_view(),
        name="friend-request",
    ),
    path(
        "friends/requests/<uuid:request_id>/<str:action>",
        views.FriendRequestActionView.as_view(),
        name="friend-request-action",
    ),
    path("friends/<uuid:user_id>", views.FriendDetailView.as_view(), name="friend"),
    path("users/search", views.UserSearchView.as_view(), name="user-search"),
    path("blocks", views.BlocksView.as_view(), name="blocks"),
    path("blocks/<uuid:user_id>", views.BlockDetailView.as_view(), name="block"),
    path("reports", views.ReportsView.as_view(), name="reports"),
    path("me/invite", views.MyInviteView.as_view(), name="my-invite"),
    path("invites/<str:code>", views.InviteView.as_view(), name="invite"),
]
