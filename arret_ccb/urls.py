from django.urls import re_path

from . import views

urlpatterns = [re_path(r"^$", views.list_view, name="areas_ccb_arret")]

