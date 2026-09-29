from django.urls import path

from . import views

urlpatterns = [
    path("sources/companion/token", views.CompanionTokenView.as_view(), name="companion-token"),
]
