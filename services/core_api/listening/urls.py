from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.SessionsView.as_view(), name="sessions"),
    path("sessions/<uuid:session_id>", views.SessionDetailView.as_view(), name="session"),
    path("sessions/<uuid:session_id>/join", views.action_view("join"), name="session-join"),
    path("sessions/<uuid:session_id>/leave", views.action_view("leave"), name="session-leave"),
    path("sessions/<uuid:session_id>/next", views.action_view("next"), name="session-next"),
    path("sessions/<uuid:session_id>/end", views.action_view("end"), name="session-end"),
    path("sessions/<uuid:session_id>/queue", views.QueueView.as_view(), name="session-queue"),
    path("queue/<uuid:entry_id>/vote", views.VoteView.as_view(), name="queue-vote"),
]
