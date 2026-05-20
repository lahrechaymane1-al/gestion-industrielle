from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import OperateurEffectif


def list_view(request):
    operators = OperateurEffectif.objects.filter(equipe="Berceau", is_deleted=False)
    query = (request.GET.get("q") or "").strip()
    if query:
        operators = operators.filter(
            Q(nom_complet__icontains=query)
            | Q(cin__icontains=query)
            | Q(identifiant__icontains=query)
        )
    sort = request.GET.get("sort", "nom_complet")
    if sort.lstrip("-") not in {"nom_complet", "cin", "identifiant", "type_contrat", "shift", "fonction", "ville_actuelle", "date_entree"}:
        sort = "nom_complet"
    page_obj = Paginator(operators.order_by(sort), 15).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "app/effectif/list.html",
        {
            "active_page": "berceau_effectif",
            "page_title": "Effectif - Berceau",
            "sidebar_hidden_default": True,
            "operators": page_obj,
            "equipe_value": "Berceau",
            "add_url_name": "berceau_effectif_add",
            "edit_url_name": "berceau_effectif_edit",
            "detail_url_name": "berceau_effectif_detail",
            "delete_url_name": "berceau_effectif_delete",
            "sort": sort,
            "query": query,
        },
    )

