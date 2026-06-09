from django.db import migrations, models
import django.core.validators


BERCEAU_DEFAULT_OBJECTIFS_A1 = (40, 45, 45, 45, 25, 45, 45, 45)
BERCEAU_DEFAULT_OBJECTIFS_A3 = (30, 33, 33, 33, 20, 33, 33, 33)


def seed_berceau_production_settings(apps, schema_editor):
    BerceauProductionSettings = apps.get_model("production", "BerceauProductionSettings")
    if BerceauProductionSettings.objects.filter(pk=1).exists():
        return
    fields = {"pk": 1}
    for h, val in enumerate(BERCEAU_DEFAULT_OBJECTIFS_A1, start=1):
        fields[f"objectif_a1_h{h}"] = val
    for h, val in enumerate(BERCEAU_DEFAULT_OBJECTIFS_A3, start=1):
        fields[f"objectif_a3_h{h}"] = val
    BerceauProductionSettings.objects.create(**fields)


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0001_berceau_impact_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="BerceauProductionSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("objectif_a1_h1", models.PositiveIntegerField(default=40, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h2", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h3", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h4", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h5", models.PositiveIntegerField(default=25, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h6", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h7", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a1_h8", models.PositiveIntegerField(default=45, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h1", models.PositiveIntegerField(default=30, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h2", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h3", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h4", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h5", models.PositiveIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h6", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h7", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("objectif_a3_h8", models.PositiveIntegerField(default=33, validators=[django.core.validators.MinValueValidator(0)])),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paramètres production Berceau",
                "verbose_name_plural": "Paramètres production Berceau",
            },
        ),
        migrations.RunPython(seed_berceau_production_settings, migrations.RunPython.noop),
    ]
