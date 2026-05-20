# Enregistre OperateurEffectif dans l'état des migrations effectif sans modifier la base
# (table existante app_operateureffectif, managed=False).

import datetime

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="OperateurEffectif",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "nom_complet",
                            models.CharField(
                                default="N/A",
                                max_length=180,
                                verbose_name="Nom complet",
                            ),
                        ),
                        (
                            "shift",
                            models.CharField(
                                choices=[("A", "A"), ("B", "B"), ("N", "N")],
                                default="A",
                                max_length=1,
                                verbose_name="Shift",
                            ),
                        ),
                        ("cin", models.CharField(max_length=32, unique=True, verbose_name="CIN")),
                        (
                            "type_contrat",
                            models.CharField(
                                choices=[("CDI", "CDI"), ("CDD", "CDD"), ("ANAPEC", "ANAPEC")],
                                default="CDI",
                                max_length=20,
                                verbose_name="Type de contrat",
                            ),
                        ),
                        (
                            "date_naissance",
                            models.DateField(
                                default=datetime.date(1990, 1, 1),
                                verbose_name="Date de naissance",
                            ),
                        ),
                        (
                            "date_entree",
                            models.DateField(
                                default=datetime.date(2010, 1, 1),
                                verbose_name="Date d'entree",
                            ),
                        ),
                        (
                            "identifiant",
                            models.CharField(max_length=64, unique=True, verbose_name="Identifiant"),
                        ),
                        (
                            "num_tel",
                            models.CharField(
                                default="+212600000000",
                                max_length=24,
                                verbose_name="Numero de telephone",
                            ),
                        ),
                        (
                            "sexe",
                            models.CharField(
                                choices=[("Homme", "Homme"), ("Femme", "Femme")],
                                default="Homme",
                                max_length=10,
                                verbose_name="Sexe",
                            ),
                        ),
                        (
                            "fonction",
                            models.CharField(
                                choices=[("PSP", "PSP"), ("OPERATEUR", "OPERATEUR")],
                                default="OPERATEUR",
                                max_length=20,
                                verbose_name="Fonction",
                            ),
                        ),
                        (
                            "ville_actuelle",
                            models.CharField(
                                default="N/A",
                                max_length=120,
                                verbose_name="Ville actuelle",
                            ),
                        ),
                        (
                            "niveau_etude",
                            models.CharField(
                                default="N/A",
                                max_length=120,
                                verbose_name="Niveau d'etude",
                            ),
                        ),
                        (
                            "numero_casier",
                            models.CharField(
                                default="N/A",
                                max_length=32,
                                verbose_name="Numero de casier",
                            ),
                        ),
                        (
                            "parada_transport",
                            models.CharField(
                                default="N/A",
                                max_length=120,
                                verbose_name="Parada de transport",
                            ),
                        ),
                        (
                            "pointure_chaussure",
                            models.PositiveIntegerField(
                                validators=[django.core.validators.MinValueValidator(1)],
                                verbose_name="Pointure de chaussure",
                            ),
                        ),
                        (
                            "specialite",
                            models.CharField(
                                default="N/A",
                                max_length=120,
                                verbose_name="Specialite",
                            ),
                        ),
                        (
                            "taille_pantalon",
                            models.CharField(
                                default="M",
                                max_length=20,
                                verbose_name="Taille pantalon",
                            ),
                        ),
                        (
                            "taille_veste",
                            models.CharField(
                                default="M",
                                max_length=20,
                                verbose_name="Taille veste",
                            ),
                        ),
                        (
                            "ville_origine",
                            models.CharField(
                                default="N/A",
                                max_length=120,
                                verbose_name="Ville origine",
                            ),
                        ),
                        (
                            "equipe",
                            models.CharField(
                                choices=[("Berceau", "Berceau"), ("CCB", "CCB")],
                                max_length=20,
                                verbose_name="Equipe",
                            ),
                        ),
                        (
                            "psp_lead",
                            models.ForeignKey(
                                blank=True,
                                help_text="PSP responsable de cette equipe operateur.",
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="team_members",
                                to="effectif.operateureffectif",
                            ),
                        ),
                        (
                            "code_equipe",
                            models.CharField(
                                blank=True,
                                db_index=True,
                                default="",
                                help_text=(
                                    "Code court partage par le PSP et ses operateurs "
                                    "(meme equipe) pour synchroniser le shift."
                                ),
                                max_length=24,
                                verbose_name="Code equipe",
                            ),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "updated_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="effectifs_updated_berceau_area",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        ("is_deleted", models.BooleanField(default=False)),
                    ],
                    options={
                        "db_table": "app_operateureffectif",
                        "ordering": ["nom_complet"],
                        "managed": False,
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
