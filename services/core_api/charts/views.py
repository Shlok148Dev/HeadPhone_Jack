"""Weekly charts API (JNG-15-01 songs, JNG-15-02 artists, JNG-15-03 Monday reveal)."""

from __future__ import annotations

from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit

from . import services


def _week(raw: str) -> date:
    try:
        return services.week_start(date.fromisoformat(raw))
    except ValueError:
        raise ApiError("VALIDATION_ERROR", "week must be a date (YYYY-MM-DD).", 400) from None


class WeeklyChartsView(APIView):
    """This week's top 5 among your people, plus last week's frozen chart and its reveal state.
    ``?week=YYYY-MM-DD`` returns one specific week instead."""

    @extend_schema(tags=["charts"], parameters=[OpenApiParameter("week", str, required=False)])
    @ratelimit(key="user", rate="120/m", scope="charts.weekly")
    def get(self, request):
        raw = request.query_params.get("week")
        if raw:
            return Response(services.weekly(request.user, _week(raw)))
        return Response(services.with_last_final(request.user))


class ChartSeenView(APIView):
    """The Home reveal of a frozen week was shown: it plays once per week, on any device."""

    @extend_schema(tags=["charts"], request=None, responses={204: None})
    def post(self, request, week: str):
        services.mark_seen(request.user, _week(week))
        return Response(status=204)
