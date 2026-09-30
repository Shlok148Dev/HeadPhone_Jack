from django.urls import path

from . import views

urlpatterns = [
    path("suggestions", views.SuggestionsView.as_view(), name="suggestions"),
    path(
        "suggestions/<uuid:user_id>/dismiss", views.DismissView.as_view(), name="suggestion-dismiss"
    ),
    path("me/taste", views.TasteView.as_view(), name="my-taste"),
]
