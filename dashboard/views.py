def index(request):
    from django.shortcuts import render

    context = {
        "active_page": "home",
        "page_title": "Bienvenue",
        "sidebar_hidden_default": request.GET.get("sidebar") == "hidden",
    }
    return render(request, "app/home.html", context)

