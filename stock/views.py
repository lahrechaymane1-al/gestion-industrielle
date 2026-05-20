def list_view(request):
    from django.shortcuts import render

    return render(
        request,
        "app/berceau/stock.html",
        {
            "active_page": "berceau_stock",
            "page_title": "Stock",
            "sidebar_hidden_default": True,
        },
    )

