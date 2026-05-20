def list_view(request):
    from django.shortcuts import render

    return render(
        request,
        "app/berceau/arret.html",
        {
            "active_page": "berceau_arret",
            "page_title": "Arret",
            "sidebar_hidden_default": True,
        },
    )

