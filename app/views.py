import io
import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from .authz import (
    can_do_action as auth_can_do_action,
    ensure_equipe_allowed,
    ensure_psp_absence_effectifs_allowed,
    ensure_psp_effectif_write_allowed,
    ensure_psp_object_access,
    ensure_shift_allowed,
    get_profile,
    get_psp_effectif_id,
    is_admin_or_ru,
    is_psp,
    restrict_psp_scope,
)
from .api_production_views import filter_production_berceau_by_diversite
from .effectif_team import CANONICAL_CODE_EQUIPE_BY_SCOPE
from .forms import (
    AbsenceForm,
    ModeDegradeForm,
    OperateurEffectifForm,
    ProductionBerceauForm,
    ProductionCCBForm,
)
from .models import Absence, ModeDegrade, OperateurEffectif, ProductionBerceau, ProductionCCB
from .models import UserAccessProfile

logger = logging.getLogger(__name__)


def require_role_action(action):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not auth_can_do_action(request.user, action):
                return HttpResponse("Acces refuse.", status=403)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def page_context(active_page, title):
    return {
        "active_page": active_page,
        "page_title": title,
        "sidebar_hidden_default": active_page != "home",
    }


def _get_filtered_production_queryset(request):
    selected_line = request.GET.get("line", "")
    queryset = ProductionBerceau.objects.all()
    queryset = filter_production_berceau_by_diversite(queryset, selected_line)
    date_val = (request.GET.get("date") or "").strip()
    if date_val:
        queryset = queryset.filter(date=date_val)
    shift = (request.GET.get("shift") or "").strip()
    if shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=shift)
    return queryset, selected_line


def berceau_production_list(request):
    queryset, selected_line = _get_filtered_production_queryset(request)
    hourly_rows = []
    for item in queryset:
        hourly_production = [
            item.production_h1,
            item.production_h2,
            item.production_h3,
            item.production_h4,
            item.production_h5,
            item.production_h6,
            item.production_h7,
            item.production_h8,
        ]
        hourly_objectifs = [
            item.objectif_h1,
            item.objectif_h2,
            item.objectif_h3,
            item.objectif_h4,
            item.objectif_h5,
            item.objectif_h6,
            item.objectif_h7,
            item.objectif_h8,
        ]
        for hour_index in range(8):
            hourly_rows.append(
                {
                    "production": item,
                    "hour": hour_index + 1,
                    "production_value": hourly_production[hour_index],
                    "objectif_value": hourly_objectifs[hour_index],
                }
            )
    context = page_context("berceau_production", "Production Berceau")
    context.update(
        {
            "productions": queryset,
            "hourly_rows": hourly_rows,
            "line_filter": selected_line,
            "line_choices": ProductionBerceau.LINE_CHOICES,
        }
    )
    return render(request, "app/berceau/production_list.html", context)


def berceau_production_export(request):
    queryset, selected_line = _get_filtered_production_queryset(request)
    export_format = (request.GET.get("format") or "").lower().strip()

    rows = []
    for item in queryset:
        rows.append(
            [
                item.line,
                item.date.strftime("%Y-%m-%d"),
                item.shift,
                item.objectif,
                item.production_h1,
                item.production_h2,
                item.production_h3,
                item.production_h4,
                item.production_h5,
                item.production_h6,
                item.production_h7,
                item.production_h8,
                item.objectif_h1,
                item.objectif_h2,
                item.objectif_h3,
                item.objectif_h4,
                item.objectif_h5,
                item.objectif_h6,
                item.objectif_h7,
                item.objectif_h8,
                item.rebut,
            ]
        )

    headers = [
        "Diversité",
        "Date",
        "Shift",
        "Objectif",
        "Production H1",
        "Production H2",
        "Production H3",
        "Production H4",
        "Production H5",
        "Production H6",
        "Production H7",
        "Production H8",
        "Objectif H1",
        "Objectif H2",
        "Objectif H3",
        "Objectif H4",
        "Objectif H5",
        "Objectif H6",
        "Objectif H7",
        "Objectif H8",
        "Rebut",
    ]

    if export_format == "excel":
        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Production Berceau"
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 28)

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = "production_berceau"
            if selected_line:
                filename += f"_{selected_line}"
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            workbook.save(response)
            return response
        except Exception:
            logger.exception("Excel export failed for line filter '%s'", selected_line)
            return HttpResponse("Une erreur est survenue lors de l'export Excel.", status=500)

    if export_format == "pdf":
        try:
            buffer = io.BytesIO()
            document = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=1 * cm,
                rightMargin=1 * cm,
                topMargin=1 * cm,
                bottomMargin=1 * cm,
            )
            table_data = [headers] + rows
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4FA3")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5E2F6")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.whitesmoke, colors.HexColor("#F5F9FF")],
                        ),
                    ]
                )
            )
            document.build([table])
            pdf = buffer.getvalue()
            buffer.close()

            response = HttpResponse(content_type="application/pdf")
            filename = "production_berceau"
            if selected_line:
                filename += f"_{selected_line}"
            response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
            response.write(pdf)
            return response
        except Exception:
            logger.exception("PDF export failed for line filter '%s'", selected_line)
            return HttpResponse("Une erreur est survenue lors de l'export PDF.", status=500)

    return HttpResponseBadRequest("Format d'export non supporte.")


def berceau_production_add(request):
    form = ProductionBerceauForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production ajoutee avec succes.")
        return redirect("berceau_production_list")
    context = page_context("berceau_production", "Ajouter une production")
    context["form"] = form
    return render(request, "app/berceau/production_form.html", context)


def berceau_production_edit(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    form = ProductionBerceauForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production modifiee avec succes.")
        return redirect("berceau_production_list")
    context = page_context("berceau_production", "Modifier une production")
    context.update({"form": form, "production": obj})
    return render(request, "app/berceau/production_form.html", context)


def berceau_production_detail(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    context = page_context("berceau_production", "Detail production Berceau")
    context["production"] = obj
    return render(request, "app/berceau/production_detail.html", context)


def berceau_production_delete(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Production supprimee avec succes.")
        return redirect("berceau_production_list")
    return HttpResponse("Methode non autorisee.", status=405)


def _placeholder(request, template, active, title):
    return render(request, template, page_context(active, title))


def _effectif_list(request, equipe, active_page, title, add_url_name, edit_url_name):
    operators = OperateurEffectif.objects.filter(equipe=equipe, is_deleted=False)
    query = (request.GET.get("q") or "").strip()
    if query:
        operators = operators.filter(
            Q(nom_complet__icontains=query)
            | Q(cin__icontains=query)
            | Q(identifiant__icontains=query)
            | Q(matricule__icontains=query)
        )
    for field in ("shift", "type_contrat", "sexe", "ville_actuelle", "specialite"):
        value = (request.GET.get(field) or "").strip()
        if value:
            operators = operators.filter(**{field: value})

    sort = request.GET.get("sort", "nom_complet")
    allowed_sort = {
        "nom_complet",
        "cin",
        "identifiant",
        "matricule",
        "type_contrat",
        "shift",
        "fonction",
        "ville_actuelle",
        "date_entree",
    }
    if sort.lstrip("-") not in allowed_sort:
        sort = "nom_complet"
    operators = operators.order_by(sort)

    export_format = (request.GET.get("export") or "").lower().strip()
    if export_format in {"csv", "excel"}:
        headers = [
            "Nom complet",
            "CIN",
            "Identifiant",
            "Matricule",
            "Type contrat",
            "Shift",
            "Fonction",
            "Ville actuelle",
            "Date entree",
        ]
        rows = [
            [
                item.nom_complet,
                item.cin,
                item.identifiant,
                item.matricule or "",
                item.type_contrat,
                item.shift,
                item.fonction,
                item.ville_actuelle,
                item.date_entree.strftime("%Y-%m-%d"),
            ]
            for item in operators
        ]
        if export_format == "csv":
            import csv

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="effectif_{equipe.lower()}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = f"Effectif {equipe}"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="effectif_{equipe.lower()}.xlsx"'
        workbook.save(response)
        return response

    page_obj = Paginator(operators, 15).get_page(request.GET.get("page") or 1)
    context = page_context(active_page, title)
    context.update(
        {
            "operators": page_obj,
            "equipe_value": equipe,
            "add_url_name": add_url_name,
            "edit_url_name": edit_url_name,
            "detail_url_name": f"{active_page}_detail",
            "delete_url_name": f"{active_page}_delete",
            "sort": sort,
            "query": query,
        }
    )
    return render(request, "app/effectif/list.html", context)


def _effectif_add(request, equipe, active_page, title, success_message, redirect_name):
    form = OperateurEffectifForm(request.POST or None, initial={"equipe": equipe})
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update(
        {
            "form": form,
            "return_url_name": redirect_name,
        }
    )
    return render(request, "app/effectif/form.html", context)


def _effectif_edit(request, pk, equipe, active_page, title, success_message, redirect_name):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe=equipe, is_deleted=False)
    form = OperateurEffectifForm(request.POST or None, instance=operator)
    if request.method == "POST" and form.is_valid():
        original_shift = operator.shift
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        impacted = _sync_psp_team_shift_if_needed(request=request, old_shift=original_shift, saved_item=obj)
        if impacted:
            messages.info(
                request,
                f"Equipe synchronisee: {impacted} collaborateur(s) (meme code equipe ou rattaches au PSP) ont le shift {obj.shift}.",
            )
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update({"form": form, "return_url_name": redirect_name})
    return render(request, "app/effectif/form.html", context)


def _effectif_detail(request, pk, equipe, active_page, title):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe=equipe, is_deleted=False)
    context = page_context(active_page, title)
    context["operator"] = operator
    context["return_url_name"] = active_page
    return render(request, "app/effectif/detail.html", context)


def _effectif_delete(request, pk, equipe, active_page, redirect_name):
    operator = get_object_or_404(OperateurEffectif, pk=pk, equipe=equipe, is_deleted=False)
    if request.method == "POST":
        operator.is_deleted = True
        operator.updated_by = request.user
        operator.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Collaborateur supprime avec succes.")
        return redirect(redirect_name)
    return HttpResponse("Methode non autorisee.", status=405)


def _mode_degrade_list(request, equipe, active_page, title, add_url_name, edit_url_name):
    items = ModeDegrade.objects.filter(equipe=equipe, is_deleted=False)
    q = (request.GET.get("q") or "").strip()
    if q:
        items = items.filter(
            Q(action__icontains=q) | Q(probleme__icontains=q) | Q(pilote__icontains=q) | Q(cause__icontains=q)
        )
    for field in ("shift", "statut"):
        value = (request.GET.get(field) or "").strip()
        if value:
            items = items.filter(**{field: value})
    if request.GET.get("date"):
        items = items.filter(date=request.GET["date"].strip())
    sort = request.GET.get("sort", "-date")
    if sort.lstrip("-") not in {"date", "shift", "statut", "delai", "pilote"}:
        sort = "-date"
    items = items.order_by(sort)

    export_format = (request.GET.get("export") or "").lower().strip()
    if export_format in {"csv", "excel"}:
        headers = ["Shift", "Action", "Probleme", "Pilote", "Date", "Delai", "Cause", "Statut"]
        rows = [
            [i.shift, i.action, i.probleme, i.pilote, i.date.strftime("%Y-%m-%d"), i.delai.strftime("%Y-%m-%d"), i.cause, i.statut]
            for i in items
        ]
        if export_format == "csv":
            import csv

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="mode_degrade_{equipe.lower()}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = f"Mode degrade {equipe}"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="mode_degrade_{equipe.lower()}.xlsx"'
        workbook.save(response)
        return response

    page_obj = Paginator(items, 15).get_page(request.GET.get("page") or 1)
    context = page_context(active_page, title)
    context.update(
        {
            "items": page_obj,
            "equipe_value": equipe,
            "add_url_name": add_url_name,
            "edit_url_name": edit_url_name,
            "detail_url_name": f"{active_page}_detail",
            "delete_url_name": f"{active_page}_delete",
        }
    )
    return render(request, "app/mode_degrade/list.html", context)


def _mode_degrade_add(request, equipe, active_page, title, success_message, redirect_name):
    form = ModeDegradeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = equipe
        obj.updated_by = request.user
        obj.save()
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update({"form": form, "return_url_name": redirect_name})
    return render(request, "app/mode_degrade/form.html", context)


def _mode_degrade_edit(request, pk, equipe, active_page, title, success_message, redirect_name):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe=equipe, is_deleted=False)
    form = ModeDegradeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = equipe
        obj.updated_by = request.user
        obj.save()
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update({"form": form, "return_url_name": redirect_name})
    return render(request, "app/mode_degrade/form.html", context)


def _mode_degrade_detail(request, pk, equipe, active_page, title):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe=equipe, is_deleted=False)
    context = page_context(active_page, title)
    context["item"] = item
    context["return_url_name"] = active_page
    return render(request, "app/mode_degrade/detail.html", context)


def _mode_degrade_delete(request, pk, equipe, redirect_name):
    item = get_object_or_404(ModeDegrade, pk=pk, equipe=equipe, is_deleted=False)
    if request.method == "POST":
        item.is_deleted = True
        item.updated_by = request.user
        item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Element mode degrade supprime avec succes.")
        return redirect(redirect_name)
    return HttpResponse("Methode non autorisee.", status=405)


@require_role_action("read")
def berceau_mode_degrade(request):
    return _mode_degrade_list(
        request=request,
        equipe="Berceau",
        active_page="berceau_mode_degrade",
        title="Mode Degrade - Berceau",
        add_url_name="berceau_mode_degrade_add",
        edit_url_name="berceau_mode_degrade_edit",
    )


@require_role_action("create")
def berceau_mode_degrade_add(request):
    return _mode_degrade_add(
        request=request,
        equipe="Berceau",
        active_page="berceau_mode_degrade",
        title="Ajouter mode degrade - Berceau",
        success_message="Element mode degrade Berceau ajoute avec succes.",
        redirect_name="berceau_mode_degrade",
    )


@require_role_action("update")
def berceau_mode_degrade_edit(request, pk):
    return _mode_degrade_edit(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_mode_degrade",
        title="Modifier mode degrade - Berceau",
        success_message="Element mode degrade Berceau modifie avec succes.",
        redirect_name="berceau_mode_degrade",
    )


@require_role_action("read")
def berceau_mode_degrade_detail(request, pk):
    return _mode_degrade_detail(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_mode_degrade",
        title="Detail mode degrade - Berceau",
    )


@require_role_action("delete")
def berceau_mode_degrade_delete(request, pk):
    return _mode_degrade_delete(
        request=request,
        pk=pk,
        equipe="Berceau",
        redirect_name="berceau_mode_degrade",
    )


@require_role_action("read")
def berceau_effectif(request):
    return _effectif_list(
        request=request,
        equipe="Berceau",
        active_page="berceau_effectif",
        title="Effectif - Berceau",
        add_url_name="berceau_effectif_add",
        edit_url_name="berceau_effectif_edit",
    )


@require_role_action("create")
def berceau_effectif_add(request):
    return _effectif_add(
        request=request,
        equipe="Berceau",
        active_page="berceau_effectif",
        title="Ajouter un operateur - Berceau",
        success_message="Operateur Berceau ajoute avec succes.",
        redirect_name="berceau_effectif",
    )


@require_role_action("update")
def berceau_effectif_edit(request, pk):
    return _effectif_edit(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_effectif",
        title="Modifier un operateur - Berceau",
        success_message="Operateur Berceau modifie avec succes.",
        redirect_name="berceau_effectif",
    )


@require_role_action("read")
def berceau_effectif_detail(request, pk):
    return _effectif_detail(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_effectif",
        title="Detail collaborateur - Berceau",
    )


@require_role_action("delete")
def berceau_effectif_delete(request, pk):
    return _effectif_delete(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_effectif",
        redirect_name="berceau_effectif",
    )


def berceau_stock(request):
    return _placeholder(request, "app/berceau/stock.html", "berceau_stock", "Stock")


def berceau_arret(request):
    return _placeholder(request, "app/berceau/arret.html", "berceau_arret", "Arret")


def ccb_production(request):
    queryset = ProductionCCB.objects.all()
    selected_shift = request.GET.get("shift", "")
    if selected_shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=selected_shift)
    context = page_context("ccb_production", "Production CCB")
    context["productions"] = queryset
    context["shift_filter"] = selected_shift
    context["shift_choices"] = ProductionCCB.SHIFT_CHOICES
    return render(request, "app/ccb/production_list.html", context)


def ccb_production_export(request):
    queryset = ProductionCCB.objects.all()
    selected_shift = request.GET.get("shift", "")
    if selected_shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=selected_shift)
    export_format = (request.GET.get("format") or "").lower().strip()

    rows = []
    for item in queryset:
        row = [
            item.date.strftime("%Y-%m-%d"),
            item.shift,
            item.objectif,
            item.volume,
            item.rebut,
            item.retouche,
            item.ro_percent,
            item.temps_arrets,
        ]
        for h in range(1, 9):
            row.extend(
                [
                    getattr(item, f"production_h{h}", 0) or 0,
                    getattr(item, f"rebut_h{h}", 0) or 0,
                ]
            )
        rows.append(row)

    headers = [
        "Date",
        "Shift",
        "Objectif",
        "Volume",
        "Rebut",
        "Retouche",
        "RO (%)",
        "Temps d'arrets",
    ]
    for h in range(1, 9):
        headers.append(f"Production H{h}")
        headers.append(f"Rebut H{h}")

    if export_format == "excel":
        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Production CCB"
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 28)

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="production_ccb.xlsx"'
            workbook.save(response)
            return response
        except Exception:
            logger.exception("Excel export failed for CCB")
            return HttpResponse("Une erreur est survenue lors de l'export Excel.", status=500)

    if export_format == "pdf":
        try:
            buffer = io.BytesIO()
            document = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=1 * cm,
                rightMargin=1 * cm,
                topMargin=1 * cm,
                bottomMargin=1 * cm,
            )
            table_data = [headers] + rows
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4FA3")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5E2F6")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.whitesmoke, colors.HexColor("#F5F9FF")],
                        ),
                    ]
                )
            )
            document.build([table])
            pdf = buffer.getvalue()
            buffer.close()

            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="production_ccb.pdf"'
            response.write(pdf)
            return response
        except Exception:
            logger.exception("PDF export failed for CCB")
            return HttpResponse("Une erreur est survenue lors de l'export PDF.", status=500)

    return HttpResponseBadRequest("Format d'export non supporte.")


def ccb_production_add(request):
    form = ProductionCCBForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production CCB ajoutee avec succes.")
        return redirect("ccb_production")
    context = page_context("ccb_production", "Ajouter une production CCB")
    context["form"] = form
    return render(request, "app/ccb/production_form.html", context)


def ccb_production_edit(request, pk):
    obj = get_object_or_404(ProductionCCB, pk=pk)
    form = ProductionCCBForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production CCB modifiee avec succes.")
        return redirect("ccb_production")
    context = page_context("ccb_production", "Modifier une production CCB")
    context.update({"form": form, "production": obj})
    return render(request, "app/ccb/production_form.html", context)


def ccb_production_detail(request, pk):
    obj = get_object_or_404(ProductionCCB, pk=pk)
    context = page_context("ccb_production", "Detail production CCB")
    context["production"] = obj
    return render(request, "app/ccb/production_detail.html", context)


def ccb_production_delete(request, pk):
    obj = get_object_or_404(ProductionCCB, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Production CCB supprimee avec succes.")
        return redirect("ccb_production")
    return HttpResponse("Methode non autorisee.", status=405)


@require_role_action("read")
def ccb_mode_degrade(request):
    return _mode_degrade_list(
        request=request,
        equipe="CCB",
        active_page="ccb_mode_degrade",
        title="Mode Degrade - CCB",
        add_url_name="ccb_mode_degrade_add",
        edit_url_name="ccb_mode_degrade_edit",
    )


@require_role_action("create")
def ccb_mode_degrade_add(request):
    return _mode_degrade_add(
        request=request,
        equipe="CCB",
        active_page="ccb_mode_degrade",
        title="Ajouter mode degrade - CCB",
        success_message="Element mode degrade CCB ajoute avec succes.",
        redirect_name="ccb_mode_degrade",
    )


@require_role_action("update")
def ccb_mode_degrade_edit(request, pk):
    return _mode_degrade_edit(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_mode_degrade",
        title="Modifier mode degrade - CCB",
        success_message="Element mode degrade CCB modifie avec succes.",
        redirect_name="ccb_mode_degrade",
    )


@require_role_action("read")
def ccb_mode_degrade_detail(request, pk):
    return _mode_degrade_detail(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_mode_degrade",
        title="Detail mode degrade - CCB",
    )


@require_role_action("delete")
def ccb_mode_degrade_delete(request, pk):
    return _mode_degrade_delete(
        request=request,
        pk=pk,
        equipe="CCB",
        redirect_name="ccb_mode_degrade",
    )


@require_role_action("read")
def ccb_effectif(request):
    return _effectif_list(
        request=request,
        equipe="CCB",
        active_page="ccb_effectif",
        title="Effectif - CCB",
        add_url_name="ccb_effectif_add",
        edit_url_name="ccb_effectif_edit",
    )


@require_role_action("create")
def ccb_effectif_add(request):
    return _effectif_add(
        request=request,
        equipe="CCB",
        active_page="ccb_effectif",
        title="Ajouter un operateur - CCB",
        success_message="Operateur CCB ajoute avec succes.",
        redirect_name="ccb_effectif",
    )


@require_role_action("update")
def ccb_effectif_edit(request, pk):
    return _effectif_edit(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_effectif",
        title="Modifier un operateur - CCB",
        success_message="Operateur CCB modifie avec succes.",
        redirect_name="ccb_effectif",
    )


@require_role_action("read")
def ccb_effectif_detail(request, pk):
    return _effectif_detail(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_effectif",
        title="Detail collaborateur - CCB",
    )


@require_role_action("delete")
def ccb_effectif_delete(request, pk):
    return _effectif_delete(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_effectif",
        redirect_name="ccb_effectif",
    )


def ccb_stock(request):
    return _placeholder(request, "app/ccb/stock.html", "ccb_stock", "Stock CCB")


def ccb_arret(request):
    return _placeholder(request, "app/ccb/arret.html", "ccb_arret", "Arret CCB")


def _absence_list(request, equipe, active_page, title, add_url_name, edit_url_name):
    absences = (
        Absence.objects.filter(equipe=equipe, is_deleted=False)
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
    date_absence = (request.GET.get("date_absence") or "").strip()
    if date_absence:
        absences = absences.filter(date_absence=date_absence)
    if request.GET.get("matricule"):
        matricule_filter = request.GET["matricule"].strip()
        absences = absences.filter(effectif__matricule__icontains=matricule_filter)
    if request.GET.get("nom"):
        nom_filter = request.GET["nom"].strip()
        absences = absences.filter(
            Q(effectif__nom_complet__icontains=nom_filter) | Q(nom_complet__icontains=nom_filter)
        )
    shift = (request.GET.get("shift") or "").strip()
    if shift in {"A", "B", "N"}:
        absences = absences.filter(shift=shift)
    effectif_filter = (request.GET.get("effectif") or "").strip()
    if effectif_filter.isdigit():
        absences = absences.filter(effectif_id=int(effectif_filter))

    sort = request.GET.get("sort", "-date_absence")
    allowed_sort = {"date_absence", "shift", "effectif__nom_complet", "motif", "created_at"}
    if sort.lstrip("-") not in allowed_sort:
        sort = "-date_absence"
    absences = absences.order_by(sort)

    export_format = (request.GET.get("export") or "").lower().strip()
    if export_format in {"csv", "excel"}:
        headers = ["Nom absent", "Shift", "Date absence", "Motif", "Remplacant", "Cree le"]
        rows = [
            [
                item.absent_nom,
                item.shift,
                item.date_absence.strftime("%Y-%m-%d"),
                item.motif,
                item.remplacant_nom,
                item.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
            for item in absences
        ]
        if export_format == "csv":
            import csv

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="absences_{equipe.lower()}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = f"Absences {equipe}"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="absences_{equipe.lower()}.xlsx"'
        workbook.save(response)
        return response

    page_obj = Paginator(absences, 15).get_page(request.GET.get("page") or 1)
    context = page_context(active_page, title)
    context.update(
        {
            "absences": page_obj,
            "equipe_value": equipe,
            "add_url_name": add_url_name,
            "edit_url_name": edit_url_name,
            "detail_url_name": f"{active_page}_detail",
            "delete_url_name": f"{active_page}_delete",
            "query": query,
            "sort": sort,
            "shift_filter": shift,
            "effectif_filter": effectif_filter,
            "effectif_options": OperateurEffectif.objects.filter(equipe=equipe, is_deleted=False)
            .order_by("nom_complet")
            .values("id", "nom_complet"),
        }
    )
    return render(request, "app/absence/list.html", context)


def _absence_add(request, equipe, active_page, title, success_message, redirect_name):
    form = AbsenceForm(request.POST or None)
    form.fields["effectif"].queryset = OperateurEffectif.objects.filter(equipe=equipe, is_deleted=False).order_by("nom_complet")
    form.fields["remplacant_effectif"].queryset = form.fields["effectif"].queryset
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = equipe
        obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
        obj.updated_by = request.user
        obj.save()
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update({"form": form, "return_url_name": redirect_name})
    return render(request, "app/absence/form.html", context)


def _absence_edit(request, pk, equipe, active_page, title, success_message, redirect_name):
    absence = get_object_or_404(Absence, pk=pk, equipe=equipe, is_deleted=False)
    form = AbsenceForm(request.POST or None, instance=absence)
    form.fields["effectif"].queryset = OperateurEffectif.objects.filter(equipe=equipe, is_deleted=False).order_by("nom_complet")
    form.fields["remplacant_effectif"].queryset = form.fields["effectif"].queryset
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.equipe = equipe
        obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
        obj.updated_by = request.user
        obj.save()
        messages.success(request, success_message)
        return redirect(redirect_name)
    context = page_context(active_page, title)
    context.update({"form": form, "return_url_name": redirect_name})
    return render(request, "app/absence/form.html", context)


def _absence_detail(request, pk, equipe, active_page, title):
    absence = get_object_or_404(
        Absence.objects.select_related("effectif", "remplacant_effectif"),
        pk=pk,
        equipe=equipe,
        is_deleted=False,
    )
    context = page_context(active_page, title)
    context["absence"] = absence
    context["return_url_name"] = active_page
    return render(request, "app/absence/detail.html", context)


def _absence_delete(request, pk, equipe, redirect_name):
    absence = get_object_or_404(Absence, pk=pk, equipe=equipe, is_deleted=False)
    if request.method == "POST":
        absence.is_deleted = True
        absence.updated_by = request.user
        absence.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        messages.success(request, "Absence supprimee avec succes.")
        return redirect(redirect_name)
    return HttpResponse("Methode non autorisee.", status=405)


@require_role_action("read")
def berceau_absence(request):
    return _absence_list(
        request=request,
        equipe="Berceau",
        active_page="berceau_absence",
        title="Absence - Berceau",
        add_url_name="berceau_absence_add",
        edit_url_name="berceau_absence_edit",
    )


@require_role_action("create")
def berceau_absence_add(request):
    return _absence_add(
        request=request,
        equipe="Berceau",
        active_page="berceau_absence",
        title="Ajouter une absence - Berceau",
        success_message="Absence Berceau ajoutee avec succes.",
        redirect_name="berceau_absence",
    )


@require_role_action("update")
def berceau_absence_edit(request, pk):
    return _absence_edit(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_absence",
        title="Modifier une absence - Berceau",
        success_message="Absence Berceau modifiee avec succes.",
        redirect_name="berceau_absence",
    )


@require_role_action("read")
def berceau_absence_detail(request, pk):
    return _absence_detail(
        request=request,
        pk=pk,
        equipe="Berceau",
        active_page="berceau_absence",
        title="Detail absence - Berceau",
    )


@require_role_action("delete")
def berceau_absence_delete(request, pk):
    return _absence_delete(
        request=request,
        pk=pk,
        equipe="Berceau",
        redirect_name="berceau_absence",
    )


@require_role_action("read")
def ccb_absence(request):
    return _absence_list(
        request=request,
        equipe="CCB",
        active_page="ccb_absence",
        title="Absence - CCB",
        add_url_name="ccb_absence_add",
        edit_url_name="ccb_absence_edit",
    )


@require_role_action("create")
def ccb_absence_add(request):
    return _absence_add(
        request=request,
        equipe="CCB",
        active_page="ccb_absence",
        title="Ajouter une absence - CCB",
        success_message="Absence CCB ajoutee avec succes.",
        redirect_name="ccb_absence",
    )


@require_role_action("update")
def ccb_absence_edit(request, pk):
    return _absence_edit(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_absence",
        title="Modifier une absence - CCB",
        success_message="Absence CCB modifiee avec succes.",
        redirect_name="ccb_absence",
    )


@require_role_action("read")
def ccb_absence_detail(request, pk):
    return _absence_detail(
        request=request,
        pk=pk,
        equipe="CCB",
        active_page="ccb_absence",
        title="Detail absence - CCB",
    )


@require_role_action("delete")
def ccb_absence_delete(request, pk):
    return _absence_delete(
        request=request,
        pk=pk,
        equipe="CCB",
        redirect_name="ccb_absence",
    )


def _api_absences_queryset(request):
    queryset = Absence.objects.filter(is_deleted=False).select_related("effectif", "remplacant_effectif")
    for field in ("equipe", "shift", "effectif"):
        value = (request.GET.get(field) or "").strip()
        if value:
            queryset = queryset.filter(**{field: value})
    q = (request.GET.get("q") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(effectif__nom_complet__icontains=q)
            | Q(motif__icontains=q)
            | Q(remplacant__icontains=q)
            | Q(remplacant_effectif__nom_complet__icontains=q)
        )
    date_absence = (request.GET.get("date_absence") or "").strip()
    if date_absence:
        queryset = queryset.filter(date_absence=date_absence)
    if request.GET.get("matricule"):
        matricule_filter = request.GET["matricule"].strip()
        queryset = queryset.filter(effectif__matricule__icontains=matricule_filter)
    if request.GET.get("nom"):
        nom_filter = request.GET["nom"].strip()
        queryset = queryset.filter(
            Q(effectif__nom_complet__icontains=nom_filter) | Q(nom_complet__icontains=nom_filter)
        )
    sort = request.GET.get("sort", "-date_absence")
    if sort.lstrip("-") not in {"date_absence", "shift", "effectif__nom_complet", "motif", "created_at"}:
        sort = "-date_absence"
    queryset = queryset.order_by(sort)
    queryset = restrict_psp_scope(request.user, queryset, shift_field="shift", equipe_field="equipe")
    # PSP: only absences for their team (psp_lead == PSP effectif) — même résolution que /api/auth/me/ (fallback username).
    if is_psp(request.user):
        lead_id = get_psp_effectif_id(request.user)
        if lead_id:
            queryset = queryset.filter(Q(effectif_id=lead_id) | Q(effectif__psp_lead_id=lead_id))
        else:
            queryset = queryset.none()
    return queryset


@require_role_action("read")
def api_absences(request):
    try:
        if request.method == "POST":
            if not auth_can_do_action(request.user, "create"):
                return HttpResponse("Acces refuse.", status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            equipe_val = payload.get("equipe") or "Berceau"
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_absences POST"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_absences POST"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            if not ensure_psp_absence_effectifs_allowed(
                request.user,
                effectif_id=payload.get("effectif"),
                remplacant_effectif_id=payload.get("remplacant_effectif"),
                equipe=equipe_val,
                shift=shift_val or None,
                endpoint="api_absences POST",
            ):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            instance = Absence(equipe=equipe_val)
            form = AbsenceForm(payload, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = payload.get("equipe") or obj.equipe
                obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
                obj.updated_by = request.user if request.user.is_authenticated else None
                obj.save()
                return JsonResponse({"id": obj.id}, status=201)
            return JsonResponse({"errors": form.errors}, status=400)

        if request.method == "GET":
            queryset = _api_absences_queryset(request)
            export_format = (request.GET.get("export") or "").lower().strip()
            if export_format in {"csv", "excel"}:
                headers = ["Nom absent", "Shift", "Date absence", "Motif", "Remplacant", "Cree le"]
                rows = [
                    [
                        item.absent_nom,
                        item.shift,
                        item.date_absence.strftime("%Y-%m-%d"),
                        item.motif,
                        item.remplacant_nom,
                        item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "",
                    ]
                    for item in queryset[:5000]
                ]
                if export_format == "csv":
                    import csv

                    response = HttpResponse(content_type="text/csv; charset=utf-8")
                    response["Content-Disposition"] = 'attachment; filename="absences.csv"'
                    writer = csv.writer(response)
                    writer.writerow(headers)
                    writer.writerows(rows)
                    return response

                workbook = Workbook()
                sheet = workbook.active
                sheet.title = "Absences"
                sheet.append(headers)
                for row in rows:
                    sheet.append(row)
                response = HttpResponse(
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = 'attachment; filename="absences.xlsx"'
                workbook.save(response)
                return response

            page = int(request.GET.get("page") or 1)
            per_page = min(int(request.GET.get("per_page") or 20), 100)
            page_obj = Paginator(queryset, per_page).get_page(page)
            return JsonResponse(
                {
                    "results": [
                        model_to_dict(
                            item,
                            fields=[
                                "id",
                                "equipe",
                                "effectif",
                                "remplacant_effectif",
                                "shift",
                                "motif",
                                "nom_complet",
                                "remplacant",
                                "commentaire",
                                "date_absence",
                                "created_at",
                                "migration_status",
                                "migration_note",
                            ],
                        )
                        | {
                            "nom_absent": item.absent_nom,
                            "nom_remplacant": item.remplacant_nom,
                        }
                        for item in page_obj
                    ],
                    "page": page_obj.number,
                    "pages": page_obj.paginator.num_pages,
                    "total": page_obj.paginator.count,
                }
            )
        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API absences")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)


@require_role_action("read")
def api_absence_detail(request, pk):
    try:
        item = get_object_or_404(Absence, pk=pk, is_deleted=False)
        if request.method == "GET":
            if not ensure_psp_object_access(request.user, item, endpoint="api_absence_detail GET"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            return JsonResponse(
                model_to_dict(
                    item,
                    fields=[
                        "id",
                        "equipe",
                        "effectif",
                        "remplacant_effectif",
                        "shift",
                        "motif",
                        "nom_complet",
                        "remplacant",
                        "commentaire",
                        "date_absence",
                        "created_at",
                        "migration_status",
                        "migration_note",
                    ],
                )
                | {"nom_absent": item.absent_nom, "nom_remplacant": item.remplacant_nom}
            )
        if request.method in {"PUT", "PATCH"}:
            if not auth_can_do_action(request.user, "update"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_absence_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            equipe_val = payload.get("equipe") or item.equipe
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_absence_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or item.shift or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_absence_detail PATCH"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            if not ensure_psp_absence_effectifs_allowed(
                request.user,
                effectif_id=payload.get("effectif", item.effectif_id),
                remplacant_effectif_id=payload.get("remplacant_effectif", item.remplacant_effectif_id),
                equipe=equipe_val,
                shift=shift_val or None,
                endpoint="api_absence_detail PATCH",
            ):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            data = model_to_dict(item)
            data.update(payload)
            form = AbsenceForm(data, instance=item)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = payload.get("equipe") or item.equipe
                obj.nom_complet = obj.effectif.nom_complet if obj.effectif_id else obj.nom_complet
                obj.updated_by = request.user if request.user.is_authenticated else None
                obj.save()
                return JsonResponse({"id": obj.id})
            return JsonResponse({"errors": form.errors}, status=400)
        if request.method == "DELETE":
            if not auth_can_do_action(request.user, "delete"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_absence_detail DELETE"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            item.is_deleted = True
            item.updated_by = request.user if request.user.is_authenticated else None
            item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
            return JsonResponse({"deleted": True})
        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API absence detail")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)


def _api_mode_degrade_queryset(request):
    queryset = ModeDegrade.objects.filter(is_deleted=False)
    for field in ("equipe", "shift", "statut"):
        value = (request.GET.get(field) or "").strip()
        if value:
            queryset = queryset.filter(**{field: value})
    if request.GET.get("date"):
        queryset = queryset.filter(date=request.GET["date"].strip())
    q = (request.GET.get("q") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(action__icontains=q) | Q(probleme__icontains=q) | Q(pilote__icontains=q) | Q(cause__icontains=q)
        )
    sort = request.GET.get("sort", "-date")
    if sort.lstrip("-") not in {"date", "shift", "statut", "delai", "pilote"}:
        sort = "-date"
    queryset = queryset.order_by(sort)
    return restrict_psp_scope(request.user, queryset, shift_field="shift", equipe_field="equipe")


@require_role_action("read")
def api_mode_degrade(request):
    try:
        if request.method == "POST":
            if not auth_can_do_action(request.user, "create"):
                return HttpResponse("Acces refuse.", status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            equipe_val = payload.get("equipe") or "Berceau"
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_mode_degrade POST"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_mode_degrade POST"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            instance = ModeDegrade(equipe=equipe_val)
            form = ModeDegradeForm(payload, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = equipe_val
                obj.updated_by = request.user if request.user.is_authenticated else None
                obj.save()
                return JsonResponse({"id": obj.id}, status=201)
            return JsonResponse({"errors": form.errors}, status=400)
        if request.method == "GET":
            queryset = _api_mode_degrade_queryset(request)
            export_format = (request.GET.get("export") or "").lower().strip()
            if export_format in {"csv", "excel"}:
                equipe_val = (request.GET.get("equipe") or "").strip()
                if equipe_val not in {"Berceau", "CCB"}:
                    return JsonResponse({"error": "Parametre equipe requis pour l'export."}, status=400)
                if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_mode_degrade GET export"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
                headers = ["Shift", "Action", "Probleme", "Pilote", "Date", "Delai", "Cause", "Statut"]
                rows = [
                    [
                        i.shift,
                        i.action,
                        i.probleme,
                        i.pilote,
                        i.date.strftime("%Y-%m-%d"),
                        i.delai.strftime("%Y-%m-%d"),
                        i.cause,
                        i.statut,
                    ]
                    for i in queryset[:5000]
                ]
                if export_format == "csv":
                    import csv

                    response = HttpResponse(content_type="text/csv")
                    response["Content-Disposition"] = f'attachment; filename="mode_degrade_{equipe_val.lower()}.csv"'
                    writer = csv.writer(response)
                    writer.writerow(headers)
                    writer.writerows(rows)
                    return response
                workbook = Workbook()
                sheet = workbook.active
                sheet.title = f"Mode degrade {equipe_val}"
                sheet.append(headers)
                for row in rows:
                    sheet.append(row)
                response = HttpResponse(
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="mode_degrade_{equipe_val.lower()}.xlsx"'
                )
                workbook.save(response)
                return response
            page = int(request.GET.get("page") or 1)
            per_page = min(int(request.GET.get("per_page") or 20), 100)
            page_obj = Paginator(queryset, per_page).get_page(page)
            return JsonResponse(
                {
                    "results": [
                        model_to_dict(
                            item,
                            fields=["id", "equipe", "shift", "action", "probleme", "pilote", "date", "delai", "cause", "statut", "created_at"],
                        )
                        for item in page_obj
                    ],
                    "page": page_obj.number,
                    "pages": page_obj.paginator.num_pages,
                    "total": page_obj.paginator.count,
                }
            )
        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API mode degrade")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)


@require_role_action("read")
def api_mode_degrade_detail(request, pk):
    try:
        item = get_object_or_404(ModeDegrade, pk=pk, is_deleted=False)
        if request.method == "GET":
            if not ensure_psp_object_access(request.user, item, endpoint="api_mode_degrade_detail GET"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            return JsonResponse(
                model_to_dict(
                    item,
                    fields=["id", "equipe", "shift", "action", "probleme", "pilote", "date", "delai", "cause", "statut", "created_at"],
                )
            )
        if request.method in {"PUT", "PATCH"}:
            if not auth_can_do_action(request.user, "update"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_mode_degrade_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            equipe_val = payload.get("equipe") or item.equipe
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_mode_degrade_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or item.shift or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_mode_degrade_detail PATCH"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            data = model_to_dict(item)
            data.update(payload)
            form = ModeDegradeForm(data, instance=item)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = payload.get("equipe") or item.equipe
                obj.updated_by = request.user if request.user.is_authenticated else None
                obj.save()
                return JsonResponse({"id": obj.id})
            return JsonResponse({"errors": form.errors}, status=400)
        if request.method == "DELETE":
            if not auth_can_do_action(request.user, "delete"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_mode_degrade_detail DELETE"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            item.is_deleted = True
            item.updated_by = request.user if request.user.is_authenticated else None
            item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
            return JsonResponse({"deleted": True})
        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API mode degrade detail")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)


def _api_effectifs_queryset(request):
    queryset = OperateurEffectif.objects.filter(is_deleted=False).select_related("psp_lead")
    for field in ("equipe", "shift", "type_contrat", "sexe", "ville_actuelle", "specialite", "fonction"):
        value = (request.GET.get(field) or "").strip()
        if value:
            queryset = queryset.filter(**{field: value})
    q = (request.GET.get("q") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(nom_complet__icontains=q)
            | Q(cin__icontains=q)
            | Q(identifiant__icontains=q)
            | Q(matricule__icontains=q)
        )
    sort = request.GET.get("sort", "nom_complet")
    sort_key = sort.lstrip("-")
    if sort_key == "shift_sections":
        queryset = queryset.annotate(
            _psp_first=Case(
                When(fonction="PSP", then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("shift", "_psp_first", "nom_complet")
    elif sort_key not in {"nom_complet", "cin", "identifiant", "matricule", "type_contrat", "shift", "date_entree"}:
        sort = "nom_complet"
        queryset = queryset.order_by(sort)
    else:
        queryset = queryset.order_by(sort)
    queryset = restrict_psp_scope(request.user, queryset, shift_field="shift", equipe_field="equipe")
    # PSP: leur fiche + équipe (psp_lead) — lead_id via get_psp_effectif_id (aligné authz /api/auth/me/).
    if is_psp(request.user):
        lead_id = get_psp_effectif_id(request.user)
        if lead_id:
            queryset = queryset.filter(Q(pk=lead_id) | Q(psp_lead_id=lead_id))
        else:
            queryset = queryset.none()
    return queryset


def _psp_login_username_map(effectif_ids: list[int]) -> dict[int, str]:
    if not effectif_ids:
        return {}
    out: dict[int, str] = {}
    for p in UserAccessProfile.objects.filter(
        effectif_id__in=effectif_ids,
        role=UserAccessProfile.Role.PSP,
    ).select_related("user"):
        out[p.effectif_id] = p.user.username
    return out


def _apply_psp_login_link_from_payload(request, *, effectif_row: OperateurEffectif, payload: dict) -> str | None:
    """RU/ADMIN : ``psp_linked_username`` lie le compte Django PSP à cette fiche (efface si chaîne vide)."""
    if not is_admin_or_ru(request.user):
        return None
    if "psp_linked_username" not in payload:
        return None
    if (effectif_row.fonction or "").strip().upper() != "PSP":
        return "Le lien compte ne s'applique qu'aux fiches PSP."

    username = (payload.get("psp_linked_username") or "").strip()
    User = get_user_model()

    if not username:
        UserAccessProfile.objects.filter(effectif_id=effectif_row.pk, role=UserAccessProfile.Role.PSP).update(
            effectif=None
        )
        return None

    user = User.objects.filter(username__iexact=username).first()
    if not user:
        return "Compte Django introuvable (identifiant de connexion inexistant)."

    existing = UserAccessProfile.objects.filter(user=user).first()
    if existing and existing.role != UserAccessProfile.Role.PSP:
        return f"Le compte « {username} » a déjà le rôle {existing.role}. Utilisez un utilisateur dédié PSP."

    UserAccessProfile.objects.filter(effectif_id=effectif_row.pk).exclude(user=user).update(effectif=None)
    UserAccessProfile.objects.update_or_create(
        user=user,
        defaults={"role": UserAccessProfile.Role.PSP, "effectif": effectif_row},
    )
    return None


def _sync_psp_team_shift_if_needed(*, request, old_shift: str, saved_item: OperateurEffectif):
    """
    Si le shift d'une fiche PSP change : déplace uniquement les opérateurs déjà rattachés via ``psp_lead``.
    Met à jour les absences (shift) pour le PSP et ces membres.
    """
    if old_shift == saved_item.shift:
        return 0
    if (saved_item.fonction or "").strip().upper() != "PSP":
        return 0

    qs = OperateurEffectif.objects.filter(
        psp_lead_id=saved_item.id,
        is_deleted=False,
    ).exclude(pk=saved_item.id)
    member_ids = list(qs.values_list("pk", flat=True))

    new_shift = saved_item.shift
    updated = qs.update(shift=new_shift, updated_by=request.user)

    affected_effectif_ids = [saved_item.id] + member_ids
    Absence.objects.filter(effectif_id__in=affected_effectif_ids, is_deleted=False).update(shift=new_shift)

    if updated:
        logger.info(
            "psp_team_shift_sync psp_effectif_id=%s old_shift=%s new_shift=%s members_updated=%s by_user_id=%s",
            saved_item.id,
            old_shift,
            new_shift,
            updated,
            getattr(request.user, "id", None),
        )
    return updated


def _resolve_psp_lead_id(raw_lead_id, equipe_val):
    if raw_lead_id in (None, "", 0, "0"):
        return None, None
    if not str(raw_lead_id).isdigit():
        return None, "psp_lead invalide."
    lead_id = int(raw_lead_id)
    lead = OperateurEffectif.objects.filter(pk=lead_id, is_deleted=False).first()
    if not lead:
        return None, "PSP responsable introuvable."
    if lead.equipe != equipe_val:
        return None, "Le PSP responsable doit appartenir a la meme equipe."
    fn = (lead.fonction or "").strip().upper()
    has_login_psp = UserAccessProfile.objects.filter(
        role=UserAccessProfile.Role.PSP,
        effectif_id=lead_id,
    ).exists()
    # Accept PSP d'effectif (fonction PSP) même sans compte utilisateur — sinon impossible d'assigner une équipe importée.
    if fn != "PSP" and not has_login_psp:
        return None, "Le responsable doit avoir la fonction PSP (ou un profil utilisateur PSP lie)."
    return lead_id, None


def _normalize_fonction_value(raw_value):
    val = str(raw_value or "").strip().upper()
    if val in {"OPERATEUR", "OPERATOR", "OPERATEUR(E)", "OPERATEURS", "OPERATEURS(E)"}:
        return "OPERATEUR"
    if val in {"OPERATEUR", "OPERATEUR "}:
        return "OPERATEUR"
    if val == "PSP":
        return "PSP"
    if val in {"RU", "R.U", "RESPONSABLE UNITE", "RESPONSABLE D'UNITE", "RESPONSABLE D’UNITE", "RESPONSABLE"}:
        return "OPERATEUR"
    if str(raw_value or "").strip().lower() == "operateur":
        return "OPERATEUR"
    return raw_value


@require_role_action("read")
def api_effectifs(request):
    try:
        if request.method == "POST":
            if not auth_can_do_action(request.user, "create"):
                return HttpResponse("Acces refuse.", status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            payload["fonction"] = _normalize_fonction_value(payload.get("fonction"))
            equipe_val = payload.get("equipe") or "Berceau"
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_effectifs POST"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_effectifs POST"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            if not ensure_psp_effectif_write_allowed(
                request.user,
                payload=payload,
                endpoint="api_effectifs POST",
            ):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            if is_psp(request.user):
                lead_id = get_psp_effectif_id(request.user)
                if lead_id:
                    payload = {**payload, "psp_lead": lead_id}
            form = OperateurEffectifForm(payload)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = equipe_val
                obj.updated_by = request.user if request.user.is_authenticated else None
                lead_id, lead_err = _resolve_psp_lead_id(payload.get("psp_lead"), equipe_val)
                if lead_err:
                    return JsonResponse({"errors": {"psp_lead": [lead_err]}}, status=400)
                obj.psp_lead_id = lead_id
                # If operator is assigned to a PSP lead, force operator shift to lead's shift.
                if lead_id:
                    lead = OperateurEffectif.objects.filter(pk=lead_id, is_deleted=False).only("shift").first()
                    if lead and lead.shift in {"A", "B", "N"}:
                        obj.shift = lead.shift
                obj.save()
                link_err = _apply_psp_login_link_from_payload(request, effectif_row=obj, payload=payload)
                if link_err:
                    return JsonResponse({"errors": {"psp_linked_username": [link_err]}}, status=400)
                return JsonResponse({"id": obj.id}, status=201)
            return JsonResponse({"errors": form.errors}, status=400)

        if request.method == "GET":
            queryset = _api_effectifs_queryset(request)
            export_format = (request.GET.get("export") or "").lower().strip()
            if export_format in {"csv", "excel"}:
                equipe_val = (request.GET.get("equipe") or "").strip()
                if equipe_val not in {"Berceau", "CCB"}:
                    return JsonResponse({"error": "Parametre equipe requis pour l'export."}, status=400)
                if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_effectifs GET export"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
                headers = [
                    "Nom complet",
                    "CIN",
                    "Identifiant",
                    "Matricule",
                    "Type contrat",
                    "Shift",
                    "Fonction",
                    "Ville actuelle",
                    "Date entree",
                ]
                rows = [
                    [
                        item.nom_complet,
                        item.cin,
                        item.identifiant,
                        item.matricule or "",
                        item.type_contrat,
                        item.shift,
                        _normalize_fonction_value(item.fonction),
                        item.ville_actuelle,
                        item.date_entree.strftime("%Y-%m-%d"),
                    ]
                    for item in queryset[:5000]
                ]
                if export_format == "csv":
                    import csv

                    response = HttpResponse(content_type="text/csv")
                    response["Content-Disposition"] = f'attachment; filename="effectif_{equipe_val.lower()}.csv"'
                    writer = csv.writer(response)
                    writer.writerow(headers)
                    writer.writerows(rows)
                    return response
                workbook = Workbook()
                sheet = workbook.active
                sheet.title = f"Effectif {equipe_val}"
                sheet.append(headers)
                for row in rows:
                    sheet.append(row)
                response = HttpResponse(
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = f'attachment; filename="effectif_{equipe_val.lower()}.xlsx"'
                workbook.save(response)
                return response
            page = int(request.GET.get("page") or 1)
            per_page = min(int(request.GET.get("per_page") or 20), 100)
            page_obj = Paginator(queryset, per_page).get_page(page)
            row_ids = [item.id for item in page_obj]
            login_map = _psp_login_username_map(row_ids) if is_admin_or_ru(request.user) else {}
            return JsonResponse(
                {
                    "results": [
                        model_to_dict(
                            item,
                            fields=[
                                "id",
                                "nom_complet",
                                "shift",
                                "cin",
                                "type_contrat",
                                "date_naissance",
                                "sexe",
                                "date_entree",
                                "identifiant",
                                "matricule",
                                "num_tel",
                                "fonction",
                                "ville_actuelle",
                                "niveau_etude",
                                "numero_casier",
                                "parada_transport",
                                "pointure_chaussure",
                                "specialite",
                                "taille_pantalon",
                                "taille_veste",
                                "ville_origine",
                                "equipe",
                                "code_equipe",
                            ],
                        )
                        | {"fonction": _normalize_fonction_value(item.fonction)}
                        | {
                            "psp_lead": item.psp_lead_id,
                            "psp_lead_nom": item.psp_lead.nom_complet if item.psp_lead_id else "",
                        }
                        | (
                            {"psp_linked_username": login_map.get(item.id, "")}
                            if is_admin_or_ru(request.user)
                            else {}
                        )
                        for item in page_obj
                    ],
                    "page": page_obj.number,
                    "pages": page_obj.paginator.num_pages,
                    "total": page_obj.paginator.count,
                }
            )

        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API effectifs")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)


@require_role_action("read")
def api_effectif_options(request):
    equipe = (request.GET.get("equipe") or "").strip()
    fonction = (request.GET.get("fonction") or "").strip()
    queryset = OperateurEffectif.objects.filter(is_deleted=False)
    if equipe:
        queryset = queryset.filter(equipe=equipe)
    if fonction:
        queryset = queryset.filter(fonction=fonction)
    queryset = restrict_psp_scope(request.user, queryset, shift_field="shift", equipe_field="equipe")
    if is_psp(request.user):
        lead_id = get_psp_effectif_id(request.user)
        if lead_id:
            queryset = queryset.filter(Q(pk=lead_id) | Q(psp_lead_id=lead_id))
        else:
            queryset = queryset.none()
    queryset = queryset.annotate(
        _psp_first=Case(
            When(fonction="PSP", then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("shift", "_psp_first", "nom_complet")
    options = [
        {
            "id": item.id,
            "nom_complet": item.nom_complet,
            "shift": item.shift,
            "fonction": _normalize_fonction_value(item.fonction),
            "equipe": item.equipe,
        }
        for item in queryset[:500]
    ]
    return JsonResponse({"results": options})


@require_role_action("read")
def api_effectif_detail(request, pk):
    try:
        item = get_object_or_404(OperateurEffectif, pk=pk, is_deleted=False)
        if request.method == "GET":
            if not ensure_psp_object_access(request.user, item, endpoint="api_effectif_detail GET"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            return JsonResponse(
                model_to_dict(
                    item,
                    fields=[
                        "id",
                        "nom_complet",
                        "shift",
                        "cin",
                        "type_contrat",
                        "date_naissance",
                        "sexe",
                        "date_entree",
                        "identifiant",
                        "matricule",
                        "num_tel",
                        "fonction",
                        "ville_actuelle",
                        "niveau_etude",
                        "numero_casier",
                        "parada_transport",
                        "pointure_chaussure",
                        "specialite",
                        "taille_pantalon",
                        "taille_veste",
                        "ville_origine",
                        "equipe",
                        "code_equipe",
                    ],
                )
                | {"fonction": _normalize_fonction_value(item.fonction)}
                | {
                    "psp_lead": item.psp_lead_id,
                    "psp_lead_nom": item.psp_lead.nom_complet if item.psp_lead_id else "",
                    "psp_linked_username": _psp_login_username_map([item.pk]).get(item.pk, ""),
                }
            )
        if request.method in {"PUT", "PATCH"}:
            if not auth_can_do_action(request.user, "update"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_effectif_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            import json

            payload = json.loads(request.body.decode("utf-8") or "{}")
            payload["fonction"] = _normalize_fonction_value(payload.get("fonction", item.fonction))
            equipe_val = payload.get("equipe") or item.equipe
            if not ensure_equipe_allowed(request.user, equipe_val, endpoint="api_effectif_detail PATCH"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            shift_val = (payload.get("shift") or item.shift or "").strip()
            if shift_val in {"A", "B", "N"}:
                if not ensure_shift_allowed(request.user, shift_val, endpoint="api_effectif_detail PATCH"):
                    return JsonResponse({"error": "Acces refuse."}, status=403)
            if not ensure_psp_effectif_write_allowed(
                request.user,
                payload=payload,
                existing_row_pk=item.pk,
                endpoint="api_effectif_detail PATCH",
            ):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            if is_psp(request.user) and item.pk != get_psp_effectif_id(request.user):
                lead_id = get_psp_effectif_id(request.user)
                if lead_id:
                    payload = {**payload, "psp_lead": lead_id}
            original_shift = item.shift
            data = model_to_dict(item)
            data.update(payload)
            form = OperateurEffectifForm(data, instance=item)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.equipe = equipe_val
                obj.updated_by = request.user if request.user.is_authenticated else None
                lead_id, lead_err = _resolve_psp_lead_id(
                    payload.get("psp_lead", obj.psp_lead_id),
                    equipe_val,
                )
                if lead_err:
                    return JsonResponse({"errors": {"psp_lead": [lead_err]}}, status=400)
                obj.psp_lead_id = lead_id
                # If operator is assigned to a PSP lead, force operator shift to lead's shift.
                if lead_id:
                    lead = OperateurEffectif.objects.filter(pk=lead_id, is_deleted=False).only("shift").first()
                    if lead and lead.shift in {"A", "B", "N"}:
                        obj.shift = lead.shift
                obj.save()
                if original_shift != obj.shift:
                    Absence.objects.filter(effectif_id=obj.pk, is_deleted=False).update(shift=obj.shift)
                impacted = _sync_psp_team_shift_if_needed(
                    request=request,
                    old_shift=original_shift,
                    saved_item=obj,
                )
                link_err = _apply_psp_login_link_from_payload(request, effectif_row=obj, payload=payload)
                if link_err:
                    return JsonResponse({"errors": {"psp_linked_username": [link_err]}}, status=400)
                return JsonResponse({"id": obj.id, "team_shift_updated_count": impacted})
            return JsonResponse({"errors": form.errors}, status=400)
        if request.method == "DELETE":
            if not auth_can_do_action(request.user, "delete"):
                return HttpResponse("Acces refuse.", status=403)
            if not ensure_psp_object_access(request.user, item, endpoint="api_effectif_detail DELETE"):
                return JsonResponse({"error": "Acces refuse."}, status=403)
            item.is_deleted = True
            item.updated_by = request.user if request.user.is_authenticated else None
            item.save(update_fields=["is_deleted", "updated_by", "updated_at"])
            return JsonResponse({"deleted": True})
        return HttpResponse(status=405)
    except Exception:
        logger.exception("Erreur API effectif detail")
        return JsonResponse({"error": "Erreur technique serveur."}, status=500)
