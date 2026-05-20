# Enregistre ProductionCCB dans l'état des migrations production_ccb sans modifier la base
# (table existante app_productionccb, managed=False).

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("production_ccb", "0003_ccb_hourly_columns_sqlite_idempotent"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ProductionCCB",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("date", models.DateField(verbose_name="Date")),
                        ("shift", models.CharField(choices=[("A", "A"), ("B", "B"), ("N", "N")], max_length=1, verbose_name="Shift")),
                        ("objectif", models.PositiveIntegerField(default=151, verbose_name="Objectif")),
                        (
                            "production_h1",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H1",
                            ),
                        ),
                        (
                            "production_h2",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H2",
                            ),
                        ),
                        (
                            "production_h3",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H3",
                            ),
                        ),
                        (
                            "production_h4",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H4",
                            ),
                        ),
                        (
                            "production_h5",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H5",
                            ),
                        ),
                        (
                            "production_h6",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H6",
                            ),
                        ),
                        (
                            "production_h7",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H7",
                            ),
                        ),
                        (
                            "production_h8",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Production H8",
                            ),
                        ),
                        (
                            "rebut_h1",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H1",
                            ),
                        ),
                        (
                            "rebut_h2",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H2",
                            ),
                        ),
                        (
                            "rebut_h3",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H3",
                            ),
                        ),
                        (
                            "rebut_h4",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H4",
                            ),
                        ),
                        (
                            "rebut_h5",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H5",
                            ),
                        ),
                        (
                            "rebut_h6",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H6",
                            ),
                        ),
                        (
                            "rebut_h7",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H7",
                            ),
                        ),
                        (
                            "rebut_h8",
                            models.PositiveIntegerField(
                                default=0,
                                validators=[django.core.validators.MinValueValidator(0)],
                                verbose_name="Rebut H8",
                            ),
                        ),
                        ("volume", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Volume")),
                        ("rebut", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Rebut")),
                        ("retouche", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Retouche")),
                        (
                            "temps_arrets",
                            models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0)], verbose_name="Temps d'arrets"),
                        ),
                    ],
                    options={
                        "db_table": "app_productionccb",
                        "ordering": ["-date", "shift"],
                        "managed": False,
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
