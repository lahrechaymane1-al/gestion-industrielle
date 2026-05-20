from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from app.forms import AbsenceForm
from .models import Absence
from effectif_ccb.models import OperateurEffectif


def list_view(request):
    absences = (
        Absence.objects.filter(equipe="CCB", is_deleted=False)
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
            "active_page": "ccb_absence",
            "page_title": "Absence - CCB",
            "sidebar_hidden_default": True,
            "absences": page_obj,
            "equipe_value": "CCB",
            "add_url_name": "ccb_absence_add",
            "edit_url_name": "ccb_absence_edit",
            "detail_url_name": "ccb_absence_detail",
            "delete_url_name": "ccb_absence_delete",
            "query": query,
            "sort": sort,
            "shift_filter": (request.GET.get("shift") or "").strip(),
            "effectif_filter": (request.GET.get("effectif") or "").strip(),
            "effectif_options": OperateurEffectif.objects.filter(equipe="CCB", is_deleted=False)
            .order_by("nom_complet")
            .values("id", "nom_complet"),
        },
    )


def add_view(request):
    form = AbsenceForm(request.POST or None)
    form.fields["effectif"].queryset = OperateurEffectif.objects.filter(equipe="CCB", is_deleted=False).order_by("nom_complet")
    form.fields["remplacant_effectif"].queryset = form.fields["effectif"].queryset
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = "CCB"
        obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Absence CCB ajoutee avec succes.")
        return redirect("ccb_absence")
    return render(
        request,
        "app/absence/form.html",
        {
            "active_page": "ccb_absence",
            "page_title": "Ajouter une absence - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_absence",
        },
    )


def edit_view(request, pk):
    absence = get_object_or_404(Absence, pk=pk, equipe="CCB", is_deleted=False)
    form = AbsenceForm(request.POST or None, instance=absence)
    form.fields["effectif"].queryset = OperateurEffectif.objects.filter(equipe="CCB", is_deleted=False).order_by("nom_complet")
    form.fields["remplacant_effectif"].queryset = form.fields["effectif"].queryset
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = "CCB"
        obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "Absence CCB modifiee avec succes.")
        return redirect("ccb_absence")
    return render(
        request,
        "app/absence/form.html",
        {
            "active_page": "ccb_absence",
            "page_title": "Modifier une absence - CCB",
            "sidebar_hidden_default": True,
            "form": form,
            "return_url_name": "ccb_absence",
        },
    )


def detail_view(request, pk):
    absence = get_object_or_404(
        Absence.objects.select_related("effectif", "remplacant_effectif"),
        pk=pk,
        equipe="CCB",
        is_deleted=False,
    )
    return render(
        request,
        "app/absence/detail.html",
        {
            "active_page": "ccb_absence",
            "page_title": "Detail absence - CCB",
            "sidebar_hidden_default": True,
            "absence": absence,
            "return_url_name": "ccb_absence",
        },
    )


def delete_view(request, pk):
    absence = get_object_or_404(Absence, pk=pk, equipe="CCB", is_deleted=False)
    if request.method == "POST":
        absence.is_deleted = True
        absence.updated_by = request.user
        absence.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Absence supprimee avec succes.")
        return redirect("ccb_absence")
    return HttpResponse("Methode non autorisee.", status=405)

