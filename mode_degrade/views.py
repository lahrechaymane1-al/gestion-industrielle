from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import ModeDegrade


def list_view(request):
    items = ModeDegrade.objects.filter(equipe="Berceau", is_deleted=False)
    q = (request.GET.get("q") or "").strip()
    if q:
        items = items.filter(
            Q(action__icontains=q) | Q(probleme__icontains=q) | Q(pilote__icontains=q) | Q(cause__icontains=q)
        )
    sort = request.GET.get("sort", "-date")
    if sort.lstrip("-") not in {"date", "shift", "statut", "delai", "pilote"}:
        sort = "-date"
    page_obj = Paginator(items.order_by(sort), 15).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "app/mode_degrade/list.html",
        {
            "active_page": "berceau_mode_degrade",
            "page_title": "Mode Degrade - Berceau",
            "sidebar_hidden_default": True,
            "items": page_obj,
            "equipe_value": "Berceau",
            "add_url_name": "berceau_mode_degrade_add",
            "edit_url_name": "berceau_mode_degrade_edit",
            "detail_url_name": "berceau_mode_degrade_detail",
            "delete_url_name": "berceau_mode_degrade_delete",
        },
    )

