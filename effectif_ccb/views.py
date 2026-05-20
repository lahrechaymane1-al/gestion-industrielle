from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from app.forms import OperateurEffectifForm
from .models import OperateurEffectif


def list_view(request):
    operators = OperateurEffectif.objects.filter(equipe="CCB", is_deleted=False)
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
            "active_page": "ccb_effectif",
            "page_title": "Effectif - CCB",
            "sidebar_hidden_default": True,
            "operators": page_obj,
            "equipe_value": "CCB",
            "add_url_name": "ccb_effectif_add",
            "edit_url_name": "ccb_effectif_edit",
            "detail_url_name": "ccb_effectif_detail",
            "delete_url_name": "ccb_effectif_delete",
            "sort": sort,
            "query": query,
        },
    )


def add_view(request):
    form = OperateurEffectifForm(request.POST or None, initial={"equipe": "CCB"})
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Operateur CCB ajoute avec succes.")
        return redirect("ccb_effectif")
    return render(
        request,
        "app/effectif/form.html",
        {
            "active_page": "ccb_effectif",
            "page_title": "Ajouter un operateur - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_effectif",
        },
    )


def edit_view(request, pk):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe="CCB", is_deleted=False)
    form = OperateurEffectifForm(request.POST or None, instance=operator)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Operateur CCB modifie avec succes.")
        return redirect("ccb_effectif")
    return render(
        request,
        "app/effectif/form.html",
        {
            "active_page": "ccb_effectif",
            "page_title": "Modifier un operateur - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_effectif",
        },
    )


def detail_view(request, pk):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe="CCB", is_deleted=False)
    return render(
        request,
        "app/effectif/detail.html",
        {
            "active_page": "ccb_effectif",
            "page_title": "Detail collaborateur - CCB",
            "sidebar_hidden_default": True,
            "operator": operator,
            "return_url_name": "ccb_effectif",
        },
    )


def delete_view(request, pk):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe="CCB", is_deleted=False)
    if request.method == "POST":
        operator.is_deleted = True
        operator.updated_by = request.user
        operator.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Collaborateur supprime avec succes.")
        return redirect("ccb_effectif")
    return HttpResponse("Methode non autorisee.", status=405)

