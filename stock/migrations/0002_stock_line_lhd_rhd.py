from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stock", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockjournal",
            name="line",
            field=models.CharField(
                blank=True,
                choices=[("A1", "A1"), ("A3", "A3"), ("LHD", "LHD"), ("RHD", "RHD")],
                max_length=8,
                null=True,
            ),
        ),
    ]
