import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0015_backfill_absence_required_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h1",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H1",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h2",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H2",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h3",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H3",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h4",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H4",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h5",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H5",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h6",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H6",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h7",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H7",
            ),
        ),
        migrations.AddField(
            model_name="productionberceau",
            name="temps_arrets_h8",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Temps arrets H8",
            ),
        ),
    ]
