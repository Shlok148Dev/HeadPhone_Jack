"""Weekly charts API (JNG-15-01 Song of the Week, JNG-15-02 Artist of the Week)."""

from __future__ import annotations

from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit

from . import services


class WeeklyChartsView(APIView):
    """Top 5 songs and artists among your people this week (or ``?week=YYYY-MM-DD`` Monday)."""

    @extend_schema(tags=["charts"], parameters=[OpenApiParameter("week", str, required=False)])
    @ratelimit(key="user", rate="120/m", scope="charts.weekly")
    def get(self, request):
        ws = None
        raw = request.query_params.get("week")
        if raw:
            try:
                ws = services.week_start(date.fromisoformat(raw))
            except ValueError:
                raise ApiError(
                    "VALIDATION_ERROR", "week must be a date (YYYY-MM-DD).", 400
                ) from None
        return Response(services.weekly(request.user, ws))
