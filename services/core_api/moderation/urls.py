from django.urls import path

from . import views

urlpatterns = [
    path("mod/reports", views.ReportQueueView.as_view(), name="mod-reports"),
    path(
        "mod/reports/<uuid:report_id>/action",
        views.ReportActionView.as_view(),
        name="mod-report-action",
    ),
    path("mod/appeals", views.AppealQueueView.as_view(), name="mod-appeals"),
    path(
        "mod/appeals/<uuid:appeal_id>/decide",
        views.AppealDecideView.as_view(),
        name="mod-appeal-decide",
    ),
    path("mod/audit", views.AuditView.as_view(), name="mod-audit"),
    path("admin/flags", views.AdminFlagsView.as_view(), name="admin-flags"),
    path("admin/budgets", views.AdminBudgetsView.as_view(), name="admin-budgets"),
    path("admin/allowlist", views.AdminAllowlistView.as_view(), name="admin-allowlist"),
    path("me/moderation", views.MyModerationView.as_view(), name="my-moderation"),
    path("me/moderation/<uuid:action_id>/appeal", views.AppealView.as_view(), name="my-appeal"),
]
