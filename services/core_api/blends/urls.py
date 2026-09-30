from django.urls import path

from . import views

urlpatterns = [
    path("blends", views.BlendsView.as_view(), name="blends"),
    path("blends/<uuid:blend_id>", views.BlendDetailView.as_view(), name="blend"),
    path(
        "blends/<uuid:blend_id>/regenerate", views.RegenerateView.as_view(), name="blend-regenerate"
    ),
    path(
        "blends/<uuid:blend_id>/tracks/<int:track_id>/pin",
        views.PinView.as_view(),
        name="blend-pin",
    ),
]
