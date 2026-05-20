def list_view(request):
    from django.shortcuts import render

    return render(
        request,
        "app/ccb/arret.html",
        {
            "active_page": "ccb_arret",
            "page_title": "Arret CCB",
            "sidebar_hidden_default": True,
        },
    )

