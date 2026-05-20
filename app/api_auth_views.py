"""Session-based auth endpoints for SPA (identifiant + code)."""

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .authz import serialize_me
from .api_utils import json_body


@require_http_methods(["POST"])
def api_auth_login(request):
    data = json_body(request)
    identifiant = (data.get("identifiant") or "").strip()
    code = (data.get("code") or "").strip()
    user = authenticate(request, username=identifiant, password=code)
    if user is None:
        return JsonResponse({"detail": "Identifiants invalides."}, status=401)
    login(request, user)
    out = serialize_me(user)
    out["authenticated"] = True
    return JsonResponse(out)


@require_http_methods(["POST"])
def api_auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def api_auth_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)
    out = serialize_me(request.user)
    out["authenticated"] = True
    return JsonResponse(out)
