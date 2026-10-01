from django.urls import path

from . import views

urlpatterns = [
    path("compatibility/<uuid:user_id>", views.CompatibilityView.as_view(), name="compatibility"),
    path("me/stats", views.MyStatsView.as_view(), name="my-stats"),
    path("me/timeline", views.MyTimelineView.as_view(), name="my-timeline"),
    path("users/<str:username>", views.ProfileView.as_view(), name="profile"),
]
