from django.db.models import Q, QuerySet

from .models import OperateurEffectif


def base_queryset() -> QuerySet[OperateurEffectif]:
    return OperateurEffectif.objects.filter(equipe="Berceau", is_deleted=False)


def apply_filters(queryset: QuerySet[OperateurEffectif], params) -> QuerySet[OperateurEffectif]:
    query = (params.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(nom_complet__icontains=query)
            | Q(cin__icontains=query)
            | Q(identifiant__icontains=query)
        )
    sort = params.get("sort", "nom_complet")
    if sort.lstrip("-") not in {"nom_complet", "cin", "identifiant", "type_contrat", "shift", "fonction", "ville_actuelle", "date_entree"}:
        sort = "nom_complet"
    return queryset.order_by(sort)

