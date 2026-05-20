"""Small shared helpers for JSON FBV endpoints (avoid duplication)."""

from __future__ import annotations

import json
from typing import Any

from django.http import JsonResponse


def json_body(request) -> dict[str, Any]:
    """Parse request.body as JSON and always return a dict."""
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def json_forbidden(message: str = "Acces refuse.") -> JsonResponse:
    return JsonResponse({"error": message}, status=403)


def parse_query_int(
    request,
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse a non-negative integer from GET; safe for pagination (no ValueError)."""
    raw = request.GET.get(key)
    try:
        value = int(raw) if raw is not None and str(raw).strip() != "" else int(default)
    except (TypeError, ValueError):
        value = int(default)
    if minimum is not None and value < minimum:
        value = minimum
    if maximum is not None and value > maximum:
        value = maximum
    return value

