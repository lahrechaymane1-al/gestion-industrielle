def list_view(request):
    from django.shortcuts import render

    from .models import ProductionCCB

    queryset = ProductionCCB.objects.all()
    selected_shift = request.GET.get("shift", "")
    if selected_shift in {"A", "B", "N"}:
        queryset = queryset.filter(shift=selected_shift)
    return render(
        request,
        "app/ccb/production_list.html",
        {
            "active_page": "ccb_production",
            "page_title": "Production CCB",
            "sidebar_hidden_default": True,
            "productions": queryset,
            "shift_filter": selected_shift,
            "shift_choices": ProductionCCB.SHIFT_CHOICES,
        },
    )

