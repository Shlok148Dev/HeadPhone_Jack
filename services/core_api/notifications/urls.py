from django.urls import path

from . import views

urlpatterns = [
    path("notifications", views.NotificationsView.as_view(), name="notifications"),
    path("notifications/read", views.ReadView.as_view(), name="notifications-read"),
    path("notifications/push-key", views.PushKeyView.as_view(), name="push-key"),
    path("me/notification-settings", views.SettingsView.as_view(), name="notification-settings"),
    path("me/push-subscription", views.PushSubscriptionView.as_view(), name="push-subscription"),
]
