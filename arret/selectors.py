from django.db.models import QuerySet

from .models import ArretBerceau


def base_queryset() -> QuerySet[ArretBerceau]:
    return ArretBerceau.objects.select_related("module", "poste", "moyen").all()


def apply_filters(queryset: QuerySet[ArretBerceau], params) -> QuerySet[ArretBerceau]:
    shift = (params.get("shift") or "").strip()
    if shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=shift)
    if params.get("date"):
        queryset = queryset.filter(date=params.get("date"))
    return queryset.order_by("-date", "shift", "heure_production")

