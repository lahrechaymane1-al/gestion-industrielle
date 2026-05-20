from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StockJournal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("equipe", models.CharField(choices=[("Berceau", "Berceau"), ("CCB", "CCB")], default="Berceau", max_length=20)),
                ("line", models.CharField(blank=True, choices=[("A1", "A1"), ("A3", "A3")], max_length=2, null=True)),
                ("stock_debut", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("entree_calculee", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("sortie_montage", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("stock_fin", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("is_closed", models.BooleanField(default=False)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_journal_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "stock_journal",
                "ordering": ["-date", "equipe", "line"],
            },
        ),
        migrations.AddConstraint(
            model_name="stockjournal",
            constraint=models.UniqueConstraint(fields=("date", "equipe", "line"), name="uniq_stock_journal_date_equipe_line"),
        ),
    ]
