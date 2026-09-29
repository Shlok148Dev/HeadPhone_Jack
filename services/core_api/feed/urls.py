from django.urls import path

from . import views

urlpatterns = [
    path("me/card", views.MyCardView.as_view(), name="me-card"),
    path("connections", views.ConnectionsView.as_view(), name="connections"),
]
