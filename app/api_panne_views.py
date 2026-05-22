import csv
import logging
from datetime import date
from io import BytesIO, StringIO

from django.db import DatabaseError
from django.db.models import Q
from django.core.paginator import Paginator
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook

from .api_utils import json_body, json_forbidden, parse_query_int
from .authz import (
    can_do_action as auth_can_do_action,
    ensure_psp_object_access,
    ensure_equipe_allowed,
    ensure_shift_allowed,
    restrict_psp_scope,
)
from .ccb_constants import CCB_MODULE_NAME
from .ccb_matrix_loader import (
    ccb_allowed_moyens_for_poste,
    ccb_moyen_sort_rank,
    ccb_poste_names_in_order,
)
from .downtime_impact import (
    berceau_alerte_impact_pct,
    production_rows_by_date_for_alertes,
    production_rows_map_for_pairs,
)
from .nro_import_utils import comment_from_imported_cause
from .panne_type_catalog import BERCEAU_PANNE_TYPE_NAMES, CCB_PANNE_TYPE_NAMES
from .models import (
    AlertePanne,
    ArretCategory,
    ArretBerceau,
    BerceauModule,
    BerceauMoyen,
    BerceauPoste,
    PanneType,
)


logger = logging.getLogger(__name__)


def _panne_types_queryset_for_equipe(equipe: str, *, active_only: bool = True):
    """Référentiel catalogue + types créés via « Ajouter type d'arrêt » (hors catalogue de l'autre UEP)."""
    queryset = PanneType.objects.all()
    if active_only:
        queryset = queryset.filter(is_active=True)
    if equipe == "CCB":
        queryset = queryset.filter(
            Q(name__in=CCB_PANNE_TYPE_NAMES) | ~Q(name__in=BERCEAU_PANNE_TYPE_NAMES)
        )
    elif equipe == "Berceau":
        queryset = queryset.filter(
            Q(name__in=BERCEAU_PANNE_TYPE_NAMES) | ~Q(name__in=CCB_PANNE_TYPE_NAMES)
        )
    return queryset


def _panne_type_is_catalog(name: str, equipe: str) -> bool:
    if equipe == "CCB":
        return name in CCB_PANNE_TYPE_NAMES
    if equipe == "Berceau":
        return name in BERCEAU_PANNE_TYPE_NAMES
    return False


def _panne_type_to_dict(item: PanneType, equipe: str = "") -> dict:
    data = model_to_dict(item, fields=["id", "name", "description", "is_active"])
    if equipe:
        data["is_catalog"] = _panne_type_is_catalog(item.name, equipe)
    return data


def _alerte_to_dict(item: AlertePanne, prod_rows: list | None = None) -> dict:
    d = {
        "id": item.id,
        "module_id": item.module_id,
        "module_nom": item.module.name,
        "poste_id": item.poste_id,
        "poste_nom": item.poste.name,
        "moyen_id": item.moyen_id,
        "moyen_nom": item.moyen.name if item.moyen_id else "",
        "panne_type_id": item.panne_type_id,
        "panne_type_nom": item.panne_type.name,
        "cause": item.cause,
        "solution": item.solution,
        "category": item.category,
        "category_label": ArretCategory(item.category).label if item.category else "",
        "date": item.date.isoformat(),
        "shift": item.shift,
        "heure_production": item.heure_production,
        "temps_arret_min": item.temps_arret_min,
        "equipe": item.equipe,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
    if (item.equipe or "").strip() == "Berceau" and prod_rows is not None:
        d["impact_pct"] = round(berceau_alerte_impact_pct(item, prod_rows), 6)
    else:
        d["impact_pct"] = None
    return d


def _production_rows_for_alerte(item: AlertePanne) -> list | None:
    if (item.equipe or "").strip() != "Berceau":
        return None
    from production.models import ProductionBerceau

    rows = list(ProductionBerceau.objects.filter(date=item.date).order_by("shift", "id"))
    return rows or []


def api_berceau_modules(request):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    # CCB is a separate UEP; its line uses /api/berceau/postes/?equipe=CCB, not this list.
    queryset = (
        BerceauModule.objects.filter(is_active=True)
        .exclude(name=CCB_MODULE_NAME)
        .order_by("name")
    )
    return JsonResponse({"results": [{"id": m.id, "name": m.name} for m in queryset]})


def api_berceau_module_postes(request, module_id):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    rows = list(BerceauPoste.objects.filter(module_id=module_id, is_active=True).select_related("module"))
    mod = BerceauModule.objects.filter(pk=module_id).first()
    if mod and mod.name == CCB_MODULE_NAME:
        rank = {n: i for i, n in enumerate(ccb_poste_names_in_order())}
        rows.sort(key=lambda p: rank.get(p.name, 999))
    else:
        rows.sort(key=lambda p: p.name)
    return JsonResponse(
        {
            "results": [
                {
                    "id": p.id,
                    "name": p.name,
                    "module_id": p.module_id,
                    "a1_enabled": p.a1_enabled,
                    "a3_enabled": p.a3_enabled,
                }
                for p in rows
            ]
        }
    )


def api_berceau_poste_moyens(request, poste_id):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    include_raw = (request.GET.get("include_moyen_id") or "").strip()
    include_pk = int(include_raw) if include_raw.isdigit() else None
    rows = list(BerceauMoyen.objects.filter(poste_id=poste_id, is_active=True))
    poste = BerceauPoste.objects.select_related("module").filter(pk=poste_id).first()
    if poste and poste.module.name == CCB_MODULE_NAME:
        rank = ccb_moyen_sort_rank(poste.name)
        rows.sort(key=lambda m: rank.get(m.name, 999))
    else:
        rows.sort(key=lambda m: m.name)
    if include_pk is not None:
        extra = (
            BerceauMoyen.objects.filter(pk=include_pk, poste_id=poste_id)
            .exclude(is_active=True)
            .first()
        )
        if extra and not any(m.id == extra.id for m in rows):
            rows = [extra] + rows
    return JsonResponse({"results": [{"id": m.id, "name": m.name, "poste_id": m.poste_id} for m in rows]})


def api_berceau_postes(request):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    equipe = (request.GET.get("equipe") or "").strip()
    queryset = BerceauPoste.objects.filter(is_active=True).select_related("module")
    if equipe == "CCB":
        queryset = queryset.filter(module__name=CCB_MODULE_NAME)
    elif equipe == "Berceau":
        queryset = queryset.exclude(module__name=CCB_MODULE_NAME)
    rows = list(queryset.order_by("module__name", "name"))
    if equipe == "CCB":
        rank = {n: i for i, n in enumerate(ccb_poste_names_in_order())}
        rows.sort(key=lambda p: rank.get(p.name, 999))
    return JsonResponse(
        {
            "results": [
                {
                    "id": p.id,
                    "name": p.name,
                    "module_id": p.module_id,
                    "module_name": p.module.name,
                    "a1_enabled": p.a1_enabled,
                    "a3_enabled": p.a3_enabled,
                }
                for p in rows
            ]
        }
    )


def api_panne_types(request):
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        q = (request.GET.get("q") or "").strip()
        equipe = (request.GET.get("equipe") or "").strip()
        queryset = _panne_types_queryset_for_equipe(equipe)
        if q:
            queryset = queryset.filter(name__icontains=q)
        include_inactive = (request.GET.get("include_inactive") or "").strip().lower() in {"1", "true", "yes"}
        if include_inactive:
            queryset = _panne_types_queryset_for_equipe(equipe, active_only=False)
            if q:
                queryset = queryset.filter(name__icontains=q)
        return JsonResponse(
            {
                "results": [
                    _panne_type_to_dict(item, equipe)
                    for item in queryset.order_by("name")
                ]
            }
        )

    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        payload = json_body(request)
        post_equipe = (request.GET.get("equipe") or payload.get("equipe") or "").strip()
        name = (payload.get("name") or "").strip()
        if not name:
            return JsonResponse({"errors": {"name": ["Ce champ est obligatoire."]}}, status=400)
        obj, created = PanneType.objects.get_or_create(
            name=name,
            defaults={
                "description": (payload.get("description") or "").strip(),
                "updated_by": request.user if request.user.is_authenticated else None,
            },
        )
        if not created:
            obj.description = (payload.get("description") or obj.description or "").strip()
            obj.is_active = True
            obj.updated_by = request.user if request.user.is_authenticated else None
            obj.save(update_fields=["description", "is_active", "updated_by", "updated_at"])
        return JsonResponse(_panne_type_to_dict(obj, post_equipe), status=201)

    return HttpResponse(status=405)


def api_panne_type_detail(request, pk):
    equipe = (request.GET.get("equipe") or "").strip()
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        item = get_object_or_404(PanneType, pk=pk)
        return JsonResponse(_panne_type_to_dict(item, equipe))

    if request.method in {"PATCH", "PUT"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        item = get_object_or_404(PanneType, pk=pk)
        payload = json_body(request)
        name = (payload.get("name") or item.name or "").strip()
        if not name:
            return JsonResponse({"errors": {"name": ["Ce champ est obligatoire."]}}, status=400)
        if PanneType.objects.filter(name__iexact=name).exclude(pk=item.pk).exists():
            return JsonResponse({"errors": {"name": ["Ce nom existe deja."]}}, status=400)
        item.name = name
        if "description" in payload:
            item.description = (payload.get("description") or "").strip()
        if "is_active" in payload:
            item.is_active = bool(payload.get("is_active"))
        item.updated_by = request.user if request.user.is_authenticated else None
        item.save(update_fields=["name", "description", "is_active", "updated_by", "updated_at"])
        return JsonResponse(_panne_type_to_dict(item, equipe))

    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        item = get_object_or_404(PanneType, pk=pk)
        is_catalog = (
            _panne_type_is_catalog(item.name, equipe)
            if equipe
            else item.name in BERCEAU_PANNE_TYPE_NAMES or item.name in CCB_PANNE_TYPE_NAMES
        )
        # Arrêts supprimés côté UI restent en base (is_deleted=True) avec FK PROTECT → pas de hard delete.
        referenced = AlertePanne.objects.filter(panne_type_id=pk).exists()
        if referenced or is_catalog:
            if item.is_active:
                item.is_active = False
                item.updated_by = request.user if request.user.is_authenticated else None
                item.save(update_fields=["is_active", "updated_by", "updated_at"])
            return JsonResponse({"id": pk, "deactivated": True})
        item.delete()
        return JsonResponse({"id": pk, "removed": True})

    return HttpResponse(status=405)


def api_arrets_temps_auto(request):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    date_val = (request.GET.get("date") or "").strip()
    shift = (request.GET.get("shift") or "").strip()
    module_id = request.GET.get("module_id")
    poste_id = request.GET.get("poste_id")
    moyen_id = request.GET.get("moyen_id")
    heure = request.GET.get("heure")
    if not (date_val and shift and module_id and poste_id and moyen_id and heure):
        return JsonResponse({"temps_arret_min": 0, "found": False})
    queryset = ArretBerceau.objects.filter(
        date=date_val,
        shift=shift,
        module_id=module_id,
        poste_id=poste_id,
        moyen_id=moyen_id,
        heure_production=heure,
    )
    queryset = restrict_psp_scope(request.user, queryset, shift_field="shift")
    total = sum(item.temps_arret_min for item in queryset)
    return JsonResponse({"temps_arret_min": total, "found": queryset.exists()})


def _normalize_optional_moyen_id(raw) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _build_alerte_from_payload(item: AlertePanne, payload: dict) -> AlertePanne:
    item.module_id = payload.get("module_id")
    item.poste_id = payload.get("poste_id")
    item.moyen_id = _normalize_optional_moyen_id(payload.get("moyen_id"))
    item.panne_type_id = payload.get("panne_type_id")
    item.cause = (payload.get("cause") or "").strip()
    item.solution = (payload.get("solution") or "").strip()
    item.category = (payload.get("category") or ArretCategory.FABRICATION).strip().lower()
    item.date = payload.get("date") or date.today()
    item.shift = (payload.get("shift") or "").strip()
    item.heure_production = payload.get("heure_production")
    item.temps_arret_min = int(payload.get("temps_arret_min") or 0)
    equipe = (payload.get("equipe") or "Berceau").strip()
    item.equipe = equipe if equipe in {"Berceau", "CCB"} else "Berceau"
    return item


def _validate_alerte_ccb_referentiel(
    payload: dict,
    *,
    patch_item: AlertePanne | None = None,
) -> tuple[bool, str | None]:
    """Poste module CCB, moyen aligné référentiel (grand-père si même moyen_id qu'à l'enregistrement)."""
    poste_id = payload.get("poste_id")
    module_id = payload.get("module_id")
    panne_type_id = payload.get("panne_type_id")
    moyen_raw = payload.get("moyen_id")
    if not poste_id:
        return False, "poste_id requis."
    if module_id is None:
        return False, "module_id requis."

    moyen_id_int = _normalize_optional_moyen_id(moyen_raw)

    poste_qs = BerceauPoste.objects.select_related("module").filter(pk=poste_id)
    if patch_item is None:
        poste = poste_qs.filter(is_active=True).first()
    else:
        poste = poste_qs.first()
    if not poste or poste.module.name != CCB_MODULE_NAME:
        return False, "Le poste doit appartenir au module CCB."
    if int(module_id) != poste.module_id:
        return False, "Le module ne correspond pas au poste selectionne."

    if moyen_id_int is not None:
        moyen = BerceauMoyen.objects.filter(pk=moyen_id_int).first()
        if not moyen:
            return False, "Moyen inconnu."
        if moyen.poste_id != int(poste_id):
            return False, "Le moyen ne correspond pas au poste selectionne."

        grandfather_moyen = patch_item is not None and patch_item.moyen_id == moyen_id_int
        if patch_item is None or not grandfather_moyen:
            if not moyen.is_active:
                return False, "Moyen inactif ou non autorise."
            allowed = ccb_allowed_moyens_for_poste(poste.name)
            if moyen.name not in allowed:
                return False, "Moyenne/module non autorise pour ce poste CCB."

    if panne_type_id:
        pt = PanneType.objects.filter(pk=panne_type_id, is_active=True).first()
        if not pt or pt.name not in CCB_PANNE_TYPE_NAMES:
            return False, "Type de panne non autorise pour CCB."
    return True, None


def _parse_heure_bounds(request):
    """Optional créneaux production 1–8: heure_from / heure_to (inclus)."""
    hf_raw = (request.GET.get("heure_from") or "").strip()
    ht_raw = (request.GET.get("heure_to") or "").strip()
    if not hf_raw and not ht_raw:
        return None, None
    hf = None
    ht = None
    if hf_raw:
        try:
            hf = int(hf_raw)
        except ValueError as exc:
            raise ValueError("heure_from invalide.") from exc
        if not 1 <= hf <= 8:
            raise ValueError("heure_from doit etre entre 1 et 8.")
    if ht_raw:
        try:
            ht = int(ht_raw)
        except ValueError as exc:
            raise ValueError("heure_to invalide.") from exc
        if not 1 <= ht <= 8:
            raise ValueError("heure_to doit etre entre 1 et 8.")
    eff_lo = hf if hf is not None else 1
    eff_hi = ht if ht is not None else 8
    if eff_lo > eff_hi:
        raise ValueError("heure_from doit etre inferieur ou egal a heure_to.")
    return hf, ht


def _filter_alertes(request):
    queryset = AlertePanne.objects.filter(is_deleted=False).select_related("module", "poste", "moyen", "panne_type")
    equipe = (request.GET.get("equipe") or "").strip()
    if equipe in {"Berceau", "CCB"}:
        queryset = queryset.filter(equipe=equipe)
    if request.GET.get("date"):
        queryset = queryset.filter(date=request.GET["date"].strip())
    if request.GET.get("shift"):
        queryset = queryset.filter(shift=request.GET["shift"].strip())
    hf, ht = _parse_heure_bounds(request)
    if hf is not None:
        queryset = queryset.filter(heure_production__gte=hf)
    if ht is not None:
        queryset = queryset.filter(heure_production__lte=ht)
    if request.GET.get("module_id"):
        queryset = queryset.filter(module_id=request.GET["module_id"].strip())
    if request.GET.get("poste_id"):
        queryset = queryset.filter(poste_id=request.GET["poste_id"].strip())
    if request.GET.get("moyen_id"):
        queryset = queryset.filter(moyen_id=request.GET["moyen_id"].strip())
    if request.GET.get("panne_type_id"):
        queryset = queryset.filter(panne_type_id=request.GET["panne_type_id"].strip())
    if request.GET.get("category"):
        queryset = queryset.filter(category=request.GET["category"].strip().lower())
    q = (request.GET.get("q") or "").strip()
    if q:
        queryset = queryset.filter(Q(cause__icontains=q) | Q(solution__icontains=q))
    queryset = restrict_psp_scope(request.user, queryset, shift_field="shift", equipe_field="equipe")
    return queryset.order_by("-date", "shift", "-created_at")


def api_alertes_pannes(request):
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        try:
            queryset = _filter_alertes(request)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        page = parse_query_int(request, "page", 1, minimum=1)
        per_page = parse_query_int(request, "per_page", 20, minimum=1, maximum=100)
        try:
            page_obj = Paginator(queryset, per_page).get_page(page)
            items = list(page_obj)
            prod_by_date = production_rows_by_date_for_alertes(items)
            results = []
            for item in items:
                pr = (
                    prod_by_date.get(item.date, [])
                    if (item.equipe or "").strip() == "Berceau"
                    else None
                )
                results.append(_alerte_to_dict(item, pr))
            return JsonResponse(
                {
                    "results": results,
                    "page": page_obj.number,
                    "pages": page_obj.paginator.num_pages,
                    "total": page_obj.paginator.count,
                }
            )
        except DatabaseError:
            logger.exception("api_alertes_pannes GET database error")
            return JsonResponse(
                {
                    "error": "Erreur base de donnees. Verifiez que les migrations sont appliquees (manage.py migrate).",
                },
                status=503,
            )

    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        payload = json_body(request)
        equipe_val = (payload.get("equipe") or "Berceau").strip()
        if equipe_val not in {"Berceau", "CCB"}:
            return JsonResponse({"errors": {"equipe": ["Equipe invalide."]}}, status=400)
        if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_alertes_pannes POST"):
            return json_forbidden()
        category = (payload.get("category") or "").strip().lower()
        if category not in {choice for choice, _ in ArretCategory.choices}:
            return JsonResponse({"errors": {"category": ["Categorie d'arret invalide."]}}, status=400)
        try:
            temps_arret_min = int(payload.get("temps_arret_min") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"errors": {"temps_arret_min": ["Le temps d'arret est obligatoire."]}}, status=400)
        if temps_arret_min <= 0:
            return JsonResponse({"errors": {"temps_arret_min": ["Le temps d'arret doit etre superieur a 0."]}}, status=400)
        payload["temps_arret_min"] = temps_arret_min
        payload["category"] = category
        shift_val = (payload.get("shift") or "").strip()
        if not ensure_shift_allowed(request.user, shift_val, endpoint="api_alertes_pannes POST"):
            return json_forbidden()
        if equipe_val == "CCB":
            if not payload.get("module_id") and payload.get("poste_id"):
                p = BerceauPoste.objects.filter(pk=payload["poste_id"], is_active=True).first()
                if p:
                    payload["module_id"] = p.module_id
            ok_ref, msg_ref = _validate_alerte_ccb_referentiel(payload, patch_item=None)
            if not ok_ref:
                return JsonResponse({"errors": {"referentiel": [msg_ref]}}, status=400)
        item = _build_alerte_from_payload(AlertePanne(), payload)
        item.updated_by = request.user if request.user.is_authenticated else None
        try:
            item.full_clean()
            item.save()
            return JsonResponse(_alerte_to_dict(item, _production_rows_for_alerte(item)), status=201)
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    return HttpResponse(status=405)


def api_alertes_pannes_detail(request, pk):
    item = get_object_or_404(
        AlertePanne.objects.select_related("module", "poste", "moyen", "panne_type"),
        pk=pk,
        is_deleted=False,
    )
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if not ensure_psp_object_access(request.user, item, endpoint="api_alertes_pannes_detail GET"):
            return json_forbidden()
        return JsonResponse(_alerte_to_dict(item, _production_rows_for_alerte(item)))

    if request.method in {"PATCH", "PUT"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if not ensure_psp_object_access(request.user, item, endpoint="api_alertes_pannes_detail PATCH"):
            return json_forbidden()
        payload = json_body(request)
        equipe_val = (payload.get("equipe") or item.equipe or "").strip()
        if equipe_val not in {"Berceau", "CCB"}:
            return JsonResponse({"errors": {"equipe": ["Equipe invalide."]}}, status=400)
        if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_alertes_pannes_detail PATCH"):
            return json_forbidden()
        category = (payload.get("category") if "category" in payload else item.category) or ""
        category = str(category).strip().lower()
        if category not in {choice for choice, _ in ArretCategory.choices}:
            return JsonResponse({"errors": {"category": ["Categorie d'arret invalide."]}}, status=400)
        try:
            temps_arret_min = int(payload.get("temps_arret_min") if "temps_arret_min" in payload else item.temps_arret_min)
        except (TypeError, ValueError):
            return JsonResponse({"errors": {"temps_arret_min": ["Le temps d'arret est obligatoire."]}}, status=400)
        if temps_arret_min <= 0:
            return JsonResponse({"errors": {"temps_arret_min": ["Le temps d'arret doit etre superieur a 0."]}}, status=400)
        payload["temps_arret_min"] = temps_arret_min
        payload["category"] = category
        shift_val = (payload.get("shift") or item.shift or "").strip()
        if not ensure_shift_allowed(request.user, shift_val, endpoint="api_alertes_pannes_detail PATCH"):
            return json_forbidden()
        if equipe_val == "CCB":
            chk = {
                "poste_id": payload.get("poste_id", item.poste_id),
                "module_id": payload.get("module_id", item.module_id),
                "panne_type_id": payload.get("panne_type_id", item.panne_type_id),
                "moyen_id": payload.get("moyen_id", item.moyen_id),
            }
            ok_ref, msg_ref = _validate_alerte_ccb_referentiel(chk, patch_item=item)
            if not ok_ref:
                return JsonResponse({"errors": {"referentiel": [msg_ref]}}, status=400)
        item = _build_alerte_from_payload(item, {**_alerte_to_dict(item), **payload})
        item.updated_by = request.user if request.user.is_authenticated else None
        try:
            item.full_clean()
            item.save()
            return JsonResponse(_alerte_to_dict(item, _production_rows_for_alerte(item)))
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        if not ensure_psp_object_access(request.user, item, endpoint="api_alertes_pannes_detail DELETE"):
            return json_forbidden()
        item.is_deleted = True
        item.updated_by = request.user if request.user.is_authenticated else None
        item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        return JsonResponse({"deleted": True})

    return HttpResponse(status=405)


def _alerte_export_commentaire(item: AlertePanne) -> str:
    """Commentaire affiché à l'export (sans tags import / diversité)."""
    solution = (item.solution or "").strip()
    if solution:
        return solution
    return comment_from_imported_cause(item.cause)


def api_alertes_pannes_export(request):
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    fmt = (request.GET.get("format") or "csv").strip().lower()
    try:
        filtered = _filter_alertes(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    rows = list(filtered[:5000])
    prod_by_date = production_rows_by_date_for_alertes(rows)
    columns = [
        "date",
        "shift",
        "heure_production",
        "module",
        "poste",
        "moyen",
        "type_panne",
        "categorie",
        "temps_arret_min",
        "impact_pct",
        "commentaire",
    ]
    data_rows = []
    for item in rows:
        berceau = (item.equipe or "").strip() == "Berceau"
        impact = (
            round(berceau_alerte_impact_pct(item, prod_by_date.get(item.date, [])), 6)
            if berceau
            else ""
        )
        data_rows.append(
            [
                item.date.isoformat(),
                item.shift,
                item.heure_production,
                item.module.name,
                item.poste.name,
                item.moyen.name if item.moyen_id else "",
                item.panne_type.name,
                ArretCategory(item.category).label if item.category else "",
                item.temps_arret_min,
                impact,
                _alerte_export_commentaire(item),
            ]
        )
    if fmt == "excel":
        wb = Workbook()
        ws = wb.active
        ws.title = "Alertes Pannes"
        ws.append(columns)
        for row in data_rows:
            ws.append(row)
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        equipe = (request.GET.get("equipe") or "berceau").strip().lower()
        if equipe not in {"berceau", "ccb"}:
            equipe = "berceau"
        response["Content-Disposition"] = f'attachment; filename="alertes_pannes_{equipe}.xlsx"'
        return response

    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(columns)
    writer.writerows(data_rows)
    response = HttpResponse(sio.getvalue(), content_type="text/csv; charset=utf-8")
    equipe = (request.GET.get("equipe") or "berceau").strip().lower()
    if equipe not in {"berceau", "ccb"}:
        equipe = "berceau"
    response["Content-Disposition"] = f'attachment; filename="alertes_pannes_{equipe}.csv"'
    return response
