from django.db.models import Q, QuerySet

from .models import Absence


def base_queryset() -> QuerySet[Absence]:
    return Absence.objects.filter(equipe="Berceau", is_deleted=False).select_related(
        "effectif", "remplacant_effectif"
    )


def apply_filters(queryset: QuerySet[Absence], params) -> QuerySet[Absence]:
    query = (params.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(effectif__nom_complet__icontains=query)
            | Q(motif__icontains=query)
            | Q(remplacant__icontains=query)
            | Q(remplacant_effectif__nom_complet__icontains=query)
        )
    shift = (params.get("shift") or "").strip()
    if shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=shift)
    sort = params.get("sort", "-date_absence")
    if sort.lstrip("-") not in {"date_absence", "shift", "effectif__nom_complet", "motif", "created_at"}:
        sort = "-date_absence"
    return queryset.order_by(sort)

