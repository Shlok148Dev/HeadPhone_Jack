from django.urls import path

from . import views

urlpatterns = [
    path("rituals", views.RitualsView.as_view(), name="rituals"),
    path("circles/<uuid:circle_id>/battle", views.CircleBattleView.as_view(), name="circle-battle"),
    path(
        "circles/<uuid:circle_id>/battle/nominate",
        views.NominateView.as_view(),
        name="battle-nominate",
    ),
    path("circles/<uuid:circle_id>/battle/skip", views.SkipView.as_view(), name="battle-skip"),
    path("circles/<uuid:circle_id>/season", views.SeasonView.as_view(), name="circle-season"),
    path("battles/<uuid:battle_id>/votes", views.VoteView.as_view(), name="battle-vote"),
    path(
        "battles/<uuid:battle_id>/votes/<uuid:nomination_id>",
        views.UnvoteView.as_view(),
        name="battle-unvote",
    ),
    path("recaps", views.RecapsView.as_view(), name="recaps"),
    path("recaps/<uuid:recap_id>/share", views.RecapShareView.as_view(), name="recap-share"),
    path("recaps/shared/<str:token>", views.SharedRecapView.as_view(), name="recap-shared"),
]
