from django.urls import re_path
from django.views.generic import RedirectView

from . import api_auth_views, api_panne_views, api_production_views, api_stock_views, page_views, react_views, views
from absence_ccb import views as absence_ccb_views
from effectif_ccb import views as effectif_ccb_views
from mode_degrade_ccb import views as mode_degrade_ccb_views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Exclusion routing (hybrid Django + React)
    #
    # Rule: Django-owned routes must be declared explicitly FIRST.
    # Then a React SPA "catch-all" comes LAST, so any remaining URL is handled
    # by the SPA router (React Router).
    # -------------------------------------------------------------------------

    # ----------------------------
    # Django pages (auth/session)
    # ----------------------------
    re_path(r"^$", react_views.react_app, name="root"),
    re_path(r"^login/?$", page_views.login_view, name="login"),
    re_path(r"^logout/?$", page_views.logout_view, name="logout"),

    # ----------------------------
    # Django JSON auth endpoints (under /api/)
    # ----------------------------
    re_path(r"^api/auth/login/?$", api_auth_views.api_auth_login, name="api_auth_login"),
    re_path(r"^api/auth/logout/?$", api_auth_views.api_auth_logout, name="api_auth_logout"),
    re_path(r"^api/auth/me/?$", api_auth_views.api_auth_me, name="api_auth_me"),
    re_path(r"^home/?$", react_views.react_app, name="home"),

    # ----------------------------
    # Django business pages (Berceau/CCB)
    # ----------------------------
    # SPA routes (React) — keep refresh consistent (serve React shell).
    re_path(r"^berceau/production/?$", react_views.react_app, name="berceau_production_list"),
    re_path(r"^berceau/production/export/?$", views.berceau_production_export, name="berceau_production_export"),
    re_path(r"^berceau/production/add/?$", views.berceau_production_add, name="berceau_production_add"),
    re_path(r"^berceau/production/edit/(?P<pk>\d+)/?$", views.berceau_production_edit, name="berceau_production_edit"),
    re_path(r"^berceau/production/(?P<pk>\d+)/?$", views.berceau_production_detail, name="berceau_production_detail"),
    re_path(r"^berceau/production/delete/(?P<pk>\d+)/?$", views.berceau_production_delete, name="berceau_production_delete"),
    re_path(r"^berceau/mode-degrade/?$", react_views.react_app, name="berceau_mode_degrade"),
    re_path(r"^berceau/mode-degrade/add/?$", views.berceau_mode_degrade_add, name="berceau_mode_degrade_add"),
    re_path(r"^berceau/mode-degrade/edit/(?P<pk>\d+)/?$", views.berceau_mode_degrade_edit, name="berceau_mode_degrade_edit"),
    re_path(r"^berceau/mode-degrade/(?P<pk>\d+)/?$", views.berceau_mode_degrade_detail, name="berceau_mode_degrade_detail"),
    re_path(r"^berceau/mode-degrade/delete/(?P<pk>\d+)/?$", views.berceau_mode_degrade_delete, name="berceau_mode_degrade_delete"),
    re_path(r"^berceau/absence/?$", react_views.react_app, name="berceau_absence"),
    re_path(r"^berceau/absence/add/?$", views.berceau_absence_add, name="berceau_absence_add"),
    re_path(r"^berceau/absence/edit/(?P<pk>\d+)/?$", views.berceau_absence_edit, name="berceau_absence_edit"),
    re_path(r"^berceau/absence/(?P<pk>\d+)/?$", views.berceau_absence_detail, name="berceau_absence_detail"),
    re_path(r"^berceau/absence/delete/(?P<pk>\d+)/?$", views.berceau_absence_delete, name="berceau_absence_delete"),
    re_path(r"^berceau/effectif/?$", react_views.react_app, name="berceau_effectif"),
    re_path(r"^berceau/effectif/add/?$", views.berceau_effectif_add, name="berceau_effectif_add"),
    re_path(r"^berceau/effectif/edit/(?P<pk>\d+)/?$", views.berceau_effectif_edit, name="berceau_effectif_edit"),
    re_path(r"^berceau/effectif/(?P<pk>\d+)/?$", views.berceau_effectif_detail, name="berceau_effectif_detail"),
    re_path(r"^berceau/effectif/delete/(?P<pk>\d+)/?$", views.berceau_effectif_delete, name="berceau_effectif_delete"),
    re_path(r"^berceau/stock/?$", react_views.react_app, name="berceau_stock"),
    re_path(r"^berceau/arret/?$", react_views.react_app, name="berceau_arret"),
    re_path(r"^ccb/production/?$", react_views.react_app, name="ccb_production"),
    re_path(r"^ccb/production/export/?$", views.ccb_production_export, name="ccb_production_export"),
    re_path(r"^ccb/production/add/?$", views.ccb_production_add, name="ccb_production_add"),
    re_path(r"^ccb/production/edit/(?P<pk>\d+)/?$", views.ccb_production_edit, name="ccb_production_edit"),
    re_path(r"^ccb/production/(?P<pk>\d+)/?$", views.ccb_production_detail, name="ccb_production_detail"),
    re_path(r"^ccb/production/delete/(?P<pk>\d+)/?$", views.ccb_production_delete, name="ccb_production_delete"),
    re_path(r"^ccb/mode-degrade/?$", react_views.react_app, name="ccb_mode_degrade"),
    re_path(r"^ccb/mode-degrade/add/?$", mode_degrade_ccb_views.add_view, name="ccb_mode_degrade_add"),
    re_path(r"^ccb/mode-degrade/edit/(?P<pk>\d+)/?$", mode_degrade_ccb_views.edit_view, name="ccb_mode_degrade_edit"),
    re_path(r"^ccb/mode-degrade/(?P<pk>\d+)/?$", mode_degrade_ccb_views.detail_view, name="ccb_mode_degrade_detail"),
    re_path(r"^ccb/mode-degrade/delete/(?P<pk>\d+)/?$", mode_degrade_ccb_views.delete_view, name="ccb_mode_degrade_delete"),
    re_path(r"^ccb/absence/?$", react_views.react_app, name="ccb_absence"),
    re_path(r"^ccb/absence/add/?$", absence_ccb_views.add_view, name="ccb_absence_add"),
    re_path(r"^ccb/absence/edit/(?P<pk>\d+)/?$", absence_ccb_views.edit_view, name="ccb_absence_edit"),
    re_path(r"^ccb/absence/(?P<pk>\d+)/?$", absence_ccb_views.detail_view, name="ccb_absence_detail"),
    re_path(r"^ccb/absence/delete/(?P<pk>\d+)/?$", absence_ccb_views.delete_view, name="ccb_absence_delete"),
    re_path(r"^ccb/effectif/?$", react_views.react_app, name="ccb_effectif"),
    re_path(r"^ccb/effectif/add/?$", effectif_ccb_views.add_view, name="ccb_effectif_add"),
    re_path(r"^ccb/effectif/edit/(?P<pk>\d+)/?$", effectif_ccb_views.edit_view, name="ccb_effectif_edit"),
    re_path(r"^ccb/effectif/(?P<pk>\d+)/?$", effectif_ccb_views.detail_view, name="ccb_effectif_detail"),
    re_path(r"^ccb/effectif/delete/(?P<pk>\d+)/?$", effectif_ccb_views.delete_view, name="ccb_effectif_delete"),
    re_path(r"^ccb/stock/?$", react_views.react_app, name="ccb_stock"),
    re_path(r"^ccb/arret/?$", react_views.react_app, name="ccb_arret"),
    re_path(r"^api/effectifs/?$", views.api_effectifs, name="api_effectifs"),
    re_path(r"^api/effectifs/options/?$", views.api_effectif_options, name="api_effectif_options"),
    re_path(r"^api/effectifs/(?P<pk>\d+)/?$", views.api_effectif_detail, name="api_effectif_detail"),
    re_path(r"^api/absences/?$", views.api_absences, name="api_absences"),
    re_path(r"^api/absences/(?P<pk>\d+)/?$", views.api_absence_detail, name="api_absence_detail"),
    re_path(r"^api/mode-degrade/?$", views.api_mode_degrade, name="api_mode_degrade"),
    re_path(r"^api/mode-degrade/(?P<pk>\d+)/?$", views.api_mode_degrade_detail, name="api_mode_degrade_detail"),
    re_path(r"^api/berceau/production/?$", api_production_views.api_production_berceau, name="api_production_berceau"),
    re_path(
        r"^api/berceau/production/(?P<pk>\d+)/?$",
        api_production_views.api_production_berceau_detail,
        name="api_production_berceau_detail",
    ),
    re_path(
        r"^api/berceau/production/(?P<pk>\d+)/validate-hour/?$",
        api_production_views.api_production_berceau_validate_hour,
        name="api_production_berceau_validate_hour",
    ),
    re_path(r"^api/ccb/production/?$", api_production_views.api_production_ccb, name="api_production_ccb"),
    re_path(
        r"^api/dashboard/ro-nro-trend/?$",
        api_production_views.api_dashboard_ro_nro_trend,
        name="api_dashboard_ro_nro_trend",
    ),
    re_path(
        r"^api/dashboard/arrets-par-jour/?$",
        api_production_views.api_dashboard_arrets_par_jour,
        name="api_dashboard_arrets_par_jour",
    ),
    re_path(
        r"^api/dashboard/pareto-pannes/?$",
        api_production_views.api_dashboard_pareto_postes,
        name="api_dashboard_pareto_pannes",
    ),
    re_path(
        r"^api/dashboard/pareto-postes/?$",
        api_production_views.api_dashboard_pareto_postes,
        name="api_dashboard_pareto_postes",
    ),
    re_path(
        r"^api/ccb/production/(?P<pk>\d+)/?$",
        api_production_views.api_production_ccb_detail,
        name="api_production_ccb_detail",
    ),
    re_path(r"^api/berceau/modules/?$", api_panne_views.api_berceau_modules, name="api_berceau_modules"),
    re_path(
        r"^api/berceau/modules/(?P<module_id>\d+)/postes/?$",
        api_panne_views.api_berceau_module_postes,
        name="api_berceau_module_postes",
    ),
    re_path(
        r"^api/berceau/postes/(?P<poste_id>\d+)/moyens/?$",
        api_panne_views.api_berceau_poste_moyens,
        name="api_berceau_poste_moyens",
    ),
    re_path(r"^api/berceau/postes/?$", api_panne_views.api_berceau_postes, name="api_berceau_postes"),
    re_path(r"^api/panne-types/?$", api_panne_views.api_panne_types, name="api_panne_types"),
    re_path(
        r"^api/panne-types/(?P<pk>\d+)/?$",
        api_panne_views.api_panne_type_detail,
        name="api_panne_type_detail",
    ),
    re_path(r"^api/arrets/temps-auto/?$", api_panne_views.api_arrets_temps_auto, name="api_arrets_temps_auto"),
    re_path(r"^api/alertes-pannes/?$", api_panne_views.api_alertes_pannes, name="api_alertes_pannes"),
    re_path(
        r"^api/alertes-pannes/export/?$",
        api_panne_views.api_alertes_pannes_export,
        name="api_alertes_pannes_export",
    ),
    re_path(
        r"^api/alertes-pannes/(?P<pk>\d+)/?$",
        api_panne_views.api_alertes_pannes_detail,
        name="api_alertes_pannes_detail",
    ),
    re_path(r"^api/stock/journal/?$", api_stock_views.api_stock_journal, name="api_stock_journal"),
    re_path(r"^api/stock/journal/update/?$", api_stock_views.api_stock_journal_update, name="api_stock_journal_update"),

    # ----------------------------
    # Back-compat redirects
    # ----------------------------
    # Back-compat: SPA used to live under /app/*. Preserve deep links (/app/foo → /foo).
    re_path(r"^app/?$", RedirectView.as_view(url="/", permanent=False), name="react_app"),
    re_path(r"^app/(?P<path>.+)$", RedirectView.as_view(url="/%(path)s", permanent=False)),

    # ----------------------------
    # React SPA catch-all (must be LAST)
    # ----------------------------
    # Any URL not matched above will return the React shell, and React Router
    # decides what to render client-side.
    re_path(r"^(?P<path>.*)$", react_views.react_app),
]
