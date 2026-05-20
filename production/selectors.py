from django.db.models import QuerySet

from .models import ProductionBerceau


def base_queryset() -> QuerySet[ProductionBerceau]:
    return ProductionBerceau.objects.all()


def apply_filters(queryset: QuerySet[ProductionBerceau], params) -> QuerySet[ProductionBerceau]:
    line = (params.get("line") or "").strip()
    if line in {"A1", "A3"}:
        queryset = queryset.filter(line=line)
    return queryset

