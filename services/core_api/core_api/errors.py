"""Error envelope (CONTRACTS.md §8): {"error": {"code", "message", "details", "request_id"}}."""

from rest_framework import exceptions, status
from rest_framework.views import exception_handler as drf_handler


class ApiError(exceptions.APIException):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(detail=message, code=code)


_DEFAULT_CODES = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is None:
        return None
    request = context.get("request")
    rid = getattr(request, "request_id", None) if request else None
    if isinstance(exc, ApiError):
        code, message, details = exc.code, exc.message, exc.details
    else:
        code = _DEFAULT_CODES.get(response.status_code, "ERROR")
        data = response.data
        if isinstance(data, dict) and set(data) == {"detail"}:
            message, details = str(data["detail"]), {}
        else:
            message, details = "Please check the highlighted fields.", data
    response.data = {"error": {"code": code, "message": message, "details": details, "request_id": rid}}
    return response
