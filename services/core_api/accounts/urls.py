from django.urls import path

from . import auth_views, views

urlpatterns = [
    path("ping", views.ping),
    path("auth/register", auth_views.RegisterView.as_view(), name="auth-register"),
    path("auth/login", auth_views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh", auth_views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", auth_views.LogoutView.as_view(), name="auth-logout"),
    path("auth/google", auth_views.GoogleSignInView.as_view(), name="auth-google"),
    path("me", views.MeView.as_view(), name="me"),
    path("me/privacy", views.PrivacyView.as_view(), name="me-privacy"),
    path("me/consents", views.ConsentListView.as_view(), name="me-consents"),
    path("me/consents/<str:purpose>", views.ConsentDetailView.as_view(), name="me-consent"),
    path("me/export", views.ExportView.as_view(), name="me-export"),
]
