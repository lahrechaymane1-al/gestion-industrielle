from django.db import migrations, models
import django.core.validators


def seed_default_settings(apps, schema_editor):
    CcbProductionSettings = apps.get_model("production_ccb", "CcbProductionSettings")
    if CcbProductionSettings.objects.filter(pk=1).exists():
        return
    CcbProductionSettings.objects.create(
        pk=1,
        objectif_h1=20,
        objectif_h2=20,
        objectif_h3=20,
        objectif_h4=20,
        objectif_h5=11,
        objectif_h6=20,
        objectif_h7=20,
        objectif_h8=20,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("production_ccb", "0005_ccb_lhd_rhd_objectifs_horaires"),
    ]

    operations = [
        migrations.CreateModel(
            name="CcbProductionSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("objectif_h1", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H1")),
                ("objectif_h2", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H2")),
                ("objectif_h3", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H3")),
                ("objectif_h4", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H4")),
                ("objectif_h5", models.PositiveIntegerField(default=11, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H5")),
                ("objectif_h6", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H6")),
                ("objectif_h7", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H7")),
                ("objectif_h8", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)], verbose_name="Objectif H8")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paramètres production CCB",
                "verbose_name_plural": "Paramètres production CCB",
            },
        ),
        migrations.RunPython(seed_default_settings, migrations.RunPython.noop),
    ]
