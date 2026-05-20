from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"^$", views.list_view, name="areas_ccb_absence"),
    re_path(r"^add/?$", views.add_view, name="areas_ccb_absence_add"),
    re_path(r"^edit/(?P<pk>\d+)/?$", views.edit_view, name="areas_ccb_absence_edit"),
    re_path(r"^(?P<pk>\d+)/?$", views.detail_view, name="areas_ccb_absence_detail"),
    re_path(r"^delete/(?P<pk>\d+)/?$", views.delete_view, name="areas_ccb_absence_delete"),
]

