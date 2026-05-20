from django.shortcuts import redirect

# Paths that must work without an authenticated session (login, JSON auth API, assets).
_PUBLIC_PREFIXES = (
    "/login",
    "/logout",
    "/api/auth/",
    "/admin",
    "/static",
    "/favicon.ico",
)


def _is_public_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


class SessionAuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if not _is_public_path(path) and not request.user.is_authenticated:
            return redirect("login")
        try:
            response = self.get_response(request)
        except Exception:
            raise

        return response
