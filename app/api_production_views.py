"""JSON API for Production Berceau / CCB (React SPA)."""
from datetime import date as date_type

from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Q, Sum
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from .authz import (
    can_do_action as auth_can_do_action,
    ensure_psp_object_access,
    ensure_shift_allowed,
    get_psp_equipe,
    is_admin_or_ru,
    is_psp,
    restrict_psp_scope,
)
from .api_panne_views import _parse_heure_bounds
from .api_utils import json_body, json_forbidden, parse_query_int
from .ccb_constants import CCB_OBJECTIFS_HORAIRES
from .forms import ProductionBerceauForm, ProductionCCBForm
from .models import AlertePanne, ArretBerceau, ProductionBerceau, ProductionCCB
from production.models import (
    BERCEAU_OBJECTIF_FIELD_NAMES,
    DEFAULT_DIVISOR_A1,
    DEFAULT_DIVISOR_A3,
    BerceauImpactSettings,
    BerceauObjectifSettings,
    BerceauProductionSettings,
)
from production_ccb.models import CcbProductionSettings, ccb_default_objectifs_horaires

logger = __import__("logging").getLogger(__name__)


def _berceau_effective_objectif_volume(row: ProductionBerceau) -> tuple[int, int]:
    """Objectif / volume alignés sur les champs horaires si renseignés (sinon champs agrégés)."""
    ho = sum(int(getattr(row, f"objectif_h{h}", 0) or 0) for h in range(1, 9))
    hv = sum(int(getattr(row, f"production_h{h}", 0) or 0) for h in range(1, 9))
    o = ho if ho > 0 else int(row.objectif or 0)
    v = hv if hv > 0 else int(row.volume or 0)
    return o, v


def filter_production_berceau_by_diversite(queryset, line: str):
    """Fiches dont la diversité globale OU au moins une heure correspond à A1/A3."""
    if line not in {"A1", "A3"}:
        return queryset
    q = Q(line=line)
    for hour in range(1, 9):
        q |= Q(**{f"line_h{hour}": line})
    return queryset.filter(q)


def _strip_production_arret_inputs(payload: dict) -> dict:
    data = dict(payload or {})
    data["temps_arrets"] = 0
    for hour in range(1, 9):
        data[f"temps_arrets_h{hour}"] = 0
    return data


def _berceau_to_dict(obj: ProductionBerceau) -> dict:
    live_arrets = obj.compute_hourly_arrets_from_sources()
    d = model_to_dict(
        obj,
        fields=[
            "id",
            "line",
            "date",
            "shift",
            "objectif",
            "objectif_h1",
            "objectif_h2",
            "objectif_h3",
            "objectif_h4",
            "objectif_h5",
            "objectif_h6",
            "objectif_h7",
            "objectif_h8",
            "line_h1",
            "line_h2",
            "line_h3",
            "line_h4",
            "line_h5",
            "line_h6",
            "line_h7",
            "line_h8",
            "production_h1",
            "production_h2",
            "production_h3",
            "production_h4",
            "production_h5",
            "production_h6",
            "production_h7",
            "production_h8",
            "rebut_h1",
            "rebut_h2",
            "rebut_h3",
            "rebut_h4",
            "rebut_h5",
            "rebut_h6",
            "rebut_h7",
            "rebut_h8",
            "retouche_h1",
            "retouche_h2",
            "retouche_h3",
            "retouche_h4",
            "retouche_h5",
            "retouche_h6",
            "retouche_h7",
            "retouche_h8",
            "temps_arrets_h1",
            "temps_arrets_h2",
            "temps_arrets_h3",
            "temps_arrets_h4",
            "temps_arrets_h5",
            "temps_arrets_h6",
            "temps_arrets_h7",
            "temps_arrets_h8",
            "volume",
            "rebut",
            "retouche",
            "temps_arrets",
            "validated_hours_mask",
        ],
    )
    d["date"] = obj.date.isoformat() if obj.date else None
    for hour in range(1, 9):
        d[f"temps_arrets_h{hour}"] = live_arrets.get(hour, 0)
    d["temps_arrets"] = sum(live_arrets.values())
    o_eff, v_eff = _berceau_effective_objectif_volume(obj)
    d["ro_percent"] = round((v_eff / o_eff) * 100, 2) if o_eff > 0 else 0
    d["nro_total"] = max(o_eff - v_eff, 0)
    d["validated_hours"] = obj.validated_hours
    d["arrets_source"] = "arret_module"
    return d


def _ccb_to_dict(obj: ProductionCCB) -> dict:
    d = model_to_dict(
        obj,
        fields=[
            "id",
            "date",
            "shift",
            "line",
            "objectif",
            "objectif_h1",
            "objectif_h2",
            "objectif_h3",
            "objectif_h4",
            "objectif_h5",
            "objectif_h6",
            "objectif_h7",
            "objectif_h8",
            "production_h1",
            "production_h2",
            "production_h3",
            "production_h4",
            "production_h5",
            "production_h6",
            "production_h7",
            "production_h8",
            "production_lhd_h1",
            "production_lhd_h2",
            "production_lhd_h3",
            "production_lhd_h4",
            "production_lhd_h5",
            "production_lhd_h6",
            "production_lhd_h7",
            "production_lhd_h8",
            "production_rhd_h1",
            "production_rhd_h2",
            "production_rhd_h3",
            "production_rhd_h4",
            "production_rhd_h5",
            "production_rhd_h6",
            "production_rhd_h7",
            "production_rhd_h8",
            "rebut_h1",
            "rebut_h2",
            "rebut_h3",
            "rebut_h4",
            "rebut_h5",
            "rebut_h6",
            "rebut_h7",
            "rebut_h8",
            "volume",
            "rebut",
            "retouche",
        ],
    )
    d["date"] = obj.date.isoformat() if obj.date else None
    d["ro_percent"] = obj.ro_percent
    d["temps_arrets"] = obj.compute_temps_arrets_from_alertes()
    defaults = ccb_default_objectifs_horaires()
    for h in range(1, 9):
        stored = int(getattr(obj, f"objectif_h{h}", 0) or 0)
        d[f"objectif_h{h}"] = stored if stored > 0 else int(defaults[h - 1])
    by_h = obj.temps_arrets_by_hour()
    for h in range(1, 9):
        d[f"temps_arrets_h{h}"] = by_h.get(h, 0)
    return d


def _psp_locked_hour_edit_attempt(request, obj: ProductionBerceau, payload: dict) -> bool:
    """Hourly validation lock disabled — all roles can PATCH hourly fields freely."""
    return False


def api_production_berceau(request):
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            queryset = ProductionBerceau.objects.none()
        else:
            queryset = ProductionBerceau.objects.all()
            queryset = restrict_psp_scope(request.user, queryset, shift_field="shift")
        line = (request.GET.get("line") or "").strip()
        queryset = filter_production_berceau_by_diversite(queryset, line)
        date_val = (request.GET.get("date") or "").strip()
        if date_val:
            queryset = queryset.filter(date=date_val)
        shift = (request.GET.get("shift") or "").strip()
        if shift in {"A", "B", "N"}:
            queryset = queryset.filter(shift=shift)
        q = (request.GET.get("q") or "").strip()
        if q:
            queryset = queryset.filter(Q(line__icontains=q))
        sort = request.GET.get("sort", "-date")
        allowed = {"date", "-date", "line", "-line", "shift", "-shift"}
        if sort not in allowed:
            sort = "-date"
        queryset = queryset.order_by(sort)
        page = parse_query_int(request, "page", 1, minimum=1)
        per_page = parse_query_int(request, "per_page", 20, minimum=1, maximum=100)
        try:
            page_obj = Paginator(queryset, per_page).get_page(page)
            results = [_berceau_to_dict(item) for item in page_obj]
        except DatabaseError:
            logger.exception("api_production_berceau GET database error")
            return JsonResponse(
                {
                    "error": "Erreur base de donnees. Verifiez que les migrations sont appliquees (manage.py migrate).",
                },
                status=503,
            )
        return JsonResponse(
            {
                "results": results,
                "page": page_obj.number,
                "pages": page_obj.paginator.num_pages,
                "total": page_obj.paginator.count,
            }
        )
    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        payload = _strip_production_arret_inputs(json_body(request))
        shift_val = (payload.get("shift") or "").strip()
        if shift_val in {"A", "B", "N"}:
            if not ensure_shift_allowed(request.user, shift_val, endpoint="api_production_berceau POST"):
                return json_forbidden()
        form = ProductionBerceauForm(payload)
        if form.is_valid():
            obj = form.save()
            return JsonResponse(_berceau_to_dict(obj), status=201)
        return JsonResponse({"errors": form.errors}, status=400)
    return HttpResponse(status=405)


def api_production_berceau_detail(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_berceau_detail GET"):
            return json_forbidden()
        return JsonResponse(_berceau_to_dict(obj))
    if request.method in {"PUT", "PATCH"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_berceau_detail PATCH"):
            return json_forbidden()
        data = _strip_production_arret_inputs(json_body(request))
        shift_val = (data.get("shift") or obj.shift or "").strip()
        if shift_val in {"A", "B", "N"}:
            if not ensure_shift_allowed(request.user, shift_val, endpoint="api_production_berceau_detail PATCH"):
                return json_forbidden()
        if _psp_locked_hour_edit_attempt(request, obj, data):
            return JsonResponse(
                {"error": "Une heure validee ne peut pas etre modifiee par un profil PSP."},
                status=403,
            )
        form = ProductionBerceauForm(data, instance=obj)
        if form.is_valid():
            saved = form.save()
            return JsonResponse(_berceau_to_dict(saved))
        return JsonResponse({"errors": form.errors}, status=400)
    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_berceau_detail DELETE"):
            return json_forbidden()
        obj.delete()
        return JsonResponse({"deleted": True})
    return HttpResponse(status=405)


def api_production_berceau_validate_hour(request, pk):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not auth_can_do_action(request.user, "update"):
        return json_forbidden()
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
        return json_forbidden()
    if not ensure_psp_object_access(request.user, obj, endpoint="api_production_berceau_validate_hour"):
        return json_forbidden()
    payload = json_body(request)
    try:
        hour = int(payload.get("hour"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Le champ hour est obligatoire (1..8)."}, status=400)
    if hour < 1 or hour > 8:
        return JsonResponse({"error": "Le champ hour doit etre compris entre 1 et 8."}, status=400)
    if hour > 1 and not obj.is_hour_validated(hour - 1):
        return JsonResponse({"error": "Validation sequentielle requise (Hx-1 doit etre validee)."}, status=400)
    if obj.is_hour_validated(hour):
        return JsonResponse({"ok": True, "already_validated": True, "validated_hours": obj.validated_hours})
    obj.validate_hour(hour)
    obj.save(update_fields=["validated_hours_mask"])
    return JsonResponse({"ok": True, "validated_hours": obj.validated_hours, "validated_hours_mask": obj.validated_hours_mask})


def _berceau_impact_settings_to_dict(obj: BerceauImpactSettings) -> dict:
    return {
        "id": obj.pk,
        "effective_from": obj.effective_from.isoformat(),
        "divisor_a1": float(obj.divisor_a1),
        "divisor_a3": float(obj.divisor_a3),
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


def api_berceau_impact_settings(request):
    """Référentiel versionné temps de cycle (diviseurs impact A1/A3)."""
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        try:
            versions = list(BerceauImpactSettings.objects.order_by("-effective_from", "-id"))
        except DatabaseError:
            logger.exception("api_berceau_impact_settings GET database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate production."},
                status=503,
            )
        date_param = (request.GET.get("date") or "").strip()
        payload: dict = {
            "versions": [_berceau_impact_settings_to_dict(v) for v in versions],
        }
        if date_param:
            try:
                d = date_type.fromisoformat(date_param)
            except ValueError:
                return JsonResponse({"error": "Date invalide (YYYY-MM-DD)."}, status=400)
            resolved = BerceauImpactSettings.get_for_date(d)
            for_date = {
                "date": date_param,
                "effective_from": resolved.effective_from.isoformat(),
                "divisor_a1": float(resolved.divisor_a1),
                "divisor_a3": float(resolved.divisor_a3),
            }
            if resolved.pk:
                for_date["id"] = resolved.pk
            payload["for_date"] = for_date
        return JsonResponse(payload)
    if request.method == "POST":
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if is_psp(request.user):
            return json_forbidden()
        payload = json_body(request)
        effective_raw = (payload.get("effective_from") or "").strip()
        if not effective_raw:
            return JsonResponse({"error": "effective_from est obligatoire (YYYY-MM-DD)."}, status=400)
        try:
            effective_from = date_type.fromisoformat(effective_raw)
        except ValueError:
            return JsonResponse({"error": "effective_from invalide."}, status=400)
        try:
            divisor_a1 = float(payload.get("divisor_a1", DEFAULT_DIVISOR_A1))
            divisor_a3 = float(payload.get("divisor_a3", DEFAULT_DIVISOR_A3))
        except (TypeError, ValueError):
            return JsonResponse({"error": "divisor_a1 et divisor_a3 doivent etre numeriques."}, status=400)
        if divisor_a1 <= 0 or divisor_a3 <= 0:
            return JsonResponse({"error": "Les diviseurs doivent etre strictement positifs."}, status=400)
        try:
            obj = BerceauImpactSettings.objects.create(
                effective_from=effective_from,
                divisor_a1=divisor_a1,
                divisor_a3=divisor_a3,
            )
        except DatabaseError:
            logger.exception("api_berceau_impact_settings POST database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate production."},
                status=503,
            )
        return JsonResponse(_berceau_impact_settings_to_dict(obj), status=201)
    return HttpResponse(status=405)


def _berceau_objectif_settings_to_dict(obj: BerceauObjectifSettings) -> dict:
    d: dict = {
        "effective_from": obj.effective_from.isoformat(),
        "objectif_total_a1": obj.objectif_total_for_line("A1"),
        "objectif_total_a3": obj.objectif_total_for_line("A3"),
    }
    if obj.pk:
        d["id"] = obj.pk
    for key in BERCEAU_OBJECTIF_FIELD_NAMES:
        d[key] = int(getattr(obj, key, 0) or 0)
    return d


def _upsert_berceau_objectif_settings(
    source: BerceauProductionSettings,
    effective_from: date_type,
) -> BerceauObjectifSettings:
    existing = BerceauObjectifSettings.objects.filter(effective_from=effective_from).order_by("-id").first()
    values = {key: int(getattr(source, key, 0) or 0) for key in BERCEAU_OBJECTIF_FIELD_NAMES}
    if existing:
        for key, val in values.items():
            setattr(existing, key, val)
        existing.save()
        return existing
    return BerceauObjectifSettings.objects.create(effective_from=effective_from, **values)


def _berceau_production_settings_to_dict(
    obj: BerceauProductionSettings,
    *,
    as_of: date_type | None = None,
    include_versions: bool = False,
) -> dict:
    target = as_of or date_type.today()
    # Sans ?date= : objectifs du singleton (fiche en cours). Avec ?date= : version en vigueur ce jour-là.
    if as_of is not None:
        objectifs = BerceauObjectifSettings.get_for_date(as_of)
        objectif_effective_from = objectifs.effective_from.isoformat()
        objectif_version_id = objectifs.pk
    else:
        objectifs = obj
        resolved = BerceauObjectifSettings.get_for_date(target)
        objectif_effective_from = resolved.effective_from.isoformat()
        objectif_version_id = resolved.pk
    impact = BerceauImpactSettings.get_for_date(target)
    d: dict = {
        "objectif_a1_h1": objectifs.objectif_a1_h1,
        "objectif_a1_h2": objectifs.objectif_a1_h2,
        "objectif_a1_h3": objectifs.objectif_a1_h3,
        "objectif_a1_h4": objectifs.objectif_a1_h4,
        "objectif_a1_h5": objectifs.objectif_a1_h5,
        "objectif_a1_h6": objectifs.objectif_a1_h6,
        "objectif_a1_h7": objectifs.objectif_a1_h7,
        "objectif_a1_h8": objectifs.objectif_a1_h8,
        "objectif_a3_h1": objectifs.objectif_a3_h1,
        "objectif_a3_h2": objectifs.objectif_a3_h2,
        "objectif_a3_h3": objectifs.objectif_a3_h3,
        "objectif_a3_h4": objectifs.objectif_a3_h4,
        "objectif_a3_h5": objectifs.objectif_a3_h5,
        "objectif_a3_h6": objectifs.objectif_a3_h6,
        "objectif_a3_h7": objectifs.objectif_a3_h7,
        "objectif_a3_h8": objectifs.objectif_a3_h8,
        "objectif_total_a1": objectifs.objectif_total_for_line("A1"),
        "objectif_total_a3": objectifs.objectif_total_for_line("A3"),
        "objectif_effective_from": objectif_effective_from,
        "objectif_resolved_for": target.isoformat(),
        "divisor_a1": float(impact.divisor_a1),
        "divisor_a3": float(impact.divisor_a3),
        "divisor_effective_from": impact.effective_from.isoformat(),
        "divisor_resolved_for": target.isoformat(),
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }
    if objectif_version_id:
        d["objectif_version_id"] = objectif_version_id
    if impact.pk:
        d["divisor_version_id"] = impact.pk
    if include_versions:
        impact_versions = list(BerceauImpactSettings.objects.order_by("-effective_from", "-id"))
        d["impact_versions"] = [_berceau_impact_settings_to_dict(v) for v in impact_versions]
        objectif_versions = list(BerceauObjectifSettings.objects.order_by("-effective_from", "-id"))
        d["objectif_versions"] = [_berceau_objectif_settings_to_dict(v) for v in objectif_versions]
    return d


def _upsert_berceau_impact_divisors(divisor_a1: float, divisor_a3: float, effective_from: date_type) -> BerceauImpactSettings:
    existing = BerceauImpactSettings.objects.filter(effective_from=effective_from).order_by("-id").first()
    if existing:
        existing.divisor_a1 = divisor_a1
        existing.divisor_a3 = divisor_a3
        existing.save(update_fields=["divisor_a1", "divisor_a3", "updated_at"])
        return existing
    return BerceauImpactSettings.objects.create(
        effective_from=effective_from,
        divisor_a1=divisor_a1,
        divisor_a3=divisor_a3,
    )


def api_berceau_production_settings(request):
    """Référentiel Berceau : objectifs horaires A1/A3 + temps de cycle (diviseurs impact)."""
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "Berceau":
            return json_forbidden()
        try:
            obj = BerceauProductionSettings.get_singleton()
        except DatabaseError:
            logger.exception("api_berceau_production_settings GET database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate production."},
                status=503,
            )
        date_param = (request.GET.get("date") or "").strip()
        as_of: date_type | None = None
        if date_param:
            try:
                as_of = date_type.fromisoformat(date_param)
            except ValueError:
                return JsonResponse({"error": "Date invalide (YYYY-MM-DD)."}, status=400)
        return JsonResponse(
            _berceau_production_settings_to_dict(
                obj,
                as_of=as_of,
                include_versions=not date_param,
            )
        )
    if request.method in {"PUT", "PATCH"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if is_psp(request.user):
            return json_forbidden()
        payload = json_body(request)
        try:
            obj = BerceauProductionSettings.get_singleton()
        except DatabaseError:
            logger.exception("api_berceau_production_settings PATCH database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate production."},
                status=503,
            )
        errors: dict[str, list[str]] = {}
        for line in ("a1", "a3"):
            for h in range(1, 9):
                key = f"objectif_{line}_h{h}"
                if key not in payload:
                    continue
                try:
                    val = int(payload[key])
                except (TypeError, ValueError):
                    errors[key] = ["Valeur entière attendue."]
                    continue
                if val < 0:
                    errors[key] = ["Doit être >= 0."]
                    continue
                setattr(obj, key, val)
        divisor_touched = "divisor_a1" in payload or "divisor_a3" in payload
        new_divisor_a1: float | None = None
        new_divisor_a3: float | None = None
        if divisor_touched:
            today = date_type.today()
            current = BerceauImpactSettings.get_for_date(today)
            try:
                new_divisor_a1 = float(payload.get("divisor_a1", current.divisor_a1))
                new_divisor_a3 = float(payload.get("divisor_a3", current.divisor_a3))
            except (TypeError, ValueError):
                errors["divisor"] = ["divisor_a1 et divisor_a3 doivent être numériques."]
            else:
                if new_divisor_a1 <= 0 or new_divisor_a3 <= 0:
                    errors["divisor"] = ["Les temps de cycle doivent être strictement positifs."]
        if errors:
            return JsonResponse({"errors": errors}, status=400)
        objectif_touched = any(key in payload for key in BERCEAU_OBJECTIF_FIELD_NAMES)
        obj.save()
        today = date_type.today()
        if objectif_touched:
            _upsert_berceau_objectif_settings(obj, today)
        if divisor_touched and new_divisor_a1 is not None and new_divisor_a3 is not None:
            current = BerceauImpactSettings.get_for_date(today)
            changed = (
                abs(new_divisor_a1 - float(current.divisor_a1)) > 1e-9
                or abs(new_divisor_a3 - float(current.divisor_a3)) > 1e-9
            )
            if changed:
                _upsert_berceau_impact_divisors(new_divisor_a1, new_divisor_a3, today)
        return JsonResponse(_berceau_production_settings_to_dict(obj, include_versions=True))
    return HttpResponse(status=405)


def _ccb_settings_to_dict(obj: CcbProductionSettings) -> dict:
    d = {
        "objectif_h1": obj.objectif_h1,
        "objectif_h2": obj.objectif_h2,
        "objectif_h3": obj.objectif_h3,
        "objectif_h4": obj.objectif_h4,
        "objectif_h5": obj.objectif_h5,
        "objectif_h6": obj.objectif_h6,
        "objectif_h7": obj.objectif_h7,
        "objectif_h8": obj.objectif_h8,
        "objectif_total": obj.objectif_total(),
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }
    return d


def api_ccb_production_settings(request):
    """Objectifs horaires par défaut CCB (singleton, toutes dates / shifts)."""
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        try:
            obj = CcbProductionSettings.get_singleton()
        except DatabaseError:
            logger.exception("api_ccb_production_settings GET database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate (production_ccb)."},
                status=503,
            )
        return JsonResponse(_ccb_settings_to_dict(obj))
    if request.method in {"PUT", "PATCH"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        payload = json_body(request)
        try:
            obj = CcbProductionSettings.get_singleton()
        except DatabaseError:
            logger.exception("api_ccb_production_settings PATCH database error")
            return JsonResponse(
                {"error": "Erreur base de donnees. Executez: python manage.py migrate (production_ccb)."},
                status=503,
            )
        errors: dict[str, list[str]] = {}
        for h in range(1, 9):
            key = f"objectif_h{h}"
            if key not in payload:
                continue
            try:
                val = int(payload[key])
            except (TypeError, ValueError):
                errors[key] = ["Valeur entière attendue."]
                continue
            if val < 0:
                errors[key] = ["Doit être >= 0."]
                continue
            setattr(obj, key, val)
        if errors:
            return JsonResponse({"errors": errors}, status=400)
        obj.save()
        return JsonResponse(_ccb_settings_to_dict(obj))
    return HttpResponse(status=405)


def api_production_ccb(request):
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            queryset = ProductionCCB.objects.none()
        else:
            queryset = restrict_psp_scope(request.user, ProductionCCB.objects.all(), shift_field="shift")
        shift = (request.GET.get("shift") or "").strip()
        if shift in {"A", "B", "N"}:
            queryset = queryset.filter(shift=shift)
        date_val = (request.GET.get("date") or "").strip()
        if date_val:
            queryset = queryset.filter(date=date_val)
        sort = request.GET.get("sort", "-date")
        allowed = {"date", "-date", "shift", "-shift"}
        if sort not in allowed:
            sort = "-date"
        queryset = queryset.order_by(sort)
        page = parse_query_int(request, "page", 1, minimum=1)
        per_page = parse_query_int(request, "per_page", 20, minimum=1, maximum=100)
        try:
            page_obj = Paginator(queryset, per_page).get_page(page)
            results = [_ccb_to_dict(item) for item in page_obj]
        except DatabaseError:
            logger.exception("api_production_ccb GET database error")
            return JsonResponse(
                {
                    "error": "Erreur base de donnees. Executez: python manage.py migrate (notamment production_ccb).",
                },
                status=503,
            )
        return JsonResponse(
            {
                "results": results,
                "page": page_obj.number,
                "pages": page_obj.paginator.num_pages,
                "total": page_obj.paginator.count,
            }
        )
    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        payload = json_body(request)
        shift_val = (payload.get("shift") or "").strip()
        if shift_val in {"A", "B", "N"}:
            if not ensure_shift_allowed(request.user, shift_val, endpoint="api_production_ccb POST"):
                return json_forbidden()
        form = ProductionCCBForm(payload)
        if form.is_valid():
            obj = form.save()
            return JsonResponse(_ccb_to_dict(obj), status=201)
        return JsonResponse({"errors": form.errors}, status=400)
    return HttpResponse(status=405)


def api_production_ccb_detail(request, pk):
    try:
        obj = get_object_or_404(ProductionCCB, pk=pk)
    except DatabaseError:
        logger.exception("api_production_ccb_detail load pk=%s", pk)
        return JsonResponse(
            {
                "error": "Erreur base de donnees. Executez: python manage.py migrate (application production_ccb).",
            },
            status=503,
        )
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_ccb_detail GET"):
            return json_forbidden()
        return JsonResponse(_ccb_to_dict(obj))
    if request.method in {"PUT", "PATCH"}:
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_ccb_detail PATCH"):
            return json_forbidden()
        data = json_body(request)
        shift_val = (data.get("shift") or obj.shift or "").strip()
        if shift_val in {"A", "B", "N"}:
            if not ensure_shift_allowed(request.user, shift_val, endpoint="api_production_ccb_detail PATCH"):
                return json_forbidden()
        form = ProductionCCBForm(data, instance=obj)
        if form.is_valid():
            saved = form.save()
            return JsonResponse(_ccb_to_dict(saved))
        return JsonResponse({"errors": form.errors}, status=400)
    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        if is_psp(request.user) and get_psp_equipe(request.user) != "CCB":
            return json_forbidden()
        if not ensure_psp_object_access(request.user, obj, endpoint="api_production_ccb_detail DELETE"):
            return json_forbidden()
        obj.delete()
        return JsonResponse({"deleted": True})
    return HttpResponse(status=405)


def api_dashboard_ro_nro_trend(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()

    shift = (request.GET.get("shift") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    if shift:
        if shift not in {"A", "B", "N"}:
            return JsonResponse({"error": "Shift invalide."}, status=400)
        if not ensure_shift_allowed(request.user, shift, endpoint="api_dashboard_ro_nro_trend GET"):
            return json_forbidden()

    # UEP Berceau uniquement (aligné fiche production Berceau ; pas d’agrégation CCB ici).
    b_qs = restrict_psp_scope(request.user, ProductionBerceau.objects.all(), shift_field="shift")
    if shift:
        b_qs = b_qs.filter(shift=shift)
    if date_from:
        b_qs = b_qs.filter(date__gte=date_from)
    if date_to:
        b_qs = b_qs.filter(date__lte=date_to)

    by_date: dict[str, dict[str, int]] = {}
    for row in b_qs.order_by("date", "shift"):
        d = row.date.isoformat()
        o_eff, v_eff = _berceau_effective_objectif_volume(row)
        agg = by_date.setdefault(d, {"objectif": 0, "volume": 0})
        agg["objectif"] += o_eff
        agg["volume"] += v_eff

    labels = sorted(by_date.keys())
    ro_series = []
    nro_series = []
    for day in labels:
        objectif = by_date[day]["objectif"]
        volume = by_date[day]["volume"]
        ro = round((volume / objectif) * 100, 2) if objectif > 0 else 0
        nro = round(max(100 - ro, 0), 2)
        ro_series.append(ro)
        nro_series.append(nro)

    return JsonResponse(
        {
            "labels": labels,
            "series": {"ro_percent": ro_series, "nro_percent": nro_series},
            "totals": {
                "objectif": sum(v["objectif"] for v in by_date.values()),
                "volume": sum(v["volume"] for v in by_date.values()),
            },
        }
    )


def api_dashboard_arrets_par_jour(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()

    shift = (request.GET.get("shift") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    if shift:
        if shift not in {"A", "B", "N"}:
            return JsonResponse({"error": "Shift invalide."}, status=400)
        if not ensure_shift_allowed(request.user, shift, endpoint="api_dashboard_arrets_par_jour GET"):
            return json_forbidden()

    arret_ber_qs = restrict_psp_scope(request.user, ArretBerceau.objects.all(), shift_field="shift")
    alerte_base = restrict_psp_scope(
        request.user,
        AlertePanne.objects.filter(is_deleted=False),
        shift_field="shift",
        equipe_field="equipe",
    )
    if shift:
        arret_ber_qs = arret_ber_qs.filter(shift=shift)
        alerte_base = alerte_base.filter(shift=shift)
    if date_from:
        arret_ber_qs = arret_ber_qs.filter(date__gte=date_from)
        alerte_base = alerte_base.filter(date__gte=date_from)
    if date_to:
        arret_ber_qs = arret_ber_qs.filter(date__lte=date_to)
        alerte_base = alerte_base.filter(date__lte=date_to)

    def _merge_arret_alerte_by_date(arret_qs, alerte_qs):
        by_date = {}
        for row in arret_qs.values("date").annotate(total=Sum("temps_arret_min")).order_by("date"):
            d = row["date"].isoformat()
            by_date[d] = int(row["total"] or 0)
        for row in alerte_qs.values("date").annotate(total=Sum("temps_arret_min")).order_by("date"):
            d = row["date"].isoformat()
            by_date[d] = by_date.get(d, 0) + int(row["total"] or 0)
        return by_date

    # Berceau : arrêts module + alertes panne UEP Berceau. CCB : alertes panne UEP CCB uniquement.
    by_berceau = _merge_arret_alerte_by_date(arret_ber_qs, alerte_base.filter(equipe="Berceau"))
    by_ccb = _merge_arret_alerte_by_date(ArretBerceau.objects.none(), alerte_base.filter(equipe="CCB"))

    labels = sorted(set(by_berceau) | set(by_ccb))
    ber_series = [by_berceau.get(d, 0) for d in labels]
    ccb_series = [by_ccb.get(d, 0) for d in labels]
    combined = [ber_series[i] + ccb_series[i] for i in range(len(labels))]
    return JsonResponse(
        {
            "labels": labels,
            "series": {
                "berceau_minutes": ber_series,
                "ccb_minutes": ccb_series,
                "arrets_minutes": combined,
            },
            "totals": {
                "berceau_minutes": sum(ber_series),
                "ccb_minutes": sum(ccb_series),
                "arrets_minutes": sum(combined),
            },
        }
    )


def api_dashboard_pareto_postes(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()

    shift = (request.GET.get("shift") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    category = (request.GET.get("category") or "").strip().lower()
    group_by = (request.GET.get("group_by") or "poste").strip().lower()
    poste_id_raw = (request.GET.get("poste_id") or "").strip()
    poste_id = None
    if shift:
        if shift not in {"A", "B", "N"}:
            return JsonResponse({"error": "Shift invalide."}, status=400)
        if not ensure_shift_allowed(request.user, shift, endpoint="api_dashboard_pareto_postes GET"):
            return json_forbidden()
    if category and category not in {"maintenance", "kta", "logistique", "fabrication"}:
        return JsonResponse({"error": "Categorie invalide."}, status=400)
    if poste_id_raw:
        if not poste_id_raw.isdigit():
            return JsonResponse({"error": "poste_id invalide."}, status=400)
        poste_id = int(poste_id_raw)
    if group_by not in {"poste", "category", "panne_type"}:
        return JsonResponse({"error": "group_by invalide."}, status=400)
    try:
        hf, ht = _parse_heure_bounds(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    arret_qs = restrict_psp_scope(
        request.user,
        ArretBerceau.objects.select_related("poste"),
        shift_field="shift",
    )
    alerte_qs = restrict_psp_scope(
        request.user,
        AlertePanne.objects.filter(is_deleted=False, equipe="Berceau").select_related("poste"),
        shift_field="shift",
        equipe_field="equipe",
    )
    if shift:
        arret_qs = arret_qs.filter(shift=shift)
        alerte_qs = alerte_qs.filter(shift=shift)
    if date_from:
        arret_qs = arret_qs.filter(date__gte=date_from)
        alerte_qs = alerte_qs.filter(date__gte=date_from)
    if date_to:
        arret_qs = arret_qs.filter(date__lte=date_to)
        alerte_qs = alerte_qs.filter(date__lte=date_to)
    if category:
        arret_qs = arret_qs.filter(category=category)
        alerte_qs = alerte_qs.filter(category=category)
    if poste_id:
        arret_qs = arret_qs.filter(poste_id=poste_id)
        alerte_qs = alerte_qs.filter(poste_id=poste_id)
    if hf is not None:
        arret_qs = arret_qs.filter(heure_production__gte=hf)
        alerte_qs = alerte_qs.filter(heure_production__gte=hf)
    if ht is not None:
        arret_qs = arret_qs.filter(heure_production__lte=ht)
        alerte_qs = alerte_qs.filter(heure_production__lte=ht)

    by_label = {}
    if group_by == "panne_type":
        for row in alerte_qs.values("panne_type__name").annotate(total=Sum("temps_arret_min")):
            name = str(row["panne_type__name"] or "N/A")
            by_label[name] = by_label.get(name, 0) + int(row["total"] or 0)
        # Consider "sans type" only for arrets that do not have a matching alerte.
        # This prevents double counting when an arret already has a typed alert.
        alerte_keys = set(
            alerte_qs.values_list(
                "date",
                "shift",
                "heure_production",
                "module_id",
                "poste_id",
                "moyen_id",
            )
        )
        arret_without_type_total = 0
        for row in arret_qs.values(
            "date",
            "shift",
            "heure_production",
            "module_id",
            "poste_id",
            "moyen_id",
            "temps_arret_min",
        ):
            key = (
                row["date"],
                row["shift"],
                row["heure_production"],
                row["module_id"],
                row["poste_id"],
                row["moyen_id"],
            )
            if key not in alerte_keys:
                arret_without_type_total += int(row["temps_arret_min"] or 0)
        if arret_without_type_total > 0:
            by_label["Sans type (arret)"] = by_label.get("Sans type (arret)", 0) + arret_without_type_total
    else:
        field_name = "poste__name" if group_by == "poste" else "category"
        for row in arret_qs.values(field_name).annotate(total=Sum("temps_arret_min")):
            name = str(row[field_name] or "N/A")
            by_label[name] = by_label.get(name, 0) + int(row["total"] or 0)
        for row in alerte_qs.values(field_name).annotate(total=Sum("temps_arret_min")):
            name = str(row[field_name] or "N/A")
            by_label[name] = by_label.get(name, 0) + int(row["total"] or 0)

    sorted_rows = sorted(by_label.items(), key=lambda item: (-item[1], item[0]))
    labels = [name for name, _ in sorted_rows]
    values = [val for _, val in sorted_rows]
    total = sum(values) or 1
    cumulative = []
    running = 0
    for v in values:
        running += v
        cumulative.append(round((running / total) * 100, 2))

    return JsonResponse(
        {
            "labels": labels,
            "series": {"arrets_minutes": values, "cumulative_percent": cumulative},
            "totals": {"arrets_minutes": sum(values)},
            "meta": {"group_by": group_by, "category_filter": category or None, "poste_id": poste_id},
        }
    )
