from django.urls import path

from . import views

urlpatterns = [path("charts/weekly", views.WeeklyChartsView.as_view(), name="charts-weekly")]
