import uuid
from datetime import UTC

from django.utils import timezone
from jingle_common.logging import request_id_var


class RequestIdMiddleware:
    """Accept or create X-Request-ID; expose it to logs and echo it on the response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = rid
        return response


class UTCMiddleware:
    """Payload timestamps are ISO-8601 UTC (Technical Bible 4.1); clients render local time."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(UTC)
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
