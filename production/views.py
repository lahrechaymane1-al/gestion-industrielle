from django.contrib import messages
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render

from .models import ProductionBerceau


def list_view(request):
    # region agent log
    try:
        import json as _json, time as _time  # noqa: E401
        from pathlib import Path as _Path  # noqa: E401
        from django.conf import settings as _settings  # type: ignore

        _payload = {
            "sessionId": "de58f7",
            "runId": "pre-fix",
            "hypothesisId": "H2",
            "location": "production/views.py:list_view",
            "message": "legacy_production_list_served",
            "data": {"path": getattr(request, "path", None), "method": getattr(request, "method", None)},
            "timestamp": int(_time.time() * 1000),
        }
        with open(str(_Path(_settings.BASE_DIR) / "debug-de58f7.log"), "a", encoding="utf-8") as _f:
            _f.write(_json.dumps(_payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion
    queryset = ProductionBerceau.objects.all()
    selected_line = request.GET.get("line", "")
    if selected_line in {"A1", "A3"}:
        queryset = queryset.filter(line=selected_line)
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
    return render(
        request,
        "app/berceau/production_list.html",
        {
            "active_page": "berceau_production",
            "page_title": "Production Berceau",
            "sidebar_hidden_default": True,
            "productions": queryset,
            "hourly_rows": hourly_rows,
            "line_filter": selected_line,
            "line_choices": ProductionBerceau.LINE_CHOICES,
        },
    )


def add_view(request):
    form_cls = modelform_factory(ProductionBerceau, fields="__all__")
    form = form_cls(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production ajoutee avec succes.")
        return redirect("areas_berceau_production_list")
    return render(
        request,
        "app/berceau/production_form.html",
        {
            "active_page": "berceau_production",
            "page_title": "Ajouter une production",
            "sidebar_hidden_default": True,
            "form": form,
        },
    )


def edit_view(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    form_cls = modelform_factory(ProductionBerceau, fields="__all__")
    form = form_cls(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production modifiee avec succes.")
        return redirect("areas_berceau_production_list")
    return render(
        request,
        "app/berceau/production_form.html",
        {
            "active_page": "berceau_production",
            "page_title": "Modifier une production",
            "sidebar_hidden_default": True,
            "form": form,
            "production": obj,
        },
    )


def detail_view(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    return render(
        request,
        "app/berceau/production_detail.html",
        {
            "active_page": "berceau_production",
            "page_title": "Detail production Berceau",
            "sidebar_hidden_default": True,
            "production": obj,
        },
    )


def delete_view(request, pk):
    obj = get_object_or_404(ProductionBerceau, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Production supprimee avec succes.")
        return redirect("areas_berceau_production_list")
    from django.http import HttpResponse

    return HttpResponse("Methode non autorisee.", status=405)

