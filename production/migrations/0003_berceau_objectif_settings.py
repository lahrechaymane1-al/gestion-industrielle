from datetime import date

from django.db import migrations, models
import django.core.validators


def seed_berceau_objectif_settings(apps, schema_editor):
    BerceauObjectifSettings = apps.get_model("production", "BerceauObjectifSettings")
    BerceauProductionSettings = apps.get_model("production", "BerceauProductionSettings")
    if BerceauObjectifSettings.objects.exists():
        return
    singleton = BerceauProductionSettings.objects.filter(pk=1).first()
    fields = {"effective_from": date(2000, 1, 1)}
    for h in range(1, 9):
        for line in ("a1", "a3"):
            key = f"objectif_{line}_h{h}"
            if singleton is not None:
                fields[key] = int(getattr(singleton, key, 0) or 0)
            else:
                defaults_a1 = (40, 45, 45, 45, 25, 45, 45, 45)
                defaults_a3 = (30, 33, 33, 33, 20, 33, 33, 33)
                fields[key] = defaults_a1[h - 1] if line == "a1" else defaults_a3[h - 1]
    BerceauObjectifSettings.objects.create(**fields)


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0002_berceau_production_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="BerceauObjectifSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateField(verbose_name="En vigueur à partir du")),
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paramètres objectifs Berceau",
                "verbose_name_plural": "Paramètres objectifs Berceau",
                "ordering": ["-effective_from", "-id"],
            },
        ),
        migrations.RunPython(seed_berceau_objectif_settings, migrations.RunPython.noop),
    ]
