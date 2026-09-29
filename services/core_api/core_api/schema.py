"""Shared OpenAPI components (drf-spectacular)."""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()
    request_id = serializers.CharField(allow_null=True)


class ErrorEnvelopeSerializer(serializers.Serializer):
    """CONTRACTS.md §8 error envelope."""

    error = ErrorBodySerializer()


def err(description: str) -> OpenApiResponse:
    return OpenApiResponse(ErrorEnvelopeSerializer, description=description)
