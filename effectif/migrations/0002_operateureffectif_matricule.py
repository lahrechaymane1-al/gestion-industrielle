from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("effectif", "0001_operateureffectif_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="operateureffectif",
                    name="matricule",
                    field=models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=64,
                        verbose_name="Matricule",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
