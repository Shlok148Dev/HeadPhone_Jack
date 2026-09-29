"""Cursor pagination (CONTRACTS.md §8): ``?cursor=&limit=`` (≤ 100) → ``{results, next_cursor}``."""

from urllib.parse import parse_qs, urlparse

from rest_framework import pagination
from rest_framework.response import Response


class CursorPagination(pagination.CursorPagination):
    page_size = 20
    max_page_size = 100
    page_size_query_param = "limit"
    ordering = "-created_at"

    def get_next_cursor(self) -> str | None:
        link = self.get_next_link()
        if not link:
            return None
        values = parse_qs(urlparse(link).query).get(self.cursor_query_param)
        return values[0] if values else None

    def get_paginated_response(self, data):
        return Response({"results": data, "next_cursor": self.get_next_cursor()})

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["results", "next_cursor"],
            "properties": {
                "results": schema,
                "next_cursor": {"type": ["string", "null"]},
            },
        }
