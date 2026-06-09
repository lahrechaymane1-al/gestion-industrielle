from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("consommable", "0003_rename_pr_torche_manuelle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="consommableitem",
            name="type_materiel",
            field=models.CharField(default="AUTRE", max_length=40),
        ),
    ]
