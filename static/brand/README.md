# Brand assets (deploy)

## Stellantis logo

| File | Used by |
|------|---------|
| `stellantis-logo.png` | Django login (`{% static 'brand/stellantis-logo.png' %}`) |
| `frontend/public/brand/stellantis-logo.png` | React sidebar (same image; copied here for Vite) |

Keep **both** copies in sync when replacing the file.

## Deploy checklist

1. **Commit** `static/brand/stellantis-logo.png` and `frontend/public/brand/stellantis-logo.png`.
2. **Build frontend** (from repo root or `frontend/`):
   ```bash
   npm run build --workspace gestion-industrielle-ui
   ```
   Vite copies `public/brand/` into `frontend/dist/brand/`. Django serves that tree via `STATICFILES_DIRS` → `frontend/dist`.
3. **No extra `collectstatic` step** is required if you deploy with `STATICFILES_DIRS` including `frontend/dist` (default in `core/settings.py`).
4. **Verify after deploy**
   - Login: logo visible on `/login/`
   - App: logo in sidebar at `/` or `/berceau/...` (URL like `/static/brand/stellantis-logo.png` in production)
5. **Dev (Vite + Django)**  
   - Login uses Django static → `static/brand/`.  
   - React dev server uses `/brand/stellantis-logo.png` (proxied or direct on port 5173).

## Replace the logo

Use an approved Stellantis asset (PNG/SVG). **Prefer a transparent background** (no white or black box) for the cleanest result on the dark UI.

The app uses `mix-blend-mode: screen` so a black-backed PNG still blends into dark panels; a transparent PNG looks best without CSS blending.

Update both paths above, rebuild the frontend, redeploy.
