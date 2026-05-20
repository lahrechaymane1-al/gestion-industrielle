"""Serve the React SPA shell and resolve Vite build manifest assets."""
import json
from pathlib import Path

from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.views.decorators.cache import never_cache


def _manifest_entry(data: dict):
    """Pick the Vite rollup entry from manifest.json (format varies by Vite version)."""
    entry = data.get("index.html") or data.get("src/main.tsx")
    if entry:
        return entry
    for val in data.values():
        if isinstance(val, dict) and val.get("isEntry"):
            return val
    return None


@never_cache
def react_app(request, path=""):
    """Shell for React Router (client-side routes under /app/*)."""
    ctx = {
        "csrf_token": get_token(request),
        "vite_js": None,
        "vite_css": [],
        "vite_cache_bust": "0",
    }
    frontend_dist_dir = Path(settings.BASE_DIR) / "frontend" / "dist"
    manifest_path = frontend_dist_dir / "manifest.json"
    mtimes: list[float] = []
    if manifest_path.is_file():
        try:
            mtimes.append(manifest_path.stat().st_mtime)
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = _manifest_entry(data)
            if entry:
                js_file = entry.get("file")
                if js_file:
                    rel = js_file if js_file.startswith("frontend/") else f"frontend/{js_file}"
                    ctx["vite_js"] = rel
                    js_path = frontend_dist_dir / rel
                    if js_path.is_file():
                        mtimes.append(js_path.stat().st_mtime)
                css_files = entry.get("css") or []
                ctx["vite_css"] = [
                    c if c.startswith("frontend/") else f"frontend/{c}" for c in css_files
                ]
                for c in ctx["vite_css"]:
                    css_path = frontend_dist_dir / c
                    if css_path.is_file():
                        mtimes.append(css_path.stat().st_mtime)
        except (json.JSONDecodeError, OSError):
            pass
    if mtimes:
        ctx["vite_cache_bust"] = str(int(max(mtimes)))
    return render(request, "app/react_app.html", ctx)
