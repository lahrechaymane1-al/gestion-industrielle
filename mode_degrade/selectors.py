from django.db.models import Q, QuerySet

from .models import ModeDegrade


def base_queryset() -> QuerySet[ModeDegrade]:
    return ModeDegrade.objects.filter(equipe="Berceau", is_deleted=False)


def apply_filters(queryset: QuerySet[ModeDegrade], params) -> QuerySet[ModeDegrade]:
    query = (params.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(action__icontains=query)
            | Q(probleme__icontains=query)
            | Q(pilote__icontains=query)
            | Q(cause__icontains=query)
        )
    sort = params.get("sort", "-date")
    if sort.lstrip("-") not in {"date", "shift", "statut", "delai", "pilote"}:
        sort = "-date"
    return queryset.order_by(sort)

