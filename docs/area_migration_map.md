# Migration map (progressive)

## Legacy -> New area wrappers

- `app.views.berceau_production_list` -> `areas/berceau/views.py::production_list`
- `app.views.berceau_production_add` -> `areas/berceau/views.py::production_add`
- `app.views.berceau_production_edit` -> `areas/berceau/views.py::production_edit`
- `app.views.berceau_production_detail` -> `areas/berceau/views.py::production_detail`
- `app.views.berceau_production_delete` -> `areas/berceau/views.py::production_delete`
- `app.views.berceau_mode_degrade` -> `areas/berceau/views.py::mode_degrade`
- `app.views.berceau_absence` -> `areas/berceau/views.py::absence`
- `app.views.berceau_effectif` -> `areas/berceau/views.py::effectif`
- `app.views.berceau_stock` -> `areas/berceau/views.py::stock`
- `app.views.berceau_arret` -> `areas/berceau/views.py::arret`

- `app.views.ccb_production` -> `areas/ccb/views.py::production_list`
- `app.views.ccb_production_add` -> `areas/ccb/views.py::production_add`
- `app.views.ccb_production_edit` -> `areas/ccb/views.py::production_edit`
- `app.views.ccb_production_detail` -> `areas/ccb/views.py::production_detail`
- `app.views.ccb_production_delete` -> `areas/ccb/views.py::production_delete`
- `app.views.ccb_mode_degrade` -> `areas/ccb/views.py::mode_degrade`
- `app.views.ccb_absence` -> `areas/ccb/views.py::absence`
- `app.views.ccb_effectif` -> `areas/ccb/views.py::effectif`
- `app.views.ccb_stock` -> `areas/ccb/views.py::stock`
- `app.views.ccb_arret` -> `areas/ccb/views.py::arret`

## Shared extraction (first pass)

- `app.authz.*` -> `shared/rbac.py` (re-export)
- common effectif selector -> `shared/selectors.py`
- common session payload service -> `shared/services.py`

## Django apps (zone-based)

- `areas/berceau` is now a dedicated Django app (`areas.berceau.apps.BerceauAreaConfig`).
- `areas/ccb` is now a dedicated Django app (`areas.ccb.apps.CcbAreaConfig`).
- `shared` is now a dedicated shared app (`shared.apps.SharedCoreConfig`).
- `industrial_management/settings.py` now registers these apps in `INSTALLED_APPS`.

## Target template/static layout

- Berceau templates target: `templates/areas/berceau/*`
- CCB templates target: `templates/areas/ccb/*`
- Static target folders:
  - `static/react/*`
  - `static/css/*`
  - `static/assets/*`
  - `static/images/*`

## Remaining migration (next phases)

1. Move Berceau API endpoints from `app/views.py` and `app/api_production_views.py` into `areas/berceau/views.py` + `services.py` + `selectors.py`.
2. Move CCB API endpoints into `areas/ccb/*`.
3. Replace wrappers with native area implementations.
4. Split templates into `templates/areas/berceau/*` and `templates/areas/ccb/*` then switch render paths.
5. Move tests into area-scoped modules:
   - `areas/berceau/tests/*`
   - `areas/ccb/tests/*`
   - `shared/tests/*`

