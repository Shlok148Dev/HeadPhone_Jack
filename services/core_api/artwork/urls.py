from django.urls import path

from . import views

urlpatterns = [
    path("artwork", views.ArtworkView.as_view(), name="artwork"),
    path("artwork/wall", views.ArtworkWallView.as_view(), name="artwork-wall"),
]
