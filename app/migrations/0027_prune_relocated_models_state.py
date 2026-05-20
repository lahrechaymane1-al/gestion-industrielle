# Les modèles métier (Absence, Production*, AlertePanne, etc.) vivent dans leurs apps dédiées
# (absence, production, arret, …) avec managed=False et les mêmes tables SQL qu'avant.
# Cette migration aligne uniquement l'état du graphe Django pour l'app « app » : il ne reste
# que UserAccessProfile. Aucune instruction SQL n'est exécutée sur la base.
#
# Doit s'appliquer après 0026_alter_useraccessprofile_effectif pour que effectif ne soit plus
# référencé via app.operateureffectif.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0026_alter_useraccessprofile_effectif"),
    ]

    _state_ops = [
        migrations.RemoveIndex(
            model_name="absence",
            name="absence_date_idx",
        ),
        migrations.RemoveIndex(
            model_name="absence",
            name="absence_motif_idx",
        ),
        migrations.RemoveConstraint(
            model_name="absence",
            name="uniq_absence_effectif_date_equipe",
        ),
        migrations.RemoveField(
            model_name="alertepanne",
            name="module",
        ),
        migrations.RemoveField(
            model_name="alertepanne",
            name="moyen",
        ),
        migrations.RemoveField(
            model_name="alertepanne",
            name="panne_type",
        ),
        migrations.RemoveField(
            model_name="alertepanne",
            name="poste",
        ),
        migrations.RemoveField(
            model_name="alertepanne",
            name="updated_by",
        ),
        migrations.RemoveConstraint(
            model_name="arretberceau",
            name="uniq_arret_berceau_scope",
        ),
        migrations.RemoveConstraint(
            model_name="berceaumoyen",
            name="uniq_berceau_moyen_poste_name",
        ),
        migrations.RemoveConstraint(
            model_name="berceauposte",
            name="uniq_berceau_poste_module_name",
        ),
        migrations.RemoveIndex(
            model_name="modedegrade",
            name="mode_degrade_date_idx",
        ),
        migrations.RemoveIndex(
            model_name="modedegrade",
            name="mode_degrade_statut_idx",
        ),
        migrations.RemoveField(
            model_name="operateureffectif",
            name="psp_lead",
        ),
        migrations.RemoveField(
            model_name="operateureffectif",
            name="updated_by",
        ),
        migrations.RemoveField(
            model_name="pannetype",
            name="updated_by",
        ),
        migrations.RemoveConstraint(
            model_name="productionberceau",
            name="uniq_production_berceau_line_date_shift",
        ),
        migrations.DeleteModel(
            name="ProductionBerceau",
        ),
        migrations.RemoveConstraint(
            model_name="productionccb",
            name="uniq_production_ccb_date_shift",
        ),
        migrations.DeleteModel(
            name="ProductionCCB",
        ),
        migrations.AlterModelOptions(
            name="useraccessprofile",
            options={"managed": False, "verbose_name": "Profil d'acces", "verbose_name_plural": "Profils d'acces"},
        ),
        migrations.RemoveField(
            model_name="absence",
            name="effectif",
        ),
        migrations.RemoveField(
            model_name="absence",
            name="remplacant_effectif",
        ),
        migrations.RemoveField(
            model_name="absence",
            name="updated_by",
        ),
        migrations.DeleteModel(
            name="AlertePanne",
        ),
        migrations.RemoveField(
            model_name="arretberceau",
            name="module",
        ),
        migrations.RemoveField(
            model_name="arretberceau",
            name="moyen",
        ),
        migrations.RemoveField(
            model_name="arretberceau",
            name="poste",
        ),
        migrations.RemoveField(
            model_name="arretberceau",
            name="updated_by",
        ),
        migrations.RemoveField(
            model_name="berceaumoyen",
            name="poste",
        ),
        migrations.RemoveField(
            model_name="berceauposte",
            name="module",
        ),
        migrations.RemoveField(
            model_name="modedegrade",
            name="updated_by",
        ),
        migrations.DeleteModel(
            name="PanneType",
        ),
        migrations.DeleteModel(
            name="OperateurEffectif",
        ),
        migrations.DeleteModel(
            name="Absence",
        ),
        migrations.DeleteModel(
            name="ArretBerceau",
        ),
        migrations.DeleteModel(
            name="BerceauMoyen",
        ),
        migrations.DeleteModel(
            name="BerceauModule",
        ),
        migrations.DeleteModel(
            name="BerceauPoste",
        ),
        migrations.DeleteModel(
            name="ModeDegrade",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=_state_ops,
            database_operations=[],
        ),
    ]
