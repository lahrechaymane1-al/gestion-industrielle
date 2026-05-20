from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import Absence
from effectif.models import OperateurEffectif


def list_view(request):
    absences = (
        Absence.objects.filter(equipe="Berceau", is_deleted=False)
        .select_related("effectif", "remplacant_effectif")
    )
    query = (request.GET.get("q") or "").strip()
    if query:
        absences = absences.filter(
            Q(effectif__nom_complet__icontains=query)
            | Q(motif__icontains=query)
            | Q(remplacant__icontains=query)
            | Q(remplacant_effectif__nom_complet__icontains=query)
        )
    sort = request.GET.get("sort", "-date_absence")
    if sort.lstrip("-") not in {"date_absence", "shift", "effectif__nom_complet", "motif", "created_at"}:
        sort = "-date_absence"
    page_obj = Paginator(absences.order_by(sort), 15).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "app/absence/list.html",
        {
            "active_page": "berceau_absence",
            "page_title": "Absence - Berceau",
            "sidebar_hidden_default": True,
            "absences": page_obj,
            "equipe_value": "Berceau",
            "add_url_name": "berceau_absence_add",
            "edit_url_name": "berceau_absence_edit",
            "detail_url_name": "berceau_absence_detail",
            "delete_url_name": "berceau_absence_delete",
            "query": query,
            "sort": sort,
            "shift_filter": (request.GET.get("shift") or "").strip(),
            "effectif_filter": (request.GET.get("effectif") or "").strip(),
            "effectif_options": OperateurEffectif.objects.filter(equipe="Berceau", is_deleted=False)
            .order_by("nom_complet")
            .values("id", "nom_complet"),
        },
    )

