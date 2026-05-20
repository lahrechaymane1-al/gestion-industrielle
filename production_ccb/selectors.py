from django.db.models import QuerySet

from .models import ProductionCCB


def base_queryset() -> QuerySet[ProductionCCB]:
    return ProductionCCB.objects.all()


def apply_filters(queryset: QuerySet[ProductionCCB], params) -> QuerySet[ProductionCCB]:
    shift = (params.get("shift") or "").strip()
    if shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=shift)
    return queryset

