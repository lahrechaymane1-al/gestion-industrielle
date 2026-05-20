def list_view(request):
    from django.shortcuts import render

    return render(
        request,
        "app/ccb/stock.html",
        {
            "active_page": "ccb_stock",
            "page_title": "Stock CCB",
            "sidebar_hidden_default": True,
        },
    )

