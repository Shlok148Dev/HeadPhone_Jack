from django.urls import path

from . import views

urlpatterns = [
    path("drops", views.DropsView.as_view(), name="drops"),
    path("drops/today", views.TodayView.as_view(), name="drops-today"),
]
