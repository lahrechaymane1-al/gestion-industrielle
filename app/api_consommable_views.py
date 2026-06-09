from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse

from consommable.models import ConsommableItem, ConsommablePurchase

from .api_utils import json_body, json_forbidden, parse_query_int
from .authz import (
    can_do_action as auth_can_do_action,
    ensure_equipe_allowed,
    is_admin_or_ru,
)

VALID_SHIFTS = {"A", "B", "N"}


def _parse_date(value: str | None) -> date_cls:
    if not value:
        return date_cls.today()
    return date_cls.fromisoformat(value)


def _normalize_equipe(raw: str | None) -> str:
    equipe = (raw or "Berceau").strip()
    return equipe if equipe in {"Berceau", "CCB"} else "Berceau"


def _to_decimal(raw) -> Decimal:
    try:
        return Decimal(str(raw or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _item_to_dict(obj: ConsommableItem) -> dict:
    return {
        "id": obj.id,
        "equipe": obj.equipe,
        "type_materiel": obj.type_materiel,
        "name": obj.name,
        "reference": obj.reference,
        "unit_price_eur": f"{obj.unit_price_eur:.2f}",
        "is_active": bool(obj.is_active),
    }


def _purchase_to_dict(obj: ConsommablePurchase) -> dict:
    return {
        "id": obj.id,
        "equipe": obj.equipe,
        "shift": obj.shift,
        "item_id": obj.item_id,
        "item_name": obj.item.name,
        "item_reference": obj.item.reference,
        "item_type": obj.item.type_materiel,
        "quantity": int(obj.quantity),
        "unit_price_eur": f"{obj.unit_price_eur:.2f}",
        "total_price_eur": f"{obj.total_price_eur:.2f}",
        "purchase_date": obj.purchase_date.isoformat(),
        "note": obj.note or "",
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
    }


def api_consommable_items(request):
    if not is_admin_or_ru(request.user):
        return json_forbidden()
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        equipe = _normalize_equipe(request.GET.get("equipe"))
        if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_items GET"):
            return json_forbidden()
        q = (request.GET.get("q") or "").strip()
        qs = ConsommableItem.objects.filter(equipe=equipe, is_active=True)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(reference__icontains=q))
        return JsonResponse({"results": [_item_to_dict(row) for row in qs.order_by("name", "reference")]})

    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        payload = json_body(request)
        equipe = _normalize_equipe(payload.get("equipe"))
        if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_items POST"):
            return json_forbidden()

        name = str(payload.get("name") or "").strip()
        reference = str(payload.get("reference") or "").strip()
        type_materiel = str(payload.get("type_materiel") or "AUTRE").strip()
        unit_price_eur = _to_decimal(payload.get("unit_price_eur"))

        errors: dict[str, list[str]] = {}
        if not name:
            errors.setdefault("name", []).append("Le nom est obligatoire.")
        if not reference:
            errors.setdefault("reference", []).append("La référence est obligatoire.")
        if not type_materiel:
            errors.setdefault("type_materiel", []).append("Le type de matériel est obligatoire.")
        if unit_price_eur < 0:
            errors.setdefault("unit_price_eur", []).append("Le prix doit être >= 0.")
        if ConsommableItem.objects.filter(
            equipe=equipe, reference__iexact=reference, name__iexact=name
        ).exists():
            errors.setdefault("reference", []).append("Cet article (référence + nom) existe déjà pour cette UEP.")
        if errors:
            return JsonResponse({"errors": errors}, status=400)

        row = ConsommableItem.objects.create(
            equipe=equipe,
            type_materiel=type_materiel,
            name=name,
            reference=reference,
            unit_price_eur=unit_price_eur,
            is_active=True,
        )
        return JsonResponse(_item_to_dict(row), status=201)

    return HttpResponse(status=405)


def api_consommable_types(request):
    if not is_admin_or_ru(request.user):
        return json_forbidden()

    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        equipe = _normalize_equipe(request.GET.get("equipe"))
        if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_types GET"):
            return json_forbidden()
        rows = (
            ConsommableItem.objects.filter(equipe=equipe)
            .values("type_materiel")
            .annotate(total=Count("id"))
            .order_by("type_materiel")
        )
        return JsonResponse({"results": [{"type_materiel": r["type_materiel"], "total": int(r["total"])} for r in rows]})

    payload = json_body(request)
    equipe = _normalize_equipe(payload.get("equipe"))
    if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_types write"):
        return json_forbidden()

    if request.method == "PATCH":
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        old_type = str(payload.get("old_type") or "").strip()
        new_type = str(payload.get("new_type") or "").strip()
        if not old_type:
            return JsonResponse({"errors": {"old_type": ["Type source obligatoire."]}}, status=400)
        if not new_type:
            return JsonResponse({"errors": {"new_type": ["Nouveau type obligatoire."]}}, status=400)
        if old_type == new_type:
            return JsonResponse({"ok": True, "updated": 0})
        updated = ConsommableItem.objects.filter(equipe=equipe, type_materiel=old_type).update(type_materiel=new_type)
        return JsonResponse({"ok": True, "updated": int(updated)})

    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        old_type = str(payload.get("old_type") or "").strip()
        replacement_type = str(payload.get("replacement_type") or "AUTRE").strip() or "AUTRE"
        if not old_type:
            return JsonResponse({"errors": {"old_type": ["Type à supprimer obligatoire."]}}, status=400)
        if old_type == replacement_type:
            return JsonResponse({"errors": {"replacement_type": ["Le type de remplacement doit être différent."]}}, status=400)
        updated = ConsommableItem.objects.filter(equipe=equipe, type_materiel=old_type).update(
            type_materiel=replacement_type
        )
        return JsonResponse({"ok": True, "updated": int(updated), "replacement_type": replacement_type})

    return HttpResponse(status=405)


def api_consommable_items_detail(request, pk: int):
    if not is_admin_or_ru(request.user):
        return json_forbidden()
    row = ConsommableItem.objects.filter(pk=pk).first()
    if not row:
        return HttpResponse(status=404)
    if not ensure_equipe_allowed(request.user, row.equipe, endpoint="api_consommable_items_detail"):
        return json_forbidden()

    if request.method == "PATCH":
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        payload = json_body(request)
        if "type_materiel" in payload:
            type_materiel = str(payload.get("type_materiel") or "").strip()
            if not type_materiel:
                return JsonResponse({"errors": {"type_materiel": ["Le type de matériel est obligatoire."]}}, status=400)
            row.type_materiel = type_materiel
        if "name" in payload:
            row.name = str(payload.get("name") or "").strip()
        if "reference" in payload:
            ref = str(payload.get("reference") or "").strip()
            if (
                ref
                and ConsommableItem.objects.filter(
                    equipe=row.equipe, reference__iexact=ref, name__iexact=row.name
                )
                .exclude(pk=row.pk)
                .exists()
            ):
                return JsonResponse({"errors": {"reference": ["Article (référence + nom) déjà utilisé."]}}, status=400)
            row.reference = ref
        if "unit_price_eur" in payload:
            row.unit_price_eur = _to_decimal(payload.get("unit_price_eur"))
        if "is_active" in payload:
            row.is_active = bool(payload.get("is_active"))
        if not row.name:
            return JsonResponse({"errors": {"name": ["Le nom est obligatoire."]}}, status=400)
        if not row.reference:
            return JsonResponse({"errors": {"reference": ["La référence est obligatoire."]}}, status=400)
        if row.unit_price_eur < 0:
            return JsonResponse({"errors": {"unit_price_eur": ["Le prix doit être >= 0."]}}, status=400)
        row.save()
        return JsonResponse(_item_to_dict(row))

    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        row.is_active = False
        row.save(update_fields=["is_active"])
        return JsonResponse({"ok": True})

    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        return JsonResponse(_item_to_dict(row))

    return HttpResponse(status=405)


def api_consommable_purchases(request):
    if not is_admin_or_ru(request.user):
        return json_forbidden()
    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        equipe = _normalize_equipe(request.GET.get("equipe"))
        if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_purchases GET"):
            return json_forbidden()
        q = (request.GET.get("q") or "").strip()
        qs = ConsommablePurchase.objects.select_related("item").filter(equipe=equipe)
        shift_val = (request.GET.get("shift") or "").strip().upper()
        if shift_val in VALID_SHIFTS:
            qs = qs.filter(shift=shift_val)
        if q:
            qs = qs.filter(Q(item__name__icontains=q) | Q(item__reference__icontains=q) | Q(note__icontains=q))
        date_val = (request.GET.get("date") or "").strip()
        if date_val:
            try:
                qs = qs.filter(purchase_date=_parse_date(date_val))
            except ValueError:
                pass

        per_page = parse_query_int(request, "per_page", 15, minimum=1, maximum=100)
        page_num = parse_query_int(request, "page", 1, minimum=1)
        paginator = Paginator(qs.order_by("-purchase_date", "-created_at"), per_page)
        page = paginator.get_page(page_num)
        return JsonResponse(
            {
                "results": [_purchase_to_dict(row) for row in page.object_list],
                "page": page.number,
                "pages": paginator.num_pages,
                "total": paginator.count,
            }
        )

    if request.method == "POST":
        if not auth_can_do_action(request.user, "create"):
            return json_forbidden()
        payload = json_body(request)
        equipe = _normalize_equipe(payload.get("equipe"))
        if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_purchases POST"):
            return json_forbidden()

        item_id = payload.get("item_id")
        quantity = int(payload.get("quantity") or 0)
        shift = str(payload.get("shift") or "").strip().upper()
        purchase_date = _parse_date(payload.get("purchase_date"))
        note = str(payload.get("note") or "").strip()
        item = ConsommableItem.objects.filter(pk=item_id, equipe=equipe, is_active=True).first()

        errors: dict[str, list[str]] = {}
        if not item:
            errors.setdefault("item_id", []).append("Article introuvable pour cette UEP.")
        if quantity <= 0:
            errors.setdefault("quantity", []).append("La quantité doit être > 0.")
        if shift not in VALID_SHIFTS:
            errors.setdefault("shift", []).append("Le shift (A, B ou N) est obligatoire.")
        if errors:
            return JsonResponse({"errors": errors}, status=400)

        unit_price_eur = item.unit_price_eur
        total_price_eur = (unit_price_eur * Decimal(quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        row = ConsommablePurchase.objects.create(
            equipe=equipe,
            shift=shift,
            item=item,
            quantity=quantity,
            unit_price_eur=unit_price_eur,
            total_price_eur=total_price_eur,
            purchase_date=purchase_date,
            note=note,
            created_by=request.user if request.user.is_authenticated else None,
            updated_by=request.user if request.user.is_authenticated else None,
        )
        return JsonResponse(_purchase_to_dict(row), status=201)

    return HttpResponse(status=405)


def api_consommable_purchases_detail(request, pk: int):
    if not is_admin_or_ru(request.user):
        return json_forbidden()
    row = ConsommablePurchase.objects.select_related("item").filter(pk=pk).first()
    if not row:
        return HttpResponse(status=404)
    if not ensure_equipe_allowed(request.user, row.equipe, endpoint="api_consommable_purchases_detail"):
        return json_forbidden()

    if request.method == "GET":
        if not auth_can_do_action(request.user, "read"):
            return json_forbidden()
        return JsonResponse(_purchase_to_dict(row))

    if request.method == "PATCH":
        if not auth_can_do_action(request.user, "update"):
            return json_forbidden()
        payload = json_body(request)
        if "shift" in payload:
            shift = str(payload.get("shift") or "").strip().upper()
            if shift not in VALID_SHIFTS:
                return JsonResponse({"errors": {"shift": ["Le shift (A, B ou N) est obligatoire."]}}, status=400)
            row.shift = shift
        if "quantity" in payload:
            quantity = int(payload.get("quantity") or 0)
            if quantity <= 0:
                return JsonResponse({"errors": {"quantity": ["La quantité doit être > 0."]}}, status=400)
            row.quantity = quantity
        if "item_id" in payload:
            item_id = payload.get("item_id")
            item = ConsommableItem.objects.filter(pk=item_id, equipe=row.equipe, is_active=True).first()
            if not item:
                return JsonResponse({"errors": {"item_id": ["Article introuvable."]}}, status=400)
            row.item = item
            row.unit_price_eur = item.unit_price_eur
        if "purchase_date" in payload:
            row.purchase_date = _parse_date(payload.get("purchase_date"))
        if "note" in payload:
            row.note = str(payload.get("note") or "").strip()
        row.total_price_eur = (row.unit_price_eur * Decimal(row.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        row.updated_by = request.user if request.user.is_authenticated else None
        row.save()
        return JsonResponse(_purchase_to_dict(row))

    if request.method == "DELETE":
        if not auth_can_do_action(request.user, "delete"):
            return json_forbidden()
        row.delete()
        return JsonResponse({"ok": True})

    return HttpResponse(status=405)


def api_consommable_stats(request):
    """Per-shift totals (money + quantity) with day/month period and shift/type filters.

    Query params:
      - mode: "day" (default) or "month"
      - date: YYYY-MM-DD  (used when mode=day)
      - month: YYYY-MM    (used when mode=month)
      - shift: optional A/B/N filter
      - type_materiel: optional material type filter
    """
    if not is_admin_or_ru(request.user):
        return json_forbidden()
    if request.method != "GET":
        return HttpResponse(status=405)
    if not auth_can_do_action(request.user, "read"):
        return json_forbidden()
    equipe = _normalize_equipe(request.GET.get("equipe"))
    if not ensure_equipe_allowed(request.user, equipe, endpoint="api_consommable_stats GET"):
        return json_forbidden()

    qs = ConsommablePurchase.objects.filter(equipe=equipe)

    mode = (request.GET.get("mode") or "").strip().lower()
    if mode == "month":
        month_val = (request.GET.get("month") or "").strip()
        if month_val:
            try:
                year_str, month_str = month_val.split("-")
                qs = qs.filter(purchase_date__year=int(year_str), purchase_date__month=int(month_str))
            except (ValueError, TypeError):
                pass
    else:
        date_val = (request.GET.get("date") or "").strip()
        if date_val:
            try:
                qs = qs.filter(purchase_date=_parse_date(date_val))
            except ValueError:
                pass

    shift_filter = (request.GET.get("shift") or "").strip().upper()
    if shift_filter in VALID_SHIFTS:
        qs = qs.filter(shift=shift_filter)

    type_filter = (request.GET.get("type_materiel") or "").strip()
    if type_filter:
        qs = qs.filter(item__type_materiel=type_filter)

    agg = {
        row["shift"]: row
        for row in qs.values("shift").annotate(
            total_eur=Sum("total_price_eur"), total_qty=Sum("quantity")
        )
    }
    results = []
    for shift in ("A", "B", "N"):
        row = agg.get(shift, {})
        total_eur = row.get("total_eur") or Decimal("0.00")
        results.append(
            {
                "shift": shift,
                "total_eur": f"{Decimal(total_eur):.2f}",
                "total_qty": int(row.get("total_qty") or 0),
            }
        )
    return JsonResponse({"results": results})

