from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from app.forms import ModeDegradeForm
from .models import ModeDegrade


def list_view(request):
    items = ModeDegrade.objects.filter(equipe="CCB", is_deleted=False)
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
            "active_page": "ccb_mode_degrade",
            "page_title": "Mode Degrade - CCB",
            "sidebar_hidden_default": True,
            "items": page_obj,
            "equipe_value": "CCB",
            "add_url_name": "ccb_mode_degrade_add",
            "edit_url_name": "ccb_mode_degrade_edit",
            "detail_url_name": "ccb_mode_degrade_detail",
            "delete_url_name": "ccb_mode_degrade_delete",
        },
    )


def add_view(request):
    form = ModeDegradeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = "CCB"
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Element mode degrade CCB ajoute avec succes.")
        return redirect("ccb_mode_degrade")
    return render(
        request,
        "app/mode_degrade/form.html",
        {
            "active_page": "ccb_mode_degrade",
            "page_title": "Ajouter mode degrade - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_mode_degrade",
        },
    )


def edit_view(request, pk):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe="CCB", is_deleted=False)
    form = ModeDegradeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = "CCB"
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Element mode degrade CCB modifie avec succes.")
        return redirect("ccb_mode_degrade")
    return render(
        request,
        "app/mode_degrade/form.html",
        {
            "active_page": "ccb_mode_degrade",
            "page_title": "Modifier mode degrade - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_mode_degrade",
        },
    )


def detail_view(request, pk):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe="CCB", is_deleted=False)
    return render(
        request,
        "app/mode_degrade/detail.html",
        {
            "active_page": "ccb_mode_degrade",
            "page_title": "Detail mode degrade - CCB",
            "sidebar_hidden_default": True,
            "item": item,
            "return_url_name": "ccb_mode_degrade",
        },
    )


def delete_view(request, pk):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe="CCB", is_deleted=False)
    if request.method == "POST":
        item.is_deleted = True
        item.updated_by = request.user
        item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Element mode degrade supprime avec succes.")
        return redirect("ccb_mode_degrade")
    return HttpResponse("Methode non autorisee.", status=405)

