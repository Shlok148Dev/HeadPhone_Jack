from django.urls import path

from . import views

urlpatterns = [
    path("recommendations", views.RecommendationsView.as_view(), name="recommendations"),
    path("inbox", views.InboxView.as_view(), name="inbox"),
    path("inbox/sent", views.SentView.as_view(), name="inbox-sent"),
    path("inbox/unread", views.UnreadView.as_view(), name="inbox-unread"),
    path("inbox/<uuid:delivery_id>/view", views.InboxViewView.as_view(), name="inbox-view"),
    path("inbox/<uuid:delivery_id>/react", views.InboxReactView.as_view(), name="inbox-react"),
    path("songs/search", views.SongSearchView.as_view(), name="songs-search"),
]
