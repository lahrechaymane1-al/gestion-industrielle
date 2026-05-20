import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm


def page_context(active_page, title):
    return {
        "active_page": active_page,
        "page_title": title,
        "sidebar_hidden_default": active_page != "home",
    }


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL or "home")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = (form.cleaned_data["identifiant"] or "").strip()
        password = form.cleaned_data["code"] or ""
        user = authenticate(request, username=username, password=password)
        if not user:
            # Bootstrap a first admin account from environment when no users exist yet.
            default_admin_username = os.getenv("APP_DEFAULT_ADMIN_USERNAME", "admin")
            default_admin_password = os.getenv("APP_DEFAULT_ADMIN_PASSWORD", "admin12345")
            if username == default_admin_username and password == default_admin_password:
                User = get_user_model()
                if not User.objects.exists():
                    User.objects.create_superuser(
                        username=default_admin_username,
                        password=default_admin_password,
                        email=os.getenv("APP_DEFAULT_ADMIN_EMAIL", ""),
                    )
                    user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL or "home")
        messages.error(request, "Identifiants incorrects.")
    return render(request, "app/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def home_view(request):
    context = page_context("home", "Bienvenue")
    if request.GET.get("sidebar") == "hidden":
        context["sidebar_hidden_default"] = True
    return render(request, "app/home.html", context)

