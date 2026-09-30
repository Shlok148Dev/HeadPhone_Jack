from django.urls import path

from . import views

urlpatterns = [
    path("me/card", views.MyCardView.as_view(), name="me-card"),
    path("connections", views.ConnectionsView.as_view(), name="connections"),
    path("feed", views.FeedView.as_view(), name="feed"),
    path("feed/<uuid:user_id>", views.FeedCardDetailView.as_view(), name="feed-card"),
]
