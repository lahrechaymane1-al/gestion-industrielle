from datetime import date

from django.db import migrations, models
import django.core.validators


def seed_default_impact_settings(apps, schema_editor):
    BerceauImpactSettings = apps.get_model("production", "BerceauImpactSettings")
    if BerceauImpactSettings.objects.exists():
        return
    BerceauImpactSettings.objects.create(
        effective_from=date(2000, 1, 1),
        divisor_a1=1.3,
        divisor_a3=1.8,
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BerceauImpactSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateField(verbose_name="En vigueur à partir du")),
                (
                    "divisor_a1",
                    models.FloatField(
                        default=1.3,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                    ),
                ),
                (
                    "divisor_a3",
                    models.FloatField(
                        default=1.8,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paramètres impact Berceau",
                "verbose_name_plural": "Paramètres impact Berceau",
                "ordering": ["-effective_from", "-id"],
            },
        ),
        migrations.RunPython(seed_default_impact_settings, migrations.RunPython.noop),
    ]
